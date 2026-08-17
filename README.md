# RAG Sistemi (Çoklu Kaynak Destekli)

Bu proje, kullanıcıların yerel olarak çalıştırdığı bir **Retrieval-Augmented Generation (RAG)** sistemidir. PDF, Word, PowerPoint, resim, metin ve MSSQL veritabanı gibi çeşitli kaynakları kullanarak doğal dilde sorular sorabilir ve belgelere dayalı cevaplar alabilirsiniz.

Sistem tamamen **yerel** çalışır; LLM, embedding ve OCR modelleri **Ollama** ve **Hugging Face** üzerinden indirilir ve hiçbir veri dışarı gönderilmez.

---

## İçindekiler

1. [Genel Mimari](#genel-mimari)
2. [Kullanılan Teknolojiler ve Modeller](#kullanılan-teknolojiler-ve-modeller)
3. [Kurulum](#kurulum)
   - [Ön Gereksinimler](#ön-gereksinimler)
   - [Backend Kurulumu](#backend-kurulumu)
   - [Frontend Kurulumu](#frontend-kurulumu)
   - [Ollama Model İndirme](#ollama-model-indirme)
   - [Ortam Değişkenleri (.env)](#ortam-değişkenleri-env)
4. [Çalıştırma](#çalıştırma)
5. [Kullanım](#kullanım)
   - [Notebook Oluşturma ve Dosya Yükleme](#notebook-oluşturma-ve-dosya-yükleme)
   - [Soru Sorma (RAG)](#soru-sorma-rag)
   - [MSSQL Veritabanı Bağlama](#mssql-veritabanı-bağlama)
6. [Desteklenen Dosya Formatları](#desteklenen-dosya-formatları)
7. [Sorun Giderme](#sorun-giderme)
8. [Güvenlik Notları](#güvenlik-notları)

---

## Genel Mimari

Proje iki ana bölümden oluşur:

- **Frontend**: Next.js (React) tabanlı bir web arayüzü. Kullanıcı notebook’lar oluşturur, dosya yükler, sohbet eder ve MSSQL yapılandırması yapar.
- **Backend**: Flask (Python) tabanlı REST API. RAG motoru, doküman indeksleme, vektör arama, MSSQL bağlantısı ve LLM ile cevap üretme işlemlerini yürütür.

Backend içinde:
- **SQLite** veritabanı (`app.db`) notebook, conversation, room ve MSSQL config bilgilerini saklar.
- **Chroma** vektör veritabanı, her belge odası için ayrı bir klasörde vektörleri tutar.
- **LangChain / LangGraph** RAG pipeline’ını yönetir.
- **Hybrid Retriever** (BM25 + semantik arama) ve **CrossEncoderReranker** ile en alakalı parçalar seçilir.

---

## Kullanılan Teknolojiler ve Modeller

| Amaç                     | Teknoloji / Model                                                                                              |
|--------------------------|----------------------------------------------------------------------------------------------------------------|
| **Web Framework (Backend)** | Flask 3.0                                                                                                     |
| **Web Framework (Frontend)** | Next.js 16 + React 19 + Tailwind CSS 4                                                                        |
| **Vektör Veritabanı**    | Chroma (langchain-chroma)                                                                                      |
| **Embedding Modeli**     | `bge-m3` (OllamaEmbeddings ile, `bge-m3` modeli)                                                               |
| **LLM (Cevap Üretimi)**  | `qwen2.5:7b-instruct` (Ollama ile, ayrıca query optimizer ve reranker’da da kullanılır)                        |
| **OCR Modeli**           | `tiiuae/Falcon-OCR` (Hugging Face transformers, görüntü ve taranmış PDF’ler için)                              |
| **PDF İşleme**           | PyMuPDF (fitz) + LangChain PyMuPDFLoader; taranmış sayfalar için Falcon-OCR fallback                           |
| **Veritabanı**           | SQLite (Flask-SQLAlchemy)                                                                                      |
| **MSSQL Bağlantısı**     | `pyodbc` + `ODBC Driver 18 for SQL Server`                                                                     |
| **Şifreleme**            | Fernet (cryptography) ile MSSQL parolası şifrelenir                                                           |
| **Dosya Dönüşümleri**    | LibreOffice (headless) eski .doc/.ppt ve .docx/.pptx’i PDF’e çevirir                                           |

---

## Kurulum

### Ön Gereksinimler

- **Python 3.10+** (backend)
- **Node.js 20+** ve **pnpm** veya **npm** (frontend)
- **Ollama** yüklü ve çalışır durumda ([ollama.com](https://ollama.com) adresinden indirilebilir)
- **LibreOffice** – bazı dosya formatlarının PDF’e dönüştürülmesi için:
  - Ubuntu/Debian: `sudo apt-get install -y libreoffice`
  - Windows/macOS: [LibreOffice indirme](https://www.libreoffice.org/download/)
- **ODBC Driver 18 for SQL Server** (MSSQL kullanacaksanız):
  - Microsoft’un resmi kurulum talimatları: [Linux](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server), [Windows](https://learn.microsoft.com/sql/connect/odbc/windows/system-requirements-installation-and-driver-files)
- **Git** (opsiyonel)

### Backend Kurulumu

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Kurulumu

Proje kök dizininde:

```bash
pnpm install     # veya npm install
```

### Ollama Model İndirme

Terminalde Ollama’yı başlatmadan önce gerekli modelleri indirin:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b-instruct
```

> **Not:** `bge-m3` embedding, `qwen2.5:7b-instruct` ise cevap üretimi ve yeniden sıralama için kullanılır. Model boyutları büyük olabilir (bge-m3 ~1.2GB, qwen2.5:7b ~4.7GB).

OCR modeli **Ollama’da yoktur**, Hugging Face’ten otomatik indirilir (ilk kullanımda). İsterseniz manuel olarak da indirebilirsiniz:

```bash
python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')"
```

### Ortam Değişkenleri (.env)

Backend, `backend/rag.env` dosyasından ayarları okur. Aşağıdaki içerikle bir `rag.env` oluşturun:

```ini
# Ollama ayarları
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Embedding modeli
EMBED_MODEL=bge-m3

# Vektör veritabanı klasörü
RAG_ROOMS_ROOT=./rag_rooms

# MSSQL şifreleme anahtarı (Fernet)
# Yeni anahtar üretmek için:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MSSQL_ENC_KEY=buraya_uretilen_anahtar

# MSSQL ODBC sürücüsü (varsayılan: ODBC Driver 18 for SQL Server)
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# OCR modeli (opsiyonel)
FALCON_OCR_MODEL_ID=tiiuae/Falcon-OCR
FALCON_OCR_LOCAL_PATH=./models/falcon-ocr

# İsteğe bağlı diğer ayarlar
APP_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///app.db
```

**Önemli:** `MSSQL_ENC_KEY` olmadan MSSQL bağlantısı kurulamaz. Boş bırakılırsa uygulama hata verir.

---

## Çalıştırma

### 1. Ollama’yı başlatın

```bash
ollama serve
```

Servisin çalıştığını kontrol etmek için:

```bash
curl http://localhost:11434
```

veya tarayıcıda `http://localhost:11434` adresine gidin.

### 2. Backend’i başlatın

Yeni bir terminalde:

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
flask --app app.py run
```

Backend varsayılan olarak `http://127.0.0.1:5000` adresinde dinler.

### 3. Frontend’i başlatın

Başka bir terminalde (proje kök dizininde):

```bash
npm run dev
```

veya

```bash
pnpm run dev
```

Frontend `http://localhost:3000` adresinde açılır.

---

## Kullanım

### Notebook Oluşturma ve Dosya Yükleme

1. Tarayıcıda `http://localhost:3000` adresine gidin.
2. Sağ üstteki **“New Notebook”** butonuna tıklayın ve bir isim verin.
3. Notebook’a tıklayarak sohbet sayfasına geçin.
4. Sol panelde **“Kaynaklar”** bölümünden dosya sürükleyip bırakabilir veya **“Dosyaları buraya sürükleyin”** alanına tıklayıp dosya seçebilirsiniz.
5. Yüklenen belgeler otomatik olarak vektör veritabanına eklenir ve **seçili** hale gelir. Birden fazla belgeyi seçerek aynı anda sorgulayabilirsiniz.

### Soru Sorma (RAG)

- Sohbet ekranında sorunuzu yazın ve Enter’a basın.
- Sistem, önce vektör araması yapar, en alakalı parçaları seçer ve **qwen2.5:7b-instruct** ile cevap üretir.
- Cevaplarda `[[c:N]]` etiketleri ile kaynak gösterilir; tıklayarak alıntılanan sayfayı/metni görebilirsiniz.

### MSSQL Veritabanı Bağlama

MSSQL’i bir notebook’a bağlamak için:

1. Ana sayfadaki **“Data Sources”** bölümünde notebook’u seçin.
2. **MSSQL Configuration** panelinde aşağıdaki alanları doldurun:
   1. **Server** – Sunucu adı veya IP
   2. **Port** – Genellikle 1433
   3. **Database Name** – Veritabanı adı
   4. **Username** – Kullanıcı adı
   5. **Password** – Şifre (güncellemede boş bırakılırsa eski şifre korunur)
   6. **Table Name** – Sorgulanacak tablo adı
   7. **Timestamp Column** – Zaman damgası sütunu (en yeni kayıtların sıralanacağı sütun)
   8. **Text Columns** – Metin içeren sütunlar (virgülle ayırın, ör. `message, level, source`)
3. **“Save & Test Connection”** butonuna basın. Backend bağlantıyı test eder; başarılıysa kaydeder.
4. Notebook’a gidin ve sohbet ekranında **“SQL Kaynağı”** adlı kaynağı seçin.
5. Sorularınızı doğal dilde sorun; sistem hem belgelerden hem de MSSQL’den gelen verilerle cevap üretir.

---

## Desteklenen Dosya Formatları

Aşağıdaki formatlar yüklenebilir ve RAG’de kullanılabilir:

```
.pdf   .md    .txt   .docx  .pptx  .doc   .ppt
.jpg   .jpeg  .png
```

- **PDF**: Metin katmanı varsa doğrudan okunur; taranmış/görüntü PDF’lerde Falcon-OCR devreye girer.
- **Resimler**: Tam sayfa OCR ile metne çevrilir.
- **Word/PowerPoint**: Metin ve gömülü resimler ayrı ayrı işlenir (resimler OCR’lanır).
- **Eski .doc/.ppt**: LibreOffice ile .docx/.pptx’e dönüştürülüp işlenir.

---

## Sorun Giderme

### Ollama bağlantı hatası

- `ollama serve` çalışıyor mu kontrol edin.
- `OLLAMA_BASE_URL` doğru mu? Varsayılan `http://localhost:11434`.
- Modeller indirildi mi? `ollama list` ile kontrol edin.

### Backend başlamıyor

- `requirements.txt`’teki bağımlılıkların kurulduğundan emin olun.
- `rag.env` dosyasının `backend/` dizininde olduğunu kontrol edin.
- SQLite dosyası (`app.db`) oluşturulabilsin diye dizin yazma izni verin.

### MSSQL bağlantı hatası

- `MSSQL_ENC_KEY` tanımlı ve geçerli bir Fernet anahtarı mı?
- ODBC Driver 18 kurulu mu?
- Sunucu, port, veritabanı adı ve tablo adı doğru mu?
- Tablo/kolon adlarında özel karakter veya boşluk olmamalı (sadece harf, rakam ve `_`).

### LibreOffice hatası

Bazı formatların PDF’e dönüştürülmesi için `soffice` komutu gerekir. Kurulu değilse:

```bash
sudo apt-get install -y libreoffice
```

### OCR yavaş veya GPU hatası

Falcon-OCR modeli büyüktür; CPU’da yavaş çalışabilir. GPU yoksa sabırlı olun veya daha küçük bir OCR modeli kullanın.

---

## Güvenlik Notları

- MSSQL şifresi **Fernet** ile şifrelenerek veritabanında saklanır, API asla şifreyi döndürmez.
- SQL sorgularında tablo/kolon adları sıkı bir beyaz liste ile doğrulanır (injection önlenir).
- Sistem tamamen yerel çalışır; belgeleriniz ve sorgularınız dışarı sızmaz.
- Yine de hassas verilerle kullanırken ağ erişimini sınırlandırmanız önerilir.

---