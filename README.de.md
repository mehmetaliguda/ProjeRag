# RAG-System (Unterstützt mehrere Datenquellen)

Dieses Projekt ist ein **Retrieval-Augmented Generation (RAG)**-System, das vollständig lokal läuft. Sie können Fragen in natürlicher Sprache stellen und erhalten Antworten basierend auf verschiedenen Quellen wie PDF, Word, PowerPoint, Bildern, Textdateien und MSSQL-Datenbanken.

Das System läuft **vollständig lokal**; LLM-, Embedding- und OCR-Modelle werden über **Ollama** und **Hugging Face** heruntergeladen, und keine Daten werden nach außen gesendet.

---

## Inhaltsverzeichnis

1. [Architekturübersicht](#architekturübersicht)
2. [Verwendete Technologien und Modelle](#verwendete-technologien-und-modelle)
3. [Installation](#installation)
   - [Voraussetzungen](#voraussetzungen)
   - [Backend-Einrichtung](#backend-einrichtung)
   - [Frontend-Einrichtung](#frontend-einrichtung)
   - [Herunterladen der Ollama-Modelle](#herunterladen-der-ollama-modelle)
   - [Umgebungsvariablen (.env)](#umgebungsvariablen-env)
4. [Ausführen der Anwendung](#ausführen-der-anwendung)
5. [Verwendung](#verwendung)
   - [Erstellen von Notebooks und Hochladen von Dateien](#erstellen-von-notebooks-und-hochladen-von-dateien)
   - [Fragen stellen (RAG)](#fragen-stellen-rag)
   - [Verbindung zu MSSQL-Datenbank](#verbindung-zu-mssql-datenbank)
6. [Unterstützte Dateiformate](#unterstützte-dateiformate)
7. [Fehlerbehebung](#fehlerbehebung)
8. [Sicherheitshinweise](#sicherheitshinweise)

---

## Architekturübersicht

Das Projekt besteht aus zwei Hauptkomponenten:

- **Frontend**: Eine Web-Oberfläche basierend auf Next.js (React). Benutzer erstellen Notebooks, laden Dateien hoch, chatten und konfigurieren MSSQL-Verbindungen.
- **Backend**: Eine REST-API basierend auf Flask (Python). Verarbeitet die RAG-Engine, Dokumentenindizierung, Vektorsuche, MSSQL-Konnektivität und LLM-Antwortgenerierung.

Im Backend:
- Die **SQLite**-Datenbank (`app.db`) speichert Notebook-, Konversations-, Raum- und MSSQL-Konfigurationsdaten.
- Die **Chroma**-Vektordatenbank speichert Embeddings in einem separaten Ordner für jeden Dokumentenraum.
- **LangChain / LangGraph** verwaltet die RAG-Pipeline.
- Der **Hybride Retriever** (BM25 + semantische Suche) und der **CrossEncoderReranker** wählen die relevantesten Textabschnitte aus.

---

## Verwendete Technologien und Modelle

| Zweck | Technologie / Modell |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| **Web-Framework (Backend)** | Flask 3.0 |
| **Web-Framework (Frontend)** | Next.js 16 + React 19 + Tailwind CSS 4 |
| **Vektordatenbank** | Chroma (langchain-chroma) |
| **Embedding-Modell** | `bge-m3` (über OllamaEmbeddings) |
| **LLM (Antwortgenerierung)** | `qwen2.5:7b-instruct` (über Ollama, auch verwendet für Query-Optimierung und Re-Ranking) |
| **OCR-Modell** | `tiiuae/Falcon-OCR` (Hugging Face transformers, für Bilder und gescannte PDFs) |
| **PDF-Verarbeitung** | PyMuPDF (fitz) + LangChain PyMuPDFLoader; Fallback auf Falcon-OCR für gescannte Seiten |
| **Datenbank** | SQLite (Flask-SQLAlchemy) |
| **MSSQL-Konnektivität** | `pyodbc` + `ODBC Driver 18 for SQL Server` |
| **Verschlüsselung** | Fernet (cryptography) zur Verschlüsselung von MSSQL-Passwörtern |
| **Dateikonvertierungen** | LibreOffice (headless) zur Konvertierung von Legacy .doc/.ppt und .docx/.pptx zu PDF |

---

## Installation

### Voraussetzungen

- **Python 3.10+** (Backend)
- **Node.js 20+** und **pnpm** oder **npm** (Frontend)
- **Ollama** installiert und ausgeführt ([ollama.com](https://ollama.com))
- **LibreOffice** – zur Konvertierung bestimmter Dateiformate in PDF:
  - Ubuntu/Debian: `sudo apt-get install -y libreoffice`
  - Windows/macOS: [LibreOffice herunterladen](https://www.libreoffice.org/download/)
- **ODBC Driver 18 for SQL Server** (falls MSSQL verwendet wird):
  - Offizielle Installationsanweisungen von Microsoft: [Linux](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server), [Windows](https://learn.microsoft.com/sql/connect/odbc/windows/system-requirements-installation-and-driver-files)
- **Git** (optional)

### Backend-Einrichtung

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend-Einrichtung

Vom Projektstammverzeichnis aus:

```bash
pnpm install     # oder npm install
```

### Herunterladen der Ollama-Modelle

Laden Sie vor dem Start von Ollama die erforderlichen Modelle herunter:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b-instruct
```

> **Hinweis:** `bge-m3` wird für Embeddings verwendet, `qwen2.5:7b-instruct` für die Antwortgenerierung und das Re-Ranking. Die Modellgrößen können groß sein (bge-m3 ~1.2GB, qwen2.5:7b ~4.7GB).

Das OCR-Modell ist **nicht auf Ollama verfügbar**; es wird bei der ersten Verwendung automatisch von Hugging Face heruntergeladen. Für manuelles Herunterladen:

```bash
python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')"
```

### Umgebungsvariablen (.env)

Das Backend liest die Konfiguration aus `backend/rag.env`. Erstellen Sie eine `rag.env`-Datei mit folgendem Inhalt:

```ini
# Ollama-Einstellungen
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Embedding-Modell
EMBED_MODEL=bge-m3

# Vektordatenbank-Ordner
RAG_ROOMS_ROOT=./rag_rooms

# MSSQL-Verschlüsselungsschlüssel (Fernet)
# Generieren Sie einen neuen Schlüssel mit:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MSSQL_ENC_KEY=ihr_generierter_schluessel_hier

# MSSQL-ODBC-Treiber (Standard: ODBC Driver 18 for SQL Server)
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# OCR-Modell (optional)
FALCON_OCR_MODEL_ID=tiiuae/Falcon-OCR
FALCON_OCR_LOCAL_PATH=./models/falcon-ocr

# Optionale zusätzliche Einstellungen
APP_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///app.db
```

**Wichtig:** Die MSSQL-Konnektivität funktioniert nicht ohne `MSSQL_ENC_KEY`. Wenn das Feld leer gelassen wird, gibt die Anwendung einen Fehler aus.

---

## Ausführen der Anwendung

### 1. Ollama starten

```bash
ollama serve
```

Überprüfen Sie, ob es läuft:

```bash
curl http://localhost:11434
```

oder besuchen Sie `http://localhost:11434` in Ihrem Browser.

### 2. Backend starten

In einem neuen Terminal:

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
flask --app app.py run
```

Das Backend lauscht standardmäßig auf `http://127.0.0.1:5000`.

### 3. Frontend starten

In einem weiteren Terminal (vom Projektstammverzeichnis aus):

```bash
npm run dev
```

oder

```bash
pnpm run dev
```

Das Frontend ist unter `http://localhost:3000` verfügbar.

---

## Verwendung

### Erstellen von Notebooks und Hochladen von Dateien

1. Öffnen Sie `http://localhost:3000` in Ihrem Browser.
2. Klicken Sie auf die Schaltfläche **"New Notebook"** oben rechts und geben Sie einen Namen ein.
3. Klicken Sie auf das Notebook, um die Chat-Seite zu öffnen.
4. Im linken Bereich unter **"Sources"** können Sie Dateien per Drag & Drop hinzufügen oder auf den Bereich **"Drop files here"** klicken, um Dateien auszuwählen.
5. Hochgeladene Dokumente werden automatisch zur Vektordatenbank hinzugefügt und standardmäßig **ausgewählt**. Sie können mehrere Dokumente auswählen, um sie gleichzeitig abzufragen.

### Fragen stellen (RAG)

- Geben Sie Ihre Frage in die Chat-Oberfläche ein und drücken Sie Enter.
- Das System führt eine Vektorsuche durch, wählt die relevantesten Textabschnitte aus und generiert eine Antwort mit **qwen2.5:7b-instruct**.
- Antworten enthalten `[[c:N]]`-Tags, die auf Quellen verweisen; klicken Sie darauf, um die zitierte Seite/den zitierten Text anzuzeigen.

### Verbindung zu MSSQL-Datenbank

So verbinden Sie ein Notebook mit MSSQL:

1. Wählen Sie im Abschnitt **"Data Sources"** auf der Hauptseite Ihr Notebook aus.
2. Füllen Sie im Bereich **MSSQL Configuration** Folgendes aus:
   1. **Server** – Servername oder IP-Adresse
   2. **Port** – Normalerweise 1433
   3. **Database Name** – Name der Datenbank
   4. **Username** – Datenbank-Benutzername
   5. **Password** – Datenbank-Passwort (bei Aktualisierung leer lassen, um das vorhandene Passwort zu behalten)
   6. **Table Name** – Die abzufragende Tabelle
   7. **Timestamp Column** – Zeitspaltenspalte zum Sortieren der neuesten Datensätze
   8. **Text Columns** – Spalten mit Textdaten (kommagetrennt, z.B. `message, level, source`)
3. Klicken Sie auf **"Save & Test Connection"**. Das Backend testet die Verbindung und speichert sie bei Erfolg.
4. Gehen Sie zum Notebook und wählen Sie **"SQL Source"** aus der Quellenliste.
5. Stellen Sie Fragen in natürlicher Sprache; das System generiert Antworten unter Verwendung von sowohl Dokumenten als auch MSSQL-Daten.

---

## Unterstützte Dateiformate

Die folgenden Formate können hochgeladen und in RAG verwendet werden:

```
.pdf   .md    .txt   .docx  .pptx  .doc   .ppt
.jpg   .jpeg  .png
```

- **PDF**: Wird direkt extrahiert, wenn eine Textebene vorhanden ist; bei gescannten/Bild-PDFs erfolgt ein Fallback auf Falcon-OCR.
- **Bilder**: Vollseiten-OCR konvertiert Bilder in Text.
- **Word/PowerPoint**: Text und eingebettete Bilder werden separat verarbeitet (Bilder werden OCR-erfasst).
- **Legacy .doc/.ppt**: Werden vor der Verarbeitung mit LibreOffice in .docx/.pptx konvertiert.

---

## Fehlerbehebung

### Ollama-Verbindungsfehler

- Überprüfen Sie, ob `ollama serve` ausgeführt wird.
- Stellen Sie sicher, dass `OLLAMA_BASE_URL` korrekt ist (Standard: `http://localhost:11434`).
- Vergewissern Sie sich, dass die Modelle heruntergeladen wurden (`ollama list` zur Überprüfung).

### Backend startet nicht

- Stellen Sie sicher, dass alle Abhängigkeiten aus `requirements.txt` installiert sind.
- Prüfen Sie, ob `rag.env` im Verzeichnis `backend/` vorhanden ist.
- Überprüfen Sie die Schreibberechtigungen für die SQLite-Datenbankdatei (`app.db`).

### MSSQL-Verbindungsfehler

- Ist `MSSQL_ENC_KEY` definiert und ein gültiger Fernet-Schlüssel?
- Ist ODBC Driver 18 installiert?
- Sind Server, Port, Datenbankname und Tabellenname korrekt?
- Tabellen-/Spaltennamen sollten keine Sonderzeichen oder Leerzeichen enthalten (nur Buchstaben, Zahlen und `_`).

### LibreOffice-Fehler

Die Dateikonvertierung erfordert den Befehl `soffice`. Falls nicht installiert:

```bash
sudo apt-get install -y libreoffice
```

### OCR langsam oder GPU-Fehler

Das Falcon-OCR-Modell ist groß und kann auf CPU langsam sein. Wenn keine GPU verfügbar ist, haben Sie Geduld oder ziehen Sie ein leichteres OCR-Modell in Betracht.

---

## Sicherheitshinweise

- MSSQL-Passwörter werden mit **Fernet** verschlüsselt in der Datenbank gespeichert; die API gibt niemals das Klartext-Passwort zurück.
- SQL-Abfragen werden gegen eine strenge Whitelist für Tabellen-/Spaltennamen validiert (verhindert Injection).
- Das System läuft vollständig lokal; Ihre Dokumente und Abfragen verlassen niemals Ihren Rechner.
- Bei sensiblen Daten wird empfohlen, den Netzwerkzugriff auf die Anwendung einzuschränken.

---