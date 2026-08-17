# RAGシステム（複数データソース対応）

このプロジェクトは、完全にローカルで動作する**検索拡張生成（RAG）**システムです。PDF、Word、PowerPoint、画像、テキストファイル、MSSQLデータベースなど、さまざまなソースを使用して自然言語で質問し、文書に基づいた回答を得ることができます。

システムは**完全にローカル**で動作します。LLM、埋め込み、OCRモデルは**Ollama**および**Hugging Face**からダウンロードされ、データが外部に送信されることは一切ありません。

---

## 目次

1. [アーキテクチャの概要](#アーキテクチャの概要)
2. [使用技術とモデル](#使用技術とモデル)
3. [インストール](#インストール)
   - [前提条件](#前提条件)
   - [バックエンドのセットアップ](#バックエンドのセットアップ)
   - [フロントエンドのセットアップ](#フロントエンドのセットアップ)
   - [Ollamaモデルのダウンロード](#ollamaモデルのダウンロード)
   - [環境変数（.env）](#環境変数env)
4. [アプリケーションの実行](#アプリケーションの実行)
5. [使用方法](#使用方法)
   - [ノートブックの作成とファイルのアップロード](#ノートブックの作成とファイルのアップロード)
   - [質問する（RAG）](#質問するrag)
   - [MSSQLデータベースへの接続](#mssqlデータベースへの接続)
6. [サポートされているファイル形式](#サポートされているファイル形式)
7. [トラブルシューティング](#トラブルシューティング)
8. [セキュリティ上の注意](#セキュリティ上の注意)

---

## アーキテクチャの概要

プロジェクトは2つの主要コンポーネントで構成されています：

- **フロントエンド**：Next.js（React）ベースのWebインターフェース。ユーザーはノートブックを作成し、ファイルをアップロードし、チャットし、MSSQL接続を設定できます。
- **バックエンド**：Flask（Python）ベースのREST API。RAGエンジン、ドキュメントインデックス作成、ベクトル検索、MSSQL接続、LLMによる応答生成を処理します。

バックエンド内部：
- **SQLite**データベース（`app.db`）は、ノートブック、会話、ルーム、MSSQL設定データを保存します。
- **Chroma**ベクトルデータベースは、各ドキュメントルームごとに別のフォルダに埋め込みを保存します。
- **LangChain / LangGraph**がRAGパイプラインを管理します。
- **ハイブリッド検索**（BM25 + セマンティック検索）および**CrossEncoderReranker**が最も関連性の高いチャンクを選択します。

---

## 使用技術とモデル

| 目的 | 技術 / モデル |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| **Webフレームワーク（バックエンド）** | Flask 3.0 |
| **Webフレームワーク（フロントエンド）** | Next.js 16 + React 19 + Tailwind CSS 4 |
| **ベクトルデータベース** | Chroma（langchain-chroma） |
| **埋め込みモデル** | `bge-m3`（OllamaEmbeddings経由） |
| **LLM（応答生成）** | `qwen2.5:7b-instruct`（Ollama経由、クエリ最適化と再ランキングにも使用） |
| **OCRモデル** | `tiiuae/Falcon-OCR`（Hugging Face transformers、画像およびスキャンPDF用） |
| **PDF処理** | PyMuPDF（fitz）+ LangChain PyMuPDFLoader；スキャンされたページはFalcon-OCRにフォールバック |
| **データベース** | SQLite（Flask-SQLAlchemy） |
| **MSSQL接続** | `pyodbc` + `ODBC Driver 18 for SQL Server` |
| **暗号化** | Fernet（cryptography）によるMSSQLパスワードの暗号化 |
| **ファイル変換** | LibreOffice（ヘッドレス）を使用して、レガシー.doc/.pptおよび.docx/.pptxをPDFに変換 |

---

## インストール

### 前提条件

- **Python 3.10+**（バックエンド）
- **Node.js 20+** および **pnpm** または **npm**（フロントエンド）
- **Ollama**がインストールされ、実行中であること（[ollama.com](https://ollama.com)）
- **LibreOffice** – 特定のファイル形式をPDFに変換するために必要：
  - Ubuntu/Debian: `sudo apt-get install -y libreoffice`
  - Windows/macOS: [LibreOfficeをダウンロード](https://www.libreoffice.org/download/)
- **ODBC Driver 18 for SQL Server**（MSSQLを使用する場合）：
  - Microsoft公式インストール手順：[Linux](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)、[Windows](https://learn.microsoft.com/sql/connect/odbc/windows/system-requirements-installation-and-driver-files)
- **Git**（オプション）

### バックエンドのセットアップ

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### フロントエンドのセットアップ

プロジェクトルートから：

```bash
pnpm install     # または npm install
```

### Ollamaモデルのダウンロード

Ollamaを起動する前に、必要なモデルをダウンロードします：

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b-instruct
```

> **注記：** `bge-m3`は埋め込みに、`qwen2.5:7b-instruct`は応答生成と再ランキングに使用されます。モデルサイズは大きくなる可能性があります（bge-m3 ~1.2GB、qwen2.5:7b ~4.7GB）。

OCRモデルは**Ollamaでは利用できません**。初回使用時にHugging Faceから自動的にダウンロードされます。手動でダウンロードするには：

```bash
python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')"
```

### 環境変数（.env）

バックエンドは`backend/rag.env`から設定を読み取ります。以下の内容で`rag.env`ファイルを作成してください：

```ini
# Ollama設定
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# 埋め込みモデル
EMBED_MODEL=bge-m3

# ベクトルデータベースフォルダ
RAG_ROOMS_ROOT=./rag_rooms

# MSSQL暗号化キー（Fernet）
# 新しいキーを生成するには：
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MSSQL_ENC_KEY=ここに生成したキー

# MSSQL ODBCドライバ（デフォルト：ODBC Driver 18 for SQL Server）
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# OCRモデル（オプション）
FALCON_OCR_MODEL_ID=tiiuae/Falcon-OCR
FALCON_OCR_LOCAL_PATH=./models/falcon-ocr

# オプションの追加設定
APP_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///app.db
```

**重要：** `MSSQL_ENC_KEY`がないとMSSQL接続は機能しません。空白のままにすると、アプリケーションはエラーをスローします。

---

## アプリケーションの実行

### 1. Ollamaを起動する

```bash
ollama serve
```

実行を確認する：

```bash
curl http://localhost:11434
```

またはブラウザで`http://localhost:11434`にアクセスします。

### 2. バックエンドを起動する

新しいターミナルで：

```bash
cd backend
source venv/bin/activate   # Windows: venv\Scripts\activate
flask --app app.py run
```

バックエンドはデフォルトで`http://127.0.0.1:5000`で待受します。

### 3. フロントエンドを起動する

別のターミナルで（プロジェクトルートから）：

```bash
npm run dev
```

または

```bash
pnpm run dev
```

フロントエンドは`http://localhost:3000`で利用可能になります。

---

## 使用方法

### ノートブックの作成とファイルのアップロード

1. ブラウザで`http://localhost:3000`を開きます。
2. 右上の**「New Notebook」**ボタンをクリックし、名前を付けます。
3. ノートブックをクリックしてチャットページに入ります。
4. 左側のパネルの**「Sources」**セクションで、ファイルをドラッグ＆ドロップするか、**「Drop files here」**エリアをクリックしてファイルを選択します。
5. アップロードされたドキュメントは自動的にベクトルデータベースに追加され、**デフォルトで選択**されます。複数のドキュメントを選択して同時にクエリできます。

### 質問する（RAG）

- チャットインターフェースに質問を入力し、Enterキーを押します。
- システムはベクトル検索を実行し、最も関連性の高いチャンクを選択し、**qwen2.5:7b-instruct**を使用して応答を生成します。
- 応答にはソースを参照する`[[c:N]]`タグが含まれます。クリックすると引用されたページ/テキストを表示できます。

### MSSQLデータベースへの接続

ノートブックをMSSQLに接続するには：

1. メインページの**「Data Sources」**セクションで、ノートブックを選択します。
2. **MSSQL Configuration**パネルで以下を入力します：
   1. **Server** – サーバー名またはIPアドレス
   2. **Port** – 通常は1433
   3. **Database Name** – データベース名
   4. **Username** – データベースユーザー名
   5. **Password** – データベースパスワード（更新時に空白のままにすると既存のパスワードが保持されます）
   6. **Table Name** – クエリするテーブル
   7. **Timestamp Column** – 最新レコードをソートするためのタイムスタンプ列
   8. **Text Columns** – テキストデータを含む列（カンマ区切り、例：`message, level, source`）
3. **「Save & Test Connection」**ボタンをクリックします。バックエンドが接続をテストし、成功したら保存します。
4. ノートブックに移動し、ソースリストから**「SQL Source」**を選択します。
5. 自然言語で質問します。システムはドキュメントとMSSQLデータの両方を使用して応答を生成します。

---

## サポートされているファイル形式

以下の形式をアップロードしてRAGで使用できます：

```
.pdf   .md    .txt   .docx  .pptx  .doc   .ppt
.jpg   .jpeg  .png
```

- **PDF**：テキストレイヤーが存在する場合は直接抽出されます。スキャン/画像PDFの場合はFalcon-OCRにフォールバックします。
- **画像**：フルページOCRでテキストに変換されます。
- **Word/PowerPoint**：テキストと埋め込み画像は別々に処理されます（画像はOCR処理されます）。
- **レガシー.doc/.ppt**：処理前にLibreOfficeを使用して.docx/.pptxに変換されます。

---

## トラブルシューティング

### Ollama接続エラー

- `ollama serve`が実行中であることを確認してください。
- `OLLAMA_BASE_URL`が正しいことを確認してください（デフォルト：`http://localhost:11434`）。
- モデルがダウンロードされていることを確認してください（`ollama list`で確認）。

### バックエンドが起動しない

- `requirements.txt`の依存関係がすべてインストールされていることを確認してください。
- `rag.env`が`backend/`ディレクトリに存在することを確認してください。
- SQLiteデータベースファイル（`app.db`）の書き込み権限を確認してください。

### MSSQL接続エラー

- `MSSQL_ENC_KEY`が定義されており、有効なFernetキーですか？
- ODBC Driver 18がインストールされていますか？
- サーバー、ポート、データベース名、テーブル名は正しいですか？
- テーブル/列名に特殊文字やスペースを含めないでください（英数字と`_`のみ）。

### LibreOfficeエラー

ファイル変換には`soffice`コマンドが必要です。インストールされていない場合：

```bash
sudo apt-get install -y libreoffice
```

### OCRが遅い、またはGPUエラー

Falcon-OCRモデルは大きく、CPUでは遅くなる可能性があります。GPUがない場合は忍耐が必要か、より軽量なOCRモデルの使用を検討してください。

---

## セキュリティ上の注意

- MSSQLパスワードは**Fernet**で暗号化されてデータベースに保存され、APIは平文のパスワードを返すことはありません。
- SQLクエリはテーブル/列名に対して厳格な許可リストで検証されます（インジェクションを防止）。
- システムは完全にローカルで動作します。ドキュメントとクエリがマシンの外部に出ることはありません。
- 機密データを扱う場合は、アプリケーションへのネットワークアクセスを制限することを推奨します。

---