# RAG Sistemi (Çoxlu Mənbə Dəstəkli)

Bu layihə tamamilə lokal olaraq işləyən **Retrieval-Augmented Generation (RAG)** sistemidir. PDF, Word, PowerPoint, şəkil, mətn və MSSQL verilənlər bazası kimi müxtəlif mənbələrdən istifadə edərək təbii dildə suallar verə və sənədlərə əsaslanan cavablar ala bilərsiniz.

Sistem tamamilə **lokal** işləyir; LLM, embedding və OCR modelləri **Ollama** və **Hugging Face** vasitəsilə yüklənir və heç bir məlumat xaricə göndərilmir.

---

## Mündəricat

1. [Ümumi Memarlıq](#ümumi-memarlıq)
2. [İstifadə Olunan Texnologiyalar və Modellər](#istifadə-olunan-texnologiyalar-və-modellər)
3. [Quraşdırma](#quraşdırma)
   - [Ön Şərtlər](#ön-şərtlər)
   - [Backend Quraşdırılması](#backend-quraşdırılması)
   - [Frontend Quraşdırılması](#frontend-quraşdırılması)
   - [Ollama Modellərinin Yüklənməsi](#ollama-modellərinin-yüklənməsi)
   - [Ətraf Mühit Dəyişənləri (.env)](#ətraf-mühit-dəyişənləri-env)
4. [İşə Salma](#işə-salma)
5. [İstifadə](#istifadə)
   - [Notebook Yaratma və Fayl Yükləmə](#notebook-yaratma-və-fayl-yükləmə)
   - [Sual Sorma (RAG)](#sual-sorma-rag)
   - [MSSQL Verilənlər Bazasına Qoşulma](#mssql-verilənlər-bazasına-qoşulma)
6. [Dəstəklənən Fayl Formatları](#dəstəklənən-fayl-formatları)
7. [Problem Həlli](#problem-həlli)
8. [Təhlükəsizlik Qeydləri](#təhlükəsizlik-qeydləri)

---

## Ümumi Memarlıq

Layihə iki əsas hissədən ibarətdir:

- **Frontend**: Next.js (React) əsaslı veb interfeys. İstifadəçilər notebook yaradır, fayl yükləyir, söhbət edir və MSSQL konfiqurasiyası edir.
- **Backend**: Flask (Python) əsaslı REST API. RAG mühərriki, sənəd indeksləmə, vektor axtarışı, MSSQL bağlantısı və LLM ilə cavab yaratma əməliyyatlarını icra edir.

Backend daxilində:
- **SQLite** verilənlər bazası (`app.db`) notebook, conversation, room və MSSQL config məlumatlarını saxlayır.
- **Chroma** vektor verilənlər bazası, hər bir sənəd otağı üçün ayrıca qovluqda vektorları saxlayır.
- **LangChain / LangGraph** RAG pipeline'ını idarə edir.
- **Hibrid Retriever** (BM25 + semantik axtarış) və **CrossEncoderReranker** ilə ən uyğun hissələr seçilir.

---

## İstifadə Olunan Texnologiyalar və Modellər

| Məqsəd | Texnologiya / Model |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| **Veb Framework (Backend)** | Flask 3.0 |
| **Veb Framework (Frontend)** | Next.js 16 + React 19 + Tailwind CSS 4 |
| **Vektor Verilənlər Bazası** | Chroma (langchain-chroma) |
| **Embedding Modeli** | `bge-m3` (OllamaEmbeddings ilə) |
| **LLM (Cavab Yaratma)** | `qwen2.5:7b-instruct` (Ollama ilə, həmçinin query optimizer və reranker-da istifadə olunur) |
| **OCR Modeli** | `tiiuae/Falcon-OCR` (Hugging Face transformers, şəkil və skan edilmiş PDF'lər üçün) |
| **PDF İşləmə** | PyMuPDF (fitz) + LangChain PyMuPDFLoader; skan edilmiş səhifələr üçün Falcon-OCR fallback |
| **Verilənlər Bazası** | SQLite (Flask-SQLAlchemy) |
| **MSSQL Bağlantısı** | `pyodbc` + `ODBC Driver 18 for SQL Server` |
| **Şifrələmə** | Fernet (cryptography) ilə MSSQL parolu şifrələnir |
| **Fayl Dönüşümləri** | LibreOffice (headless) köhnə .doc/.ppt və .docx/.pptx-i PDF-ə çevirir |

---

## Quraşdırma

### Ön Şərtlər

- **Python 3.10+** (backend)
- **Node.js 20+** və **pnpm** və ya **npm** (frontend)
- **Ollama** yüklü və işlək vəziyyətdə ([ollama.com](https://ollama.com))
- **LibreOffice** – bəzi fayl formatlarının PDF-ə çevrilməsi üçün:
  - Ubuntu/Debian: `sudo apt-get install -y libreoffice`
  - Windows/macOS: [LibreOffice yüklə](https://www.libreoffice.org/download/)
- **ODBC Driver 18 for SQL Server** (MSSQL istifadə edəcəksinizsə):
  - Microsoft-un rəsmi quraşdırma təlimatları: [Linux](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server), [Windows](https://learn.microsoft.com/sql/connect/odbc/windows/system-requirements-installation-and-driver-files)
- **Git** (opsional)

### Backend Quraşdırılması

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Quraşdırılması

Layihə kök qovluğundan:

```bash
pnpm install     # və ya npm install
```

### Ollama Modellərinin Yüklənməsi

Ollama-ya başlamazdan əvvəl lazımi modelləri yükləyin:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b-instruct
```

> **Qeyd:** `bge-m3` embedding, `qwen2.5:7b-instruct` isə cavab yaratma və yenidən sıralama üçün istifadə olunur. Model ölçüləri böyük ola bilər (bge-m3 ~1.2GB, qwen2.5:7b ~4.7GB).

OCR modeli **Ollama-da yoxdur**; Hugging Face-dən avtomatik yüklənir (ilk istifadədə). İstəsəniz əl ilə də yükləyə bilərsiniz:

```bash
python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')"
```

### Ətraf Mühit Dəyişənləri (.env)

Backend, `backend/rag.env` faylından ayarları oxuyur. Aşağıdakı məzmunla bir `rag.env` yaradın:

```ini
# Ollama ayarları
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Embedding modeli
EMBED_MODEL=bge-m3

# Vektor verilənlər bazası qovluğu
RAG_ROOMS_ROOT=./rag_rooms

# MSSQL şifrələmə açarı (Fernet)
# Yeni açar yaratmaq üçün:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MSSQL_ENC_KEY=buraya_yaradılan_açar

# MSSQL ODBC sürücüsü (standart: ODBC Driver 18 for SQL Server)
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# OCR modeli (opsional)
FALCON_OCR_MODEL_ID=tiiuae/Falcon-OCR
FALCON_OCR_LOCAL_PATH=./models/falcon-ocr

# İsteğe bağlı digər ayarlar
APP_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///app.db
```

**Əhəmiyyətli:** `MSSQL_ENC_KEY` olmadan MSSQL bağlantısı qurula bilməz. Boş qoyularsa, proqram xəta verir.

---

## İşə Salma

### 1. Ollama-ya başlayın

```bash
ollama serve
```

Xidmətin işlədiyini yoxlamaq üçün:

```bash
curl http://localhost:11434
```

və ya brauzerdə `http://localhost:11434` ünvanına gedin.

### 2. Backend-i başladın

Yeni bir terminalda:

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
flask --app app.py run
```

Backend standart olaraq `http://127.0.0.1:5000` ünvanında dinləyir.

### 3. Frontend-i başladın

Başqa bir terminalda (layihə kök qovluğunda):

```bash
npm run dev
```

və ya

```bash
pnpm run dev
```

Frontend `http://localhost:3000` ünvanında açılır.

---

## İstifadə

### Notebook Yaratma və Fayl Yükləmə

1. Brauzerdə `http://localhost:3000` ünvanına gedin.
2. Sağ yuxarıdakı **"New Notebook"** düyməsinə klikləyin və bir ad verin.
3. Notebook-a klikləyərək söhbət səhifəsinə keçin.
4. Sol paneldə **"Sources"** bölməsindən faylı sürükləyib buraxa və ya **"Drop files here"** sahəsinə klikləyib fayl seçə bilərsiniz.
5. Yüklənən sənədlər avtomatik olaraq vektor verilənlər bazasına əlavə olunur və **seçili** vəziyyətə gəlir. Birdən çox sənədi seçərək eyni anda sorğulaya bilərsiniz.

### Sual Sorma (RAG)

- Söhbət ekranında sualınızı yazın və Enter-ə basın.
- Sistem əvvəlcə vektor axtarışı aparır, ən uyğun hissələri seçir və **qwen2.5:7b-instruct** ilə cavab yaradır.
- Cavablarda `[[c:N]]` etiketləri ilə mənbə göstərilir; klikləyərək sitat gətirilən səhifəni/mətni görə bilərsiniz.

### MSSQL Verilənlər Bazasına Qoşulma

MSSQL-i notebook-a bağlamaq üçün:

1. Ana səhifədəki **"Data Sources"** bölməsində notebook-u seçin.
2. **MSSQL Configuration** panelində aşağıdakı sahələri doldurun:
   1. **Server** – Server adı və ya IP
   2. **Port** – Adətən 1433
   3. **Database Name** – Verilənlər bazası adı
   4. **Username** – İstifadəçi adı
   5. **Password** – Şifrə (yeniləmədə boş qoyularsa köhnə şifrə qorunur)
   6. **Table Name** – Sorğulanacaq cədvəl adı
   7. **Timestamp Column** – Zaman damğası sütunu (ən yeni qeydlərin sıralanacağı sütun)
   8. **Text Columns** – Mətn olan sütunlar (vergüllə ayırın, məs. `message, level, source`)
3. **"Save & Test Connection"** düyməsinə basın. Backend bağlantını test edir; uğurlu olarsa yadda saxlayır.
4. Notebook-a gedin və söhbət ekranında **"SQL Source"** adlı mənbəni seçin.
5. Suallarınızı təbii dildə soruşun; sistem həm sənədlərdən, həm də MSSQL-dən gələn məlumatlarla cavab yaradır.

---

## Dəstəklənən Fayl Formatları

Aşağıdakı formatlar yüklənə və RAG-də istifadə oluna bilər:

```
.pdf   .md    .txt   .docx  .pptx  .doc   .ppt
.jpg   .jpeg  .png
```

- **PDF**: Mətn qatı varsa birbaşa oxunur; skan edilmiş/şəkil PDF-lərdə Falcon-OCR işə düşür.
- **Şəkillər**: Tam səhifə OCR ilə mətnə çevrilir.
- **Word/PowerPoint**: Mətn və daxili şəkillər ayrıca işlənir (şəkillər OCR-lanır).
- **Köhnə .doc/.ppt**: LibreOffice ilə .docx/.pptx-ə çevrilib işlənir.

---

## Problem Həlli

### Ollama bağlantı xətası

- `ollama serve` işləyir? Yoxlayın.
- `OLLAMA_BASE_URL` doğrudur? Standart `http://localhost:11434`.
- Modellər yüklənib? `ollama list` ilə yoxlayın.

### Backend başlamır

- `requirements.txt`-dəki asılılıqların yükləndiyinə əmin olun.
- `rag.env` faylının `backend/` qovluğunda olduğunu yoxlayın.
- SQLite faylı (`app.db`) yaradıla bilsin deyə qovluq yazma icazəsi verin.

### MSSQL bağlantı xətası

- `MSSQL_ENC_KEY` müəyyən edilib və etibarlı Fernet açarıdır?
- ODBC Driver 18 yüklənib?
- Server, port, verilənlər bazası adı və cədvəl adı doğrudur?
- Cədvəl/sütun adlarında xüsusi simvol və ya boşluq olmamalıdır (yalnız hərf, rəqəm və `_`).

### LibreOffice xətası

Bəzi formatların PDF-ə çevrilməsi üçün `soffice` əmri lazımdır. Yüklü deyilsə:

```bash
sudo apt-get install -y libreoffice
```

### OCR yavaş və ya GPU xətası

Falcon-OCR modeli böyükdür; CPU-da yavaş işləyə bilər. GPU yoxsa səbirli olun və ya daha kiçik bir OCR modeli istifadə edin.

---

## Təhlükəsizlik Qeydləri

- MSSQL şifrəsi **Fernet** ilə şifrələnərək verilənlər bazasında saxlanılır, API heç vaxt şifrəni qaytarmır.
- SQL sorğularında cədvəl/sütun adları sərt bir ağ siyahı ilə doğrulanır (injection qarşısı alınır).
- Sistem tamamilə lokal işləyir; sənədləriniz və sorğularınız xaricə sızmır.
- Yenə də həssas məlumatlarla istifadə edərkən şəbəkə girişini məhdudlaşdırmaq tövsiyə olunur.

---