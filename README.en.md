İşte İngilizce README dosyası. Dosya adı için önerim: **`README.en.md`** (yaygın kullanılan standart) veya **`README.md`** (İngilizce varsayılan olacaksa). Türkçe ve İngilizce birlikte tutmak isterseniz `README.tr.md` ve `README.en.md` olarak ayırabilirsiniz.

```markdown
# RAG System (Multi-Source Supported)

This project is a **Retrieval-Augmented Generation (RAG)** system that runs entirely locally. You can ask natural language questions and receive answers based on various sources including PDF, Word, PowerPoint, images, text files, and MSSQL databases.

The system runs **completely locally**; LLM, embedding, and OCR models are downloaded via **Ollama** and **Hugging Face**, and no data is ever sent externally.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technologies and Models](#technologies-and-models)
3. [Installation](#installation)
   - [Prerequisites](#prerequisites)
   - [Backend Setup](#backend-setup)
   - [Frontend Setup](#frontend-setup)
   - [Downloading Ollama Models](#downloading-ollama-models)
   - [Environment Variables (.env)](#environment-variables-env)
4. [Running the Application](#running-the-application)
5. [Usage](#usage)
   - [Creating Notebooks and Uploading Files](#creating-notebooks-and-uploading-files)
   - [Asking Questions (RAG)](#asking-questions-rag)
   - [Connecting to MSSQL Database](#connecting-to-mssql-database)
6. [Supported File Formats](#supported-file-formats)
7. [Troubleshooting](#troubleshooting)
8. [Security Notes](#security-notes)

---

## Architecture Overview

The project consists of two main components:

- **Frontend**: A Next.js (React) web interface. Users create notebooks, upload files, chat, and configure MSSQL connections.
- **Backend**: A Flask (Python) REST API. Handles the RAG engine, document indexing, vector search, MSSQL connectivity, and LLM response generation.

Inside the backend:
- **SQLite** database (`app.db`) stores notebook, conversation, room, and MSSQL configuration data.
- **Chroma** vector database stores embeddings in a separate folder for each document room.
- **LangChain / LangGraph** manages the RAG pipeline.
- **Hybrid Retriever** (BM25 + semantic search) and **CrossEncoderReranker** select the most relevant chunks.

---

## Technologies and Models

| Purpose                  | Technology / Model                                                                                        |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| **Web Framework (Backend)** | Flask 3.0                                                                                                |
| **Web Framework (Frontend)** | Next.js 16 + React 19 + Tailwind CSS 4                                                                   |
| **Vector Database**      | Chroma (langchain-chroma)                                                                                  |
| **Embedding Model**      | `bge-m3` (via OllamaEmbeddings)                                                                            |
| **LLM (Response Generation)** | `qwen2.5:7b-instruct` (via Ollama, also used for query optimization and reranking)                        |
| **OCR Model**            | `tiiuae/Falcon-OCR` (Hugging Face transformers, for images and scanned PDFs)                              |
| **PDF Processing**       | PyMuPDF (fitz) + LangChain PyMuPDFLoader; Falcon-OCR fallback for scanned pages                           |
| **Database**             | SQLite (Flask-SQLAlchemy)                                                                                 |
| **MSSQL Connectivity**   | `pyodbc` + `ODBC Driver 18 for SQL Server`                                                                |
| **Encryption**           | Fernet (cryptography) for encrypting MSSQL passwords                                                      |
| **File Conversions**     | LibreOffice (headless) to convert legacy .doc/.ppt and .docx/.pptx to PDF                                 |

---

## Installation

### Prerequisites

- **Python 3.10+** (backend)
- **Node.js 20+** and **pnpm** or **npm** (frontend)
- **Ollama** installed and running ([ollama.com](https://ollama.com))
- **LibreOffice** – for converting certain file formats to PDF:
  - Ubuntu/Debian: `sudo apt-get install -y libreoffice`
  - Windows/macOS: [Download LibreOffice](https://www.libreoffice.org/download/)
- **ODBC Driver 18 for SQL Server** (if using MSSQL):
  - Official installation instructions from Microsoft: [Linux](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server), [Windows](https://learn.microsoft.com/sql/connect/odbc/windows/system-requirements-installation-and-driver-files)
- **Git** (optional)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

From the project root:

```bash
pnpm install     # or npm install
```

### Downloading Ollama Models

Before starting Ollama, download the required models:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b-instruct
```

> **Note:** `bge-m3` is used for embeddings, `qwen2.5:7b-instruct` for response generation and reranking. Model sizes can be large (bge-m3 ~1.2GB, qwen2.5:7b ~4.7GB).

The OCR model is **not available on Ollama**; it will be downloaded automatically from Hugging Face on first use. To download it manually:

```bash
python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')"
```

### Environment Variables (.env)

The backend reads configuration from `backend/rag.env`. Create a `rag.env` file with the following content:

