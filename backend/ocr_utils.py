"""
ocr_utils.py
------------
Butun "dokumandan metin/on izleme cikarma" mantigi TEK bu modulde toplanir:

  - Falcon-OCR (tiiuae/Falcon-OCR) fallback'ini saran, VRAM yasam donguresunu
    elle yoneten FalconOCR sarmalayicisi.
  - extract_documents(): ALLOWED_EXT'teki her format icin uzantiya gore
    PyMuPDF/TextLoader/Docx2txtLoader/python-pptx arasinda dispatch eder;
    PDF'te taranmis (metin katmani yok/az) sayfalari ve dogrudan resim
    yuklemelerini Falcon-OCR ile isler.
  - extract_pdf_page_text(): citation fallback'i icin tek bir PDF sayfasinin
    duz metnini cikarir.
  - generate_preview_pdf(): kaynak hangi formatta olursa olsun ("ekran
    goruntusu" mantiginda) frontend'de indirilebilir/goruntulenebilir TEK
    bir PDF uretir.
  - Eski .doc/.ppt (OLE2) formatlarini .docx/.pptx/.pdf'e cevirmek icin
    LibreOffice headless sarmalayicisi.

rag_chat.py SADECE bu moduldeki fonksiyonlari cagirir ve donen List[Document]
/ metin / dosya yolunu kullanir - "hangi format nasil metne/PDF'e cevrilir"
sorusunun TEK cevabi burasidir; rag_chat.py'de format-spesifik loader/OCR
importu veya kodu YOKTUR.

NOT (model karti dogrulamasi): huggingface.co/tiiuae/Falcon-OCR resmi
"Use this model" ornegine gore bu model icin AYRI bir processor YOK.
Sadece `AutoModelForCausalLM.from_pretrained(..., trust_remote_code=True)`
ile yukleniyor ve PIL.Image'i dogrudan `model.generate(image, category=...)`
ile isliyor; cikti `list[str]`. Asagida `self.processor` alani yine de
tutuluyor (ileride gercek bir processor gerektiren bir surume gecilirse
cagiran taraflarin sozlesmesi kirilmasin diye), ama bu modelde daima None.

Kullanim (rag_chat.py'deki gibi):
    from ocr_utils import (
        extract_documents, extract_pdf_page_text, generate_preview_pdf,
        ALLOWED_EXT, IMAGE_EXTS,
    )

    docs = extract_documents(file_path)            # List[langchain_core.documents.Document]
    text = extract_pdf_page_text(pdf_path, 3)       # tek PDF sayfasinin metni
    generate_preview_pdf(file_path, out_pdf_path)   # format ne olursa olsun tek PDF

    # Dusuk seviye, tek sayfa/resim icin dogrudan da kullanilabilir:
    with FalconOCR() as ocr:
        text = ocr.extract_text(pil_image)
"""

import gc
import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader
from langchain_core.documents import Document
from pptx import Presentation  # unstructured yerine: onnx/pdfminer/poppler gibi agir
                                # bagimliliklari yok, sadece pptx okumak icin python-pptx yeterli

from dotenv_rag import get_env_variable

FALCON_OCR_MODEL_ID = get_env_variable("FALCON_OCR_MODEL_ID", "tiiuae/Falcon-OCR")

# Proje ilk basta sadece PDF destekliyordu; sonradan eklenen formatlar da
# buraya katildi. Hem upload akisinin (rag_chat.py: create_room_from_upload)
# hem de extract_documents/_get_loader'in TEK ortak referansi burasi - yeni
# bir format eklenince sadece ALLOWED_EXT + _get_loader/extract_documents
# guncellenir.
ALLOWED_EXT = {".pdf", ".md", ".txt", ".docx", ".pptx", ".doc", ".ppt", ".jpg", ".jpeg", ".png"}

# "Sayfa" kavrami olmayan, dogrudan-resim yuklemesi olan formatlar.
IMAGE_EXTS = (".jpg", ".jpeg", ".png")

# LibreOffice ile PDF'e/office formatlarina cevrilebilen formatlar
# (generate_preview_pdf ve legacy .doc/.ppt donusumu bunlari kullanir).
_LIBREOFFICE_CONVERTIBLE_EXT = (".docx", ".doc", ".pptx", ".ppt", ".txt", ".md")

