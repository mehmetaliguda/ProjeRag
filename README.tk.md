# RAG Sistemi (Köp Çeşmeli Goldaw)

Bu taslama düýbünden ýerli ýagdaýda işleýän **Retrieval-Augmented Generation (RAG)** ulgamydyr. PDF, Word, PowerPoint, surat, tekst faýllary we MSSQL maglumat bazasy ýaly dürli çeşmeleri ulanyp, tebigy dilde soraglar berip, resminamalara esaslanan jogap alyp bilersiňiz.

Ulgam düýbünden **ýerli** işleýär; LLM, embedding we OCR modelleri **Ollama** we **Hugging Face** arkaly ýüklenýär we hiç hili maglumat daşary iberilmeýär.

---

## Mündewrijat

1. [Umumy Arhitektura](#umumy-arhitektura)
2. [Ulanylýan Tehnologiýalar we Modeller](#ulanylýan-tehnologiýalar-we-modeller)
3. [Gurnama](#gurnama)
   - [Öňünden Talaplar](#öňünden-talaplar)
   - [Backend Gurnama](#backend-gurnama)
   - [Frontend Gurnama](#frontend-gurnama)
   - [Ollama Modellerini Ýüklemek](#ollama-modellerini-ýüklemek)
   - [Daşky Gurşaw Üýtgeýjileri (.env)](#daşky-gurşaw-üýtgeýjileri-env)
4. [Programmany Işe Başlamak](#programmany-işe-başlamak)
5. [Ulanylyşy](#ulanylyşy)
   - [Notebook Döretmek we Faýllary Ýüklemek](#notebook-döretmek-we-faýllary-ýüklemek)
   - [Sorag Bermek (RAG)](#sorag-bermek-rag)
   - [MSSQL Maglumat Bazasyna Birikmek](#mssql-maglumat-bazasyna-birikmek)
6. [Goldanylýan Faýl Formatlary](#goldanylýan-faýl-formatlary)
7. [Meseleleri Çözmek](#meseleleri-çözmek)
8. [Howpsuzlyk Bellikleri](#howpsuzlyk-bellikleri)

---

## Umumy Arhitektura

Taslama iki esasy bölekden durýar:

- **Frontend**: Next.js (React) esasly web interfeýs. Ulanyjylar notebook döredýär, faýl ýükleýär, gürleşýär we MSSQL konfigurasiýasyny edýär.
- **Backend**: Flask (Python) esasly REST API. RAG hereketlendirijisi, resminamalary indekslemek, wektor gözlegi, MSSQL birikmesi we LLM arkaly jogap döretmek amallaryny ýerine ýetirýär.

Backend içinde:
- **SQLite** maglumat bazasy (`app.db`) notebook, gürleşme, otag we MSSQL konfig maglumatlaryny saklaýar.
- **Chroma** wektor maglumat bazasy, her bir resminama otagy üçin aýry bukja içinde wektorlary saklaýar.
- **LangChain / LangGraph** RAG pipeline'yny dolandyrýar.
- **Gibrid Retriever** (BM25 + semantik gözleg) we **CrossEncoderReranker** bilen iň laýyk bölekler saýlanýar.

---

## Ulanylýan Tehnologiýalar we Modeller

| Maksat | Tehnologiýa / Model |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| **Web Framework (Backend)** | Flask 3.0 |
| **Web Framework (Frontend)** | Next.js 16 + React 19 + Tailwind CSS 4 |
| **Wektor Maglumat Bazasy** | Chroma (langchain-chroma) |
| **Embedding Modeli** | `bge-m3` (OllamaEmbeddings arkaly) |
| **LLM (Jogap Döretme)** | `qwen2.5:7b-instruct` (Ollama arkaly, soragy optimallaşdyrmak we täzeden tertiplemek üçin hem ulanylýar) |
| **OCR Modeli** | `tiiuae/Falcon-OCR` (Hugging Face transformers, suratlar we skanirlenen PDF'ler üçin) |
| **PDF Işlemek** | PyMuPDF (fitz) + LangChain PyMuPDFLoader; skanirlenen sahypalar üçin Falcon-OCR fallback |
| **Maglumat Bazasy** | SQLite (Flask-SQLAlchemy) |
| **MSSQL Birikmesi** | `pyodbc` + `ODBC Driver 18 for SQL Server` |
| **Şifrlemek** | Fernet (cryptography) bilen MSSQL paroly şifrlenýär |
| **Faýl Öwürmeler** | LibreOffice (headless) köne .doc/.ppt we .docx/.pptx faýlly PDF-e öwürýär |

---

## Gurnama

### Öňünden Talaplar

- **Python 3.10+** (backend)
- **Node.js 20+** we **pnpm** ýa-da **npm** (frontend)
- **Ollama** gurnalan we işleýär ([ollama.com](https://ollama.com))
- **LibreOffice** – käbir faýl formatlaryny PDF-e öwürmek üçin:
  - Ubuntu/Debian: `sudo apt-get install -y libreoffice`
  - Windows/macOS: [LibreOffice ýüklemek](https://www.libreoffice.org/download/)
- **ODBC Driver 18 for SQL Server** (eýer MSSQL ulansaňyz):
  - Microsoft-yň resmi gurnama görkezmesi: [Linux](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server), [Windows](https://learn.microsoft.com/sql/connect/odbc/windows/system-requirements-installation-and-driver-files)
- **Git** (hökman däl)

### Backend Gurnama

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Gurnama

Taslamanyň kök bukjasyndan:

```bash
pnpm install     # ýa-da npm install
```

### Ollama Modellerini Ýüklemek

Ollama-ny işe başlamazdan öň gerekli modelleri ýükläň:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b-instruct
```

> **Bellik:** `bge-m3` embedding üçin, `qwen2.5:7b-instruct` jogap döretmek we täzeden tertiplemek üçin ulanylýar. Model ölçegleri uly bolup biler (bge-m3 ~1.2GB, qwen2.5:7b ~4.7GB).

OCR modeli **Ollama-da ýok**; Hugging Face-den awtomatik ýüklenýär (ilkinji gezek ulanylanda). Ise görä el bilen hem ýükläp bilersiňiz:

```bash
python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')"
```

### Daşky Gurşaw Üýtgeýjileri (.env)

Backend, `backend/rag.env` faýlyndan sazlamalary okaýar. Aşakdaky mazmun bilen `rag.env` faýlyny dörediň:

```ini
# Ollama sazlamalary
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Embedding modeli
EMBED_MODEL=bge-m3

# Wektor maglumat bazasy bukjasy
RAG_ROOMS_ROOT=./rag_rooms

# MSSQL şifrleme açary (Fernet)
# Täze açary döretmek üçin:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MSSQL_ENC_KEY=bu_ýerde_döredilen_açar

# MSSQL ODBC sürüjisi (öwrenişen: ODBC Driver 18 for SQL Server)
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# OCR modeli (hökman däl)
FALCON_OCR_MODEL_ID=tiiuae/Falcon-OCR
FALCON_OCR_LOCAL_PATH=./models/falcon-ocr

# Islege görä goşmaça sazlamalar
APP_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///app.db
```

**Möhüm:** `MSSQL_ENC_KEY` bolmasa, MSSQL birikmesi gurulmaýar. Boş goýsaňyz, programma ýalňyş berýär.

---

## Programmany Işe Başlamak

### 1. Ollama-ny işe başlaň

```bash
ollama serve
```

Hyzmatyň işleýändigini barlamak üçin:

```bash
curl http://localhost:11434
```

ýa-da brauzerde `http://localhost:11434` salgysyna gidiň.

### 2. Backend-i işe başlaň

Täze terminalda:

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
flask --app app.py run
```

Backend öwrenişen ýagdaýda `http://127.0.0.1:5000` salgysynda diňleýär.

### 3. Frontend-i işe başlaň

Başga terminalda (taslamanyň kök bukjasyndan):

```bash
npm run dev
```

ýa-da

```bash
pnpm run dev
```

Frontend `http://localhost:3000` salgysynda açylýar.

---

## Ulanylyşy

### Notebook Döretmek we Faýllary Ýüklemek

1. Brauzerde `http://localhost:3000` salgysyna gidiň.
2. Ýokarky sag tarapdaky **"New Notebook"** düwmesine basyň we at beriň.
3. Notebook-a basyp, gürleşme sahypasyna geçiň.
4. Çep panelde **"Sources"** bölüminden faýly süýräp taşlaň ýa-da **"Drop files here"** meýdanyna basyp, faýllary saýlaň.
5. Ýüklenen resminamalar awtomatik wektor maglumat bazasyna goşulýar we **saýlanan** ýagdaýa gelýär. Birnäçe resminamany saýlap, bir wagtyň özünde sorag edip bilersiňiz.

### Sorag Bermek (RAG)

- Gürleşme ekranynda soragyňyzy ýazyň we Enter basyň.
- Ulgam ilki wektor gözlegini geçirýär, iň laýyk bölekleri saýlaýar we **qwen2.5:7b-instruct** bilen jogap döredýär.
- Jogaplarda `[[c:N]]` bellikleri bilen çeşme görkezilýär; basyp, sitat getirilen sahypany/teksti görüp bilersiňiz.

### MSSQL Maglumat Bazasyna Birikmek

MSSQL-i notebook-a birikdirmek üçin:

1. Esasy sahypadaky **"Data Sources"** bölüminde notebook-y saýlaň.
2. **MSSQL Configuration** panelinde aşakdaky meýdanlary dolduryň:
   1. **Server** – Server ady ýa-da IP
   2. **Port** – Adatça 1433
   3. **Database Name** – Maglumat bazasynyň ady
   4. **Username** – Ulanyjy ady
   5. **Password** – Parol (täzelände boş goýsaňyz, köne parol saklanýar)
   6. **Table Name** – Sorag ediljek tablisanyň ady
   7. **Timestamp Column** – Wagt belligi sütüni (iň täze ýazgylary tertiplemek üçin)
   8. **Text Columns** – Tekstli sütünler (ot belligi bilen aýyryň, mys. `message, level, source`)
3. **"Save & Test Connection"** düwmesine basyň. Backend birikmani barlaýar; üstünlikli bolsa saklaýar.
4. Notebook-a gidiň we gürleşme ekranynda **"SQL Source"** atly çeşmäni saýlaň.
5. Soraglaryňyzy tebigy dilde beriň; ulgam hem resminamalardan, hem MSSQL-den gelen maglumatlar bilen jogap döredýär.

---

## Goldanylýan Faýl Formatlary

Aşakdaky formatlar ýüklenip, RAG-da ulanylyp bilner:

```
.pdf   .md    .txt   .docx  .pptx  .doc   .ppt
.jpg   .jpeg  .png
```

- **PDF**: Tekst gatlagy bar bolsa göni okalýar; skanirlenen/suratly PDF'lerde Falcon-OCR işe girýär.
- **Suratlar**: Doly sahypa OCR arkaly texte öwrülýär.
- **Word/PowerPoint**: Tekst we içindäki suratlar aýratyn işlenýär (suratlar OCR edilýär).
- **Köne .doc/.ppt**: LibreOffice arkaly .docx/.pptx-e öwrülip işlenýär.

---

## Meseleleri Çözmek

### Ollama birikme ýalňyşy

- `ollama serve` işleýärmi? Barlaň.
- `OLLAMA_BASE_URL` dogrymy? Öwrenişen `http://localhost:11434`.
- Modeller ýüklendimi? `ollama list` bilen barlaň.

### Backend işe başlamaýar

- `requirements.txt`-däki baglylyklaryň gurnalanydygyny barlaň.
- `rag.env` faýlynyň `backend/` bukjasynyň içinde bardygyny barlaň.
- SQLite faýly (`app.db`) döredilip bilinmegi üçin bukja ýazmak rugsadyny beriň.

### MSSQL birikme ýalňyşy

- `MSSQL_ENC_KEY` kesgitlenenmi we ygtybarly Fernet açarymy?
- ODBC Driver 18 gurnalanymy?
- Server, port, maglumat bazasynyň ady we tablisanyň ady dogrymy?
- Tablisa/sütün atlarynda aýratyn nyşanlar ýa-da boşluk bolmaly däl (diňe harplar, sanlar we `_`).

### LibreOffice ýalňyşy

Käbir formatlary PDF-e öwürmek üçin `soffice` buýrugy gerek. Gurnalan bolmasa:

```bash
sudo apt-get install -y libreoffice
```

### OCR haýal ýa-da GPU ýalňyşy

Falcon-OCR modeli uly; CPU-da haýal işläp biler. GPU bolmasa, sabyr ediň ýa-da kiçiräk OCR modelini ulanyň.

---

## Howpsuzlyk Bellikleri

- MSSQL paroly **Fernet** bilen şifrlenip, maglumat bazasynda saklanýar; API hiç haçan paroly yzyna gaýtarmaýar.
- SQL soraglarynda tablisa/sütün atlary gaty ak sanaw bilen barlanýar (inýeksiýanyň öňüni alýar).
- Ulgam düýbünden ýerli işleýär; resminamalaryňyz we soraglaryňyz daşary çykmaýar.
- Şeýle-de bolsa, duýgur maglumatlar bilen ulanylanda, tor girişini çäklendirmek maslahat berilýär.

---