```ini
# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Embedding model
EMBED_MODEL=bge-m3

# Vector database folder
RAG_ROOMS_ROOT=./rag_rooms

# MSSQL encryption key (Fernet)
# Generate a new key with:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MSSQL_ENC_KEY=your_generated_key_here

# MSSQL ODBC driver (default: ODBC Driver 18 for SQL Server)
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# OCR model (optional)
FALCON_OCR_MODEL_ID=tiiuae/Falcon-OCR
FALCON_OCR_LOCAL_PATH=./models/falcon-ocr

# Optional additional settings
APP_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///app.db
```

**Important:** MSSQL connectivity will not work without `MSSQL_ENC_KEY`. If left blank, the application will throw an error.

---

## Running the Application

### 1. Start Ollama

```bash
ollama serve
```

Verify it's running:

```bash
curl http://localhost:11434
```

or visit `http://localhost:11434` in your browser.

### 2. Start the Backend

In a new terminal:

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
flask --app app.py run
```

The backend will listen on `http://127.0.0.1:5000` by default.

### 3. Start the Frontend

In another terminal (from the project root):

```bash
npm run dev
```

or

```bash
pnpm run dev
```

The frontend will be available at `http://localhost:3000`.

---

## Usage

### Creating Notebooks and Uploading Files

1. Open `http://localhost:3000` in your browser.
2. Click the **"New Notebook"** button in the top right and give it a name.
3. Click on the notebook to enter the chat page.
4. In the left panel under **"Sources"**, drag and drop files or click the **"Drop files here"** area to select files.
5. Uploaded documents are automatically added to the vector database and **selected** by default. You can select multiple documents to query them simultaneously.

### Asking Questions (RAG)

- Type your question in the chat interface and press Enter.
- The system performs vector retrieval, selects the most relevant chunks, and generates a response using **qwen2.5:7b-instruct**.
- Responses include `[[c:N]]` tags referencing sources; click them to view the cited page/text.

### Connecting to MSSQL Database

To connect a notebook to MSSQL:

1. In the **"Data Sources"** section on the main page, select your notebook.
2. In the **MSSQL Configuration** panel, fill in the following:
   1. **Server** – Server name or IP address
   2. **Port** – Usually 1433
   3. **Database Name** – The name of the database
   4. **Username** – Database username
   5. **Password** – Database password (leave blank when updating to keep existing password)
   6. **Table Name** – The table to query
   7. **Timestamp Column** – Timestamp column for sorting latest records
   8. **Text Columns** – Columns containing text data (comma-separated, e.g., `message, level, source`)
3. Click **"Save & Test Connection"**. The backend tests the connection and saves it on success.
4. Go to the notebook and select the **"SQL Source"** from the sources list.
5. Ask questions in natural language; the system generates responses using both documents and MSSQL data.

---

## Supported File Formats

The following formats can be uploaded and used in RAG:

```
.pdf   .md    .txt   .docx  .pptx  .doc   .ppt
.jpg   .jpeg  .png
```

- **PDF**: Extracted directly if text layer exists; scanned/image PDFs fall back to Falcon-OCR.
- **Images**: Full-page OCR converts images to text.
- **Word/PowerPoint**: Text and embedded images are processed separately (images are OCR'ed).
- **Legacy .doc/.ppt**: Converted to .docx/.pptx using LibreOffice before processing.

---

## Troubleshooting

### Ollama Connection Error

- Check that `ollama serve` is running.
- Verify `OLLAMA_BASE_URL` is correct (default: `http://localhost:11434`).
- Ensure models are downloaded (`ollama list` to check).

### Backend Fails to Start

- Confirm all dependencies from `requirements.txt` are installed.
- Ensure `rag.env` is present in the `backend/` directory.
- Verify write permissions for the SQLite database file (`app.db`).

### MSSQL Connection Error

- Is `MSSQL_ENC_KEY` defined and a valid Fernet key?
- Is ODBC Driver 18 installed?
- Are server, port, database name, and table name correct?
- Table/column names should not contain special characters or spaces (only letters, numbers, and `_`).

### LibreOffice Error

File conversion requires the `soffice` command. If not installed:

```bash
sudo apt-get install -y libreoffice
```

### OCR Slow or GPU Error

The Falcon-OCR model is large and may be slow on CPU. If no GPU is available, be patient or consider using a lighter OCR model.

---

## Security Notes

- MSSQL passwords are encrypted using **Fernet** and stored in the database; the API never returns the plaintext password.
- SQL queries are validated against a strict allowlist for table/column names (preventing injection).
- The system runs entirely locally; your documents and queries never leave your machine.
- For sensitive data, it is recommended to restrict network access to the application.

---
```

Dosya adı olarak **`README.en.md`** kullanmanı öneririm. Bu şekilde:
- Türkçe versiyon `README.md` veya `README.tr.md` olarak kalabilir
- İngilizce versiyon `README.en.md` olarak yanında durabilir
- GitHub otomatik olarak `README.md`'yi varsayılan gösterir, ama ikinci bir dil dosyası da mevcut olur

İstersen dosyayı kopyalayıp projene `README.en.md` olarak kaydedebilirsin.