# Model karti "Choose an output format" bolumunde listelenen gecerli
# category degerleri (mode="layout" ayri bir API'ye -> generate_with_layout).
_VALID_PLAIN_CATEGORIES = {
    "plain", "text", "table", "formula", "caption", "footnote",
    "list-item", "page-footer", "page-header", "section-header", "title",
}

# Taranmis/gorsel PDF sayfasi tespiti icin esik: strip() sonrasi bu
# karakterden az metin iceren sayfa OCR'a dusecek aday sayilir.
_OCR_FALLBACK_MIN_CHARS = 20


class FalconOCR:
    """Falcon-OCR modelinin GPU yasam donguresunu yoneten sarmalayici.

    Context manager olarak kullanilir (girişte yukler, çıkışta indirir):
        with FalconOCR() as ocr:
            ...

    _load()/_unload() ayri ayri da cagrilabilir; bir job sirasinda birden
    fazla sayfa varsa cagiran taraf TEK context acip hepsini icinde
    islemeli (bkz. _ocr_fallback_for_pdf_pages), aksi halde her sayfada
    ayri yukleme/indirme cok yavas olur.
    """

    def __init__(self, model_id: str = FALCON_OCR_MODEL_ID):
        self.model_id = model_id
        self.model = None
        self.processor = None  # bu modelde kullanilmiyor, yukaridaki NOT'a bak
        self._loaded = False

    def _load(self):
        """Modeli yukler. Eger model zaten cache'de varsa internet baglantisi kontrolu yapmaz."""
        if self._loaded:
            return
        import torch
        from transformers import AutoModelForCausalLM
        import os

        # Yerel model dizini - modelin indirildigi yeri belirt
        local_model_path = os.getenv("FALCON_OCR_LOCAL_PATH", "./models/falcon-ocr")

        try:
            # Once yerel dizinde kontrol et
            if os.path.exists(local_model_path) and os.path.isdir(local_model_path):
                print(f"Model yerel dizinden yukleniyor: {local_model_path}")
                self.model = AutoModelForCausalLM.from_pretrained(
                    local_model_path,  # Yerel yol
                    trust_remote_code=True,
                    torch_dtype=torch.bfloat16,
                    device_map="auto",
                    local_files_only=True,  # Internet baglantisi kontrolu yapma
                )
            else:
                # Yerel yoksa, cache'de var mi kontrol et
                print(f"Model araniyor: {self.model_id} (yerel kopya yok, cache kontrol ediliyor)")
                try:
                    # Once cache'de var mi dene (internet baglantisi yoksa bile calisir)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        trust_remote_code=True,
                        torch_dtype=torch.bfloat16,
                        device_map="auto",
                        local_files_only=True,  # Sadece cache'de varsa yukle
                    )
                except Exception as cache_error:
                    print(f"Model cache'de bulunamadi: {cache_error}")
                    print(f"Model indiriliyor: {self.model_id} (cache'e kaydedilecek)")
                    # Cache'e indir
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        trust_remote_code=True,
                        torch_dtype=torch.bfloat16,
                        device_map="auto",
                        cache_dir=local_model_path,  # Bu dizine indir
                    )
                    # Indirdikten sonra yerel dosya olarak da kaydet
                    try:
                        self.model.save_pretrained(local_model_path)
                        print(f"Model {local_model_path} dizinine kaydedildi")
                    except Exception as save_error:
                        print(f"Model kaydedilemedi: {save_error}")

            self._loaded = True

        except Exception as e:
            print(f"Model yuklenirken hata: {e}")
            # Son bir deneme: internetten indirmeyi dene
            try:
                print(f"Son deneme: model dogrudan indiriliyor: {self.model_id}")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    trust_remote_code=True,
                    torch_dtype=torch.bfloat16,
                    device_map="auto",
                )
                self._loaded = True
                # Yerel olarak kaydet
                try:
                    os.makedirs(local_model_path, exist_ok=True)
                    self.model.save_pretrained(local_model_path)
                    print(f"Model {local_model_path} dizinine kaydedildi")
                except Exception:
                    pass
            except Exception as final_error:
                raise RuntimeError(
                    f"Falcon-OCR modeli yuklenemedi: {final_error}\n"
                    "Modeli manuel olarak indirmek icin:\n"
                    "  python -c \"from transformers import AutoModelForCausalLM; "
                    "model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', "
                    "trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')\"\n"
                    "Veya internet baglantisini kontrol edin."
                )

    def _unload(self):
        if not self._loaded:
            return
        import torch

        del self.model
        self.model = None
        self.processor = None
        self._loaded = False
        torch.cuda.empty_cache()
        gc.collect()

    def __enter__(self) -> "FalconOCR":
        self._load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._unload()
        return False

    def extract_text(self, image, mode: str = "plain") -> str:
        """image: PIL.Image.Image. mode="plain" (varsayilan) veya "layout".

        Model yuklu degilse (context disinda yanlislikla cagrilirsa)
        sessizce otomatik yuklemek YERINE acikca hata firlatir - yasam
        donguresunu caller kontrol etmeli.
        """
        if not self._loaded or self.model is None:
            raise RuntimeError(
                "FalconOCR modeli yuklu degil. extract_text(), "
                "`with FalconOCR() as ocr:` blogu icinde cagrilmali; "
                "otomatik/orsuz yukleme yapilmiyor."
            )

        if mode == "layout":
            return self.generate_with_layout(image)

        texts = self.model.generate(image, category="plain")
        return texts[0] if texts else ""

    def generate_with_layout(self, image) -> str:
        # TODO: layout modu (model.generate_with_layout) ilk versiyonda
        # implement edilmedi.
        raise NotImplementedError("generate_with_layout henuz implement edilmedi (TODO).")


