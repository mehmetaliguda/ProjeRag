"""
ocr_utils.py
------------
Taranmis/gorsel sayfalar icin Falcon-OCR (tiiuae/Falcon-OCR) fallback'ini
saran, VRAM yasam donguresunu elle yoneten yardimci modul.

NOT (model karti dogrulamasi): huggingface.co/tiiuae/Falcon-OCR resmi
"Use this model" ornegine gore bu model icin AYRI bir processor YOK.
Sadece `AutoModelForCausalLM.from_pretrained(..., trust_remote_code=True)`
ile yukleniyor ve PIL.Image'i dogrudan `model.generate(image, category=...)`
ile isliyor; cikti `list[str]`. Asagida `self.processor` alani yine de
tutuluyor (ileride gercek bir processor gerektiren bir surume gecilirse
cagiran taraflarin sozlesmesi kirilmasin diye), ama bu modelde daima None.

Kullanim (dotenv_rag.py'deki get_env_variable deseniyle tutarli):
    from ocr_utils import FalconOCR

    with FalconOCR() as ocr:
        text = ocr.extract_text(pil_image)   # tek sayfa
        text2 = ocr.extract_text(pil_image2)  # ayni yukleme icinde bir sayfa daha
    # blok bitince model otomatik GPU'dan iner
"""

import gc
from typing import List, Optional

from dotenv_rag import get_env_variable

FALCON_OCR_MODEL_ID = get_env_variable("FALCON_OCR_MODEL_ID", "tiiuae/Falcon-OCR")

# Model karti "Choose an output format" bolumunde listelenen gecerli
# category degerleri (mode="layout" ayri bir API'ye -> generate_with_layout).
_VALID_PLAIN_CATEGORIES = {
    "plain", "text", "table", "formula", "caption", "footnote",
    "list-item", "page-footer", "page-header", "section-header", "title",
}


class FalconOCR:
    """Falcon-OCR modelinin GPU yasam donguresunu yoneten sarmalayici.

    Context manager olarak kullanilir (girişte yukler, çıkışta indirir):
        with FalconOCR() as ocr:
            ...

    _load()/_unload() ayri ayri da cagrilabilir; bir job sirasinda birden
    fazla sayfa varsa cagiran taraf TEK context acip hepsini icinde
    islemeli (bkz. rag_chat.py _ocr_fallback_for_pages), aksi halde her
    sayfada ayri yukleme/indirme cok yavas olur.
    """

    def __init__(self, model_id: str = FALCON_OCR_MODEL_ID):
        self.model_id = model_id
        self.model = None
        self.processor = None  # bu modelde kullanilmiyor, yukaridaki NOT'a bak
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        import torch
        from transformers import AutoModelForCausalLM

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        self._loaded = True

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
        donguresunu caller (rag_chat.py) kontrol etmeli.
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