# Sistema RAG (Con Múltiples Fuentes de Datos)

Este proyecto es un sistema de **Generación Aumentada por Recuperación (RAG)** que funciona completamente de forma local. Puedes hacer preguntas en lenguaje natural y recibir respuestas basadas en diversas fuentes, incluyendo PDF, Word, PowerPoint, imágenes, archivos de texto y bases de datos MSSQL.

El sistema funciona **completamente en local**; los modelos LLM, de embeddings y OCR se descargan a través de **Ollama** y **Hugging Face**, y ningún dato se envía al exterior.

---

## Tabla de Contenidos

1. [Descripción General de la Arquitectura](#descripción-general-de-la-arquitectura)
2. [Tecnologías y Modelos Utilizados](#tecnologías-y-modelos-utilizados)
3. [Instalación](#instalación)
   - [Requisitos Previos](#requisitos-previos)
   - [Configuración del Backend](#configuración-del-backend)
   - [Configuración del Frontend](#configuración-del-frontend)
   - [Descarga de Modelos de Ollama](#descarga-de-modelos-de-ollama)
   - [Variables de Entorno (.env)](#variables-de-entorno-env)
4. [Ejecución de la Aplicación](#ejecución-de-la-aplicación)
5. [Uso](#uso)
   - [Creación de Notebooks y Carga de Archivos](#creación-de-notebooks-y-carga-de-archivos)
   - [Haciendo Preguntas (RAG)](#haciendo-preguntas-rag)
   - [Conexión a Base de Datos MSSQL](#conexión-a-base-de-datos-mssql)
6. [Formatos de Archivo Soportados](#formatos-de-archivo-soportados)
7. [Solución de Problemas](#solución-de-problemas)
8. [Notas de Seguridad](#notas-de-seguridad)

---

## Descripción General de la Arquitectura

El proyecto consta de dos componentes principales:

- **Frontend**: Interfaz web basada en Next.js (React). Los usuarios crean notebooks, suben archivos, chatean y configuran conexiones MSSQL.
- **Backend**: API REST basada en Flask (Python). Maneja el motor RAG, indexación de documentos, búsqueda vectorial, conectividad MSSQL y generación de respuestas mediante LLM.

Dentro del backend:
- La base de datos **SQLite** (`app.db`) almacena notebooks, conversaciones, salas y configuraciones MSSQL.
- La base de datos vectorial **Chroma** almacena embeddings en una carpeta separada para cada sala de documentos.
- **LangChain / LangGraph** gestiona el pipeline RAG.
- El **Recuperador Híbrido** (BM25 + búsqueda semántica) y el **CrossEncoderReranker** seleccionan los fragmentos más relevantes.

---

## Tecnologías y Modelos Utilizados

| Propósito | Tecnología / Modelo |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| **Framework Web (Backend)** | Flask 3.0 |
| **Framework Web (Frontend)** | Next.js 16 + React 19 + Tailwind CSS 4 |
| **Base de Datos Vectorial** | Chroma (langchain-chroma) |
| **Modelo de Embeddings** | `bge-m3` (a través de OllamaEmbeddings) |
| **LLM (Generación de Respuestas)** | `qwen2.5:7b-instruct` (a través de Ollama, también usado para optimización de consultas y re-ranking) |
| **Modelo OCR** | `tiiuae/Falcon-OCR` (Hugging Face transformers, para imágenes y PDFs escaneados) |
| **Procesamiento de PDF** | PyMuPDF (fitz) + LangChain PyMuPDFLoader; fallback a Falcon-OCR para páginas escaneadas |
| **Base de Datos** | SQLite (Flask-SQLAlchemy) |
| **Conectividad MSSQL** | `pyodbc` + `ODBC Driver 18 for SQL Server` |
| **Encriptación** | Fernet (cryptography) para encriptar contraseñas de MSSQL |
| **Conversiones de Archivos** | LibreOffice (headless) para convertir .doc/.ppt y .docx/.pptx antiguos a PDF |

---

## Instalación

### Requisitos Previos

- **Python 3.10+** (backend)
- **Node.js 20+** y **pnpm** o **npm** (frontend)
- **Ollama** instalado y en ejecución ([ollama.com](https://ollama.com))
- **LibreOffice** – para convertir ciertos formatos de archivo a PDF:
  - Ubuntu/Debian: `sudo apt-get install -y libreoffice`
  - Windows/macOS: [Descargar LibreOffice](https://www.libreoffice.org/download/)
- **ODBC Driver 18 for SQL Server** (si usas MSSQL):
  - Instrucciones oficiales de Microsoft: [Linux](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server), [Windows](https://learn.microsoft.com/sql/connect/odbc/windows/system-requirements-installation-and-driver-files)
- **Git** (opcional)

### Configuración del Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuración del Frontend

Desde la raíz del proyecto:

```bash
pnpm install     # o npm install
```

### Descarga de Modelos de Ollama

Antes de iniciar Ollama, descarga los modelos necesarios:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b-instruct
```

> **Nota:** `bge-m3` se usa para embeddings, `qwen2.5:7b-instruct` para generación de respuestas y re-ranking. Los tamaños de los modelos pueden ser grandes (bge-m3 ~1.2GB, qwen2.5:7b ~4.7GB).

El modelo OCR **no está disponible en Ollama**; se descargará automáticamente desde Hugging Face en el primer uso. Para descargarlo manualmente:

```bash
python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')"
```

### Variables de Entorno (.env)

El backend lee la configuración de `backend/rag.env`. Crea un archivo `rag.env` con el siguiente contenido:

```ini
# Configuración de Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Modelo de embeddings
EMBED_MODEL=bge-m3

# Carpeta de la base de datos vectorial
RAG_ROOMS_ROOT=./rag_rooms

# Clave de encriptación MSSQL (Fernet)
# Genera una nueva clave con:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MSSQL_ENC_KEY=tu_clave_generada_aqui

# Controlador ODBC de MSSQL (predeterminado: ODBC Driver 18 for SQL Server)
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# Modelo OCR (opcional)
FALCON_OCR_MODEL_ID=tiiuae/Falcon-OCR
FALCON_OCR_LOCAL_PATH=./models/falcon-ocr

# Configuraciones adicionales opcionales
APP_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///app.db
```

**Importante:** La conectividad MSSQL no funcionará sin `MSSQL_ENC_KEY`. Si se deja en blanco, la aplicación lanzará un error.

---

## Ejecución de la Aplicación

### 1. Iniciar Ollama

```bash
ollama serve
```

Verifica que está funcionando:

```bash
curl http://localhost:11434
```

o visita `http://localhost:11434` en tu navegador.

### 2. Iniciar el Backend

En una nueva terminal:

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
flask --app app.py run
```

El backend escuchará en `http://127.0.0.1:5000` por defecto.

### 3. Iniciar el Frontend

En otra terminal (desde la raíz del proyecto):

```bash
npm run dev
```

o

```bash
pnpm run dev
```

El frontend estará disponible en `http://localhost:3000`.

---

## Uso

### Creación de Notebooks y Carga de Archivos

1. Abre `http://localhost:3000` en tu navegador.
2. Haz clic en el botón **"New Notebook"** en la parte superior derecha y asígnale un nombre.
3. Haz clic en el notebook para entrar en la página de chat.
4. En el panel izquierdo, en la sección **"Sources"**, arrastra y suelta archivos o haz clic en el área **"Drop files here"** para seleccionar archivos.
5. Los documentos subidos se añaden automáticamente a la base de datos vectorial y se **seleccionan** por defecto. Puedes seleccionar múltiples documentos para consultarlos simultáneamente.

### Haciendo Preguntas (RAG)

- Escribe tu pregunta en la interfaz de chat y presiona Enter.
- El sistema realiza una búsqueda vectorial, selecciona los fragmentos más relevantes y genera una respuesta usando **qwen2.5:7b-instruct**.
- Las respuestas incluyen etiquetas `[[c:N]]` que hacen referencia a las fuentes; haz clic en ellas para ver la página/texto citado.

### Conexión a Base de Datos MSSQL

Para conectar un notebook a MSSQL:

1. En la sección **"Data Sources"** de la página principal, selecciona tu notebook.
2. En el panel **MSSQL Configuration**, completa lo siguiente:
   1. **Server** – Nombre del servidor o dirección IP
   2. **Port** – Generalmente 1433
   3. **Database Name** – Nombre de la base de datos
   4. **Username** – Nombre de usuario de la base de datos
   5. **Password** – Contraseña de la base de datos (déjala en blanco al actualizar para mantener la contraseña existente)
   6. **Table Name** – La tabla a consultar
   7. **Timestamp Column** – Columna de marca de tiempo para ordenar los registros más recientes
   8. **Text Columns** – Columnas que contienen datos de texto (separadas por comas, ej: `message, level, source`)
3. Haz clic en **"Save & Test Connection"**. El backend prueba la conexión y la guarda si tiene éxito.
4. Ve al notebook y selecciona **"SQL Source"** de la lista de fuentes.
5. Haz preguntas en lenguaje natural; el sistema genera respuestas usando tanto documentos como datos de MSSQL.

---

## Formatos de Archivo Soportados

Los siguientes formatos pueden ser subidos y utilizados en RAG:

```
.pdf   .md    .txt   .docx  .pptx  .doc   .ppt
.jpg   .jpeg  .png
```

- **PDF**: Se extrae directamente si tiene capa de texto; los PDFs escaneados/imagen usan Falcon-OCR como fallback.
- **Imágenes**: OCR de página completa convierte las imágenes a texto.
- **Word/PowerPoint**: El texto y las imágenes incrustadas se procesan por separado (las imágenes son OCRizadas).
- **.doc/.ppt antiguos**: Se convierten a .docx/.pptx usando LibreOffice antes del procesamiento.

---

## Solución de Problemas

### Error de Conexión con Ollama

- Verifica que `ollama serve` esté ejecutándose.
- Confirma que `OLLAMA_BASE_URL` sea correcto (predeterminado: `http://localhost:11434`).
- Asegúrate de que los modelos estén descargados (`ollama list` para verificar).

### El Backend No se Inicia

- Confirma que todas las dependencias de `requirements.txt` estén instaladas.
- Asegúrate de que `rag.env` esté presente en el directorio `backend/`.
- Verifica los permisos de escritura para el archivo de la base de datos SQLite (`app.db`).

### Error de Conexión MSSQL

- ¿Está `MSSQL_ENC_KEY` definida y es una clave Fernet válida?
- ¿Está instalado ODBC Driver 18?
- ¿Son correctos el servidor, puerto, nombre de la base de datos y nombre de la tabla?
- Los nombres de tablas/columnas no deben contener caracteres especiales ni espacios (solo letras, números y `_`).

### Error de LibreOffice

La conversión de archivos requiere el comando `soffice`. Si no está instalado:

```bash
sudo apt-get install -y libreoffice
```

### OCR Lento o Error de GPU

El modelo Falcon-OCR es grande y puede ser lento en CPU. Si no tienes GPU, ten paciencia o considera usar un modelo OCR más ligero.

---

## Notas de Seguridad

- Las contraseñas de MSSQL se encriptan usando **Fernet** y se almacenan en la base de datos; la API nunca devuelve la contraseña en texto plano.
- Las consultas SQL se validan contra una lista de permisos estricta para nombres de tablas/columnas (previniendo inyección).
- El sistema funciona completamente en local; tus documentos y consultas nunca salen de tu máquina.
- Para datos sensibles, se recomienda restringir el acceso de red a la aplicación.

---