class _PptxLoader:
    """Docx2txtLoader/TextLoader ile ayni sozlesme: .load() -> List[Document].

    Sadece metin degil, her slide'daki GOMULU RESIMLER de islenir: once tum
    slide'lar taranip metin + resim(ler) toplanir, sonra TUM resimler TEK
    bir FalconOCR context'i icinde OCR'lanir (slide basina ayri ayri context
    acmak yavas olurdu), son olarak her slide'in metniyle o slide'daki
    resim(ler)in OCR metni tek page_content'te birlestirilir."""

    def __init__(self, file_path: str, room_id: str = ""):
        self.file_path = file_path
        self.room_id = room_id

    def load(self) -> List[Document]:
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        from PIL import Image
        import io

        prefix = f"[{self.room_id}] " if self.room_id else ""
        prs = Presentation(self.file_path)

        slide_texts: List[str] = []
        slide_images: List[list] = []  # her slide icin PIL.Image listesi
        for slide in prs.slides:
            lines = []
            images = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        line = "".join(run.text for run in para.runs)
                        if line.strip():
                            lines.append(line)
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    try:
                        images.append(Image.open(io.BytesIO(shape.image.blob)).convert("RGB"))
                    except Exception as e:
                        print(f"{prefix}Slide gomulu resmi okunamadi: {e}")
            slide_texts.append("\n".join(lines).strip())
            slide_images.append(images)

        total_images = sum(len(imgs) for imgs in slide_images)
        ocr_by_slide: List[List[str]] = [[] for _ in slide_images]
        if total_images:
            print(f"{prefix}OCR modeli yukleniyor ({total_images} gomulu resim icin)")
            with FalconOCR() as ocr:
                for i, imgs in enumerate(slide_images):
                    for img in imgs:
                        try:
                            ocr_by_slide[i].append(ocr.extract_text(img, mode="plain"))
                        except Exception as e:
                            print(f"{prefix}OCR hatasi (slide {i}): {e}")
                            ocr_by_slide[i].append("")
            print(f"{prefix}OCR modeli indirildi, VRAM bosaltildi")

        docs = []
        for i, text in enumerate(slide_texts):
            image_texts = [t for t in ocr_by_slide[i] if t.strip()]
            combined = "\n".join([p for p in [text] + image_texts if p]).strip()
            if combined:
                docs.append(Document(page_content=combined, metadata={"page": i}))
        return docs


def _convert_legacy_office(file_path: str, target_ext: str) -> str:
    """LibreOffice headless ile bir office dosyasini baska bir formata cevirir.

    Iki kullanim yeri var:
      1) .doc -> .docx / .ppt -> .pptx (eski OLE2 formatlarini _get_loader'in
         okuyabilecegi formata getirmek icin, target_ext=".docx"/".pptx").
      2) generate_preview_pdf() icinde, ALLOWED_EXT'teki hemen her office
         formatini dogrudan PDF'e cevirmek icin (target_ext=".pdf").

    Basarisizsa RuntimeError firlatir, caller (yukarida (1) icin _get_loader,
    (2) icin generate_preview_pdf) bunu yakalayip anlamli bir hata mesaji verir.
    """
    tmpdir = tempfile.mkdtemp(prefix="legacy_office_")
    try:
        result = subprocess.run(
            [
                "soffice", "--headless", "--norestore",
                "--convert-to", target_ext.lstrip("."),
                "--outdir", tmpdir,
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice donusturme basarisiz (code={result.returncode}): "
                f"{result.stderr.strip()}"
            )
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        converted_path = os.path.join(tmpdir, f"{base_name}{target_ext}")
        if not os.path.exists(converted_path):
            raise RuntimeError(
                f"Donusturme sonrasi beklenen dosya bulunamadi: {converted_path}"
            )
        return converted_path
    except FileNotFoundError:
        raise RuntimeError(
            "LibreOffice (soffice) sistemde kurulu degil. "
            "'sudo apt-get install -y libreoffice' ile kur."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("LibreOffice donusturme zaman asimina ugradi (60sn).")


def _get_loader(file_path: str, room_id: str = ""):
    """Uzantiya gore .load() -> List[Document] dondüren loader secer.
    Bu fonksiyon SADECE pdf/resim/docx/doc DISINDAKI formatlar icin cagrilir
    (pdf ve resimler extract_documents() icinde, docx/doc ise
    _extract_docx_documents() icinde Falcon-OCR fallback'iyle birlikte
    ayrica ele alinir). .ppt (eski binary OLE2 format) icin once LibreOffice
    ile .pptx'e donusturulur, sonra ayni loader kullanilir."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".md", ".txt"):
        return TextLoader(file_path, encoding="utf-8")
    if ext == ".pptx":
        return _PptxLoader(file_path, room_id=room_id)
    if ext == ".ppt":
        converted = _convert_legacy_office(file_path, ".pptx")
        return _PptxLoader(converted, room_id=room_id)
    raise ValueError(f"Desteklenmeyen dosya formati: {ext}")


def _extract_images_from_docx(docx_path: str) -> List:
    """.docx bir zip arsividir; gomulu resimler word/media/ altinda durur.
    python-docx gibi ekstra bir bagimliliga gerek kalmadan dogrudan zipfile
    ile okunur. Sirasi belgedeki gomulu-resim sirasiyla ayni olmayabilir
    (Word media dosyalarini kendi ic sirasina gore adlandirir) - "hangi
    resim nerede" onemli degil, hepsinin metni ayni belgeye ekleniyor."""
    import zipfile
    import io
    from PIL import Image

    images = []
    try:
        with zipfile.ZipFile(docx_path) as z:
            for name in sorted(z.namelist()):
                if name.startswith("word/media/"):
                    try:
                        images.append(Image.open(io.BytesIO(z.read(name))).convert("RGB"))
                    except Exception:
                        continue  # media/ altinda resim olmayan bir dosya (ornegin .emf) olabilir
    except Exception as e:
        print(f"docx gomulu resimleri okunamadi ({docx_path}): {e}")
    return images


def _ocr_images(images: List, log_prefix: str = "") -> List[str]:
    """Bir PIL.Image listesini TEK FalconOCR context'i icinde OCR'lar,
    metinleri (basarisiz olanlar icin bos string) sirali doner."""
    if not images:
        return []
    texts: List[str] = []
    print(f"{log_prefix}OCR modeli yukleniyor ({len(images)} gomulu resim icin)")
    with FalconOCR() as ocr:
        for img in images:
            try:
                texts.append(ocr.extract_text(img, mode="plain"))
            except Exception as e:
                print(f"{log_prefix}OCR hatasi (gomulu resim): {e}")
                texts.append("")
    print(f"{log_prefix}OCR modeli indirildi, VRAM bosaltildi")
    return texts


def _extract_docx_documents(display_path: str, docx_path: str, room_id: str = "") -> List[Document]:
    """.docx (veya .doc'tan LibreOffice ile donusturulmus .docx) icin hem
    duz metni (Docx2txtLoader) hem de belgeye GOMULU RESIMLERIN OCR metnini
    tek bir Document listesinde birlestirir.

    Word "sayfa" bilgisini erisilebilir sekilde saklamadigi icin metin
    Document'i ve her gomulu resmin OCR Document'i ayri Document'ler olarak
    donulur; caller (rag_chat.py) split sonrasi sequential chunk_index'i
    "page" gibi kullanir - bu yuzden burada page metadata'sina gerek yok."""
    prefix = f"[{room_id}] " if room_id else ""

    text_docs = Docx2txtLoader(docx_path).load()

    images = _extract_images_from_docx(docx_path)
    ocr_texts = _ocr_images(images, log_prefix=prefix)

    source_name = os.path.basename(display_path)
    image_docs = [
        Document(page_content=t, metadata={"source": source_name, "kind": "image_ocr"})
        for t in ocr_texts
        if t.strip()
    ]

    return text_docs + image_docs


def _ocr_fallback_for_pdf_pages(pdf_path: str, page_nums: List[int], log_prefix: str = "") -> Dict[int, str]:
    """Taranmis (metin katmani yok/az) PDF sayfalari icin Falcon-OCR fallback.

    page_nums bos ise FalconOCR HIC yuklenmez (VRAM'e dokunulmaz). Doluysa
    TEK bir `with FalconOCR() as ocr:` blogu icinde listedeki TUM sayfalar
    sirayla islenir - her sayfa icin ayri context acip kapatmak hem yavas
    olur hem gereksiz yukleme/indirme dongusu yaratir, o yuzden yukleme/
    indirme tam olarak bu fonksiyonun basinda/sonunda bir kere olur."""
    if not page_nums:
        return {}

    import fitz
    from PIL import Image

    results: Dict[int, str] = {}
    print(f"{log_prefix}OCR modeli yukleniyor ({len(page_nums)} sayfa icin)")
    with FalconOCR() as ocr:
        with fitz.open(pdf_path) as doc:
            for page_num in page_nums:
                if page_num < 0 or page_num >= len(doc):
                    continue
                pix = doc[page_num].get_pixmap(dpi=200)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                try:
                    results[page_num] = ocr.extract_text(image, mode="plain")
                except Exception as e:
                    print(f"{log_prefix}OCR hatasi (sayfa {page_num}): {e}")
                    results[page_num] = ""
    print(f"{log_prefix}OCR modeli indirildi, VRAM bosaltildi")
    return results


def extract_documents(file_path: str, room_id: str = "") -> List[Document]:
    """Dosyayi (ALLOWED_EXT'teki herhangi bir format) List[Document]'e cevirir.
    RAG tarafinin (rag_chat.py) tek metin-cikarma girisi budur.

    - .pdf: PyMuPDFLoader ile once normal metni cikarir, sonra taranmis
      (metin katmani yok/az) sayfalari tespit eder (strip() sonrasi
      _OCR_FALLBACK_MIN_CHARS karakterden az metin -> OCR'a dusecek aday
      sayfa) ve bunlari TEK bir FalconOCR context'i icinde OCR'lar.
    - resim (.jpg/.jpeg/.png): dogrudan resim yuklemesi, "sayfa" kavrami
      yok; TEK bir FalconOCR context'i icinde OCR'lanir, "page" metadata'si
      0 sabit kalir.
    - .docx (veya .doc'tan donusturulmus): Docx2txtLoader ile duz metin +
      belgeye gomulu TUM resimler TEK bir FalconOCR context'i icinde OCR'lanip
      metne eklenir (bkz. _extract_docx_documents). Word "sayfa" bilgisini
      saklamadigi icin metin ve her resmin OCR'i ayri Document olarak doner.
    - .pptx (veya .ppt'ten donusturulmus): her slide'in metni + o slide'daki
      gomulu resim(ler)in OCR'i TEK page_content'te birlesir (bkz. _PptxLoader).
    - digerleri (.md/.txt): _get_loader() dispatch'i kullanilir.

    Donen Document listesi caller'da (rag_chat.py) dogrudan text splitter'a
    verilir; "page" metadata'si sadece PDF'te (PyMuPDFLoader'dan) ve resimde
    (0 sabit) anlamlidir - diger formatlarda sayfa kavrami olmadigi icin
    caller split SONRASI sequential chunk_index'i "page" gibi kullanir.
    """
    ext = os.path.splitext(file_path)[1].lower()
    prefix = f"[{room_id}] " if room_id else ""

    if ext == ".pdf":
        loader = PyMuPDFLoader(file_path)
        docs = loader.load()
        ocr_page_nums = [
            d.metadata.get("page", i)
            for i, d in enumerate(docs)
            if len(d.page_content.strip()) < _OCR_FALLBACK_MIN_CHARS
        ]
        if ocr_page_nums:
            ocr_texts = _ocr_fallback_for_pdf_pages(file_path, ocr_page_nums, log_prefix=prefix)
            for d in docs:
                page = d.metadata.get("page")
                ocr_text = ocr_texts.get(page)
                if ocr_text:
                    d.page_content = ocr_text
        return docs

    if ext in IMAGE_EXTS:
        from PIL import Image

        print(f"{prefix}OCR modeli yukleniyor (1 sayfa icin)")
        with FalconOCR() as ocr:
            image = Image.open(file_path).convert("RGB")
            try:
                ocr_text = ocr.extract_text(image, mode="plain")
            except Exception as e:
                print(f"{prefix}OCR hatasi: {e}")
                ocr_text = ""
        print(f"{prefix}OCR modeli indirildi, VRAM bosaltildi")
        return [Document(page_content=ocr_text, metadata={"page": 0})] if ocr_text.strip() else []

    if ext == ".docx":
        return _extract_docx_documents(file_path, file_path, room_id=room_id)
    if ext == ".doc":
        converted = _convert_legacy_office(file_path, ".docx")
        return _extract_docx_documents(file_path, converted, room_id=room_id)

    loader = _get_loader(file_path, room_id=room_id)
    return loader.load()


def extract_pdf_page_text(pdf_path: str, page_num: int, max_chars: int = 3000) -> Optional[str]:
    """Citation fallback'i icin: PDF'in belirli bir sayfasinin duz metnini
    cikarir (fitz ile). rag_chat.py'deki RagRoom.get_page_text'in eski
    fitz-tabanli PDF kolu buraya tasindi; PDF-disi formatlardaki
    vectorstore-tabanli fallback rag_chat.py'de kaliyor - o kisim OCR/
    metin-cikarma degil, RAG/vectorstore-spesifik bir sorgu."""
    if page_num is None:
        return None
    try:
        import fitz
        with fitz.open(pdf_path) as doc:
            if page_num < 0 or page_num >= len(doc):
                return None
            text = doc[page_num].get_text().strip()
            if not text:
                return None
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            return text
    except Exception as e:
        print(f"PDF sayfa metni okunamadi ({pdf_path}, sayfa {page_num}): {e}")
        return None


def generate_preview_pdf(source_path: str, output_pdf_path: str) -> str:
    """Kaynak dosyayi (ALLOWED_EXT'teki hangi formatta olursa olsun) frontend'de
    "PDF olarak indir/goruntule" icin TEK bir PDF dosyasina cevirip
    output_pdf_path'e yazar ve bu yolu doner.

    - .pdf            -> zaten PDF, dogrudan kopyalanir.
    - resim (.jpg/.jpeg/.png) -> Pillow ile tek sayfalik "ekran goruntusu"
      PDF'ine cevrilir.
    - .docx/.doc/.pptx/.ppt/.txt/.md -> LibreOffice headless ile PDF'e
      donusturulur (ayni --convert-to mekanizmasi, _convert_legacy_office
      uzerinden, target_ext=".pdf").

    Basarisiz olursa RuntimeError/ValueError firlatir; caller (rag_chat.py:
    create_room_from_upload) bunu yakalayip preview'siz devam edebilir
    (frontend'de "PDF onizleme yok" durumu - oda olusturma BASARISIZ SAYILMAZ).
    """
    ext = os.path.splitext(source_path)[1].lower()
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

    if ext == ".pdf":
        shutil.copy(source_path, output_pdf_path)
        return output_pdf_path

    if ext in IMAGE_EXTS:
        from PIL import Image

        image = Image.open(source_path).convert("RGB")
        image.save(output_pdf_path, "PDF")
        return output_pdf_path

    if ext in _LIBREOFFICE_CONVERTIBLE_EXT:
        converted = _convert_legacy_office(source_path, ".pdf")
        shutil.copy(converted, output_pdf_path)
        return output_pdf_path

    raise ValueError(f"Onizleme PDF'i uretilemez, desteklenmeyen format: {ext}")