# Système RAG (Support Multi-Sources)

Ce projet est un système de **Génération Augmentée par Récupération (RAG)** qui fonctionne entièrement en local. Vous pouvez poser des questions en langage naturel et recevoir des réponses basées sur diverses sources telles que PDF, Word, PowerPoint, images, fichiers texte et bases de données MSSQL.

Le système fonctionne **complètement en local** ; les modèles LLM, d'embedding et OCR sont téléchargés via **Ollama** et **Hugging Face**, et aucune donnée n'est jamais envoyée à l'extérieur.

---

## Table des Matières

1. [Aperçu de l'Architecture](#aperçu-de-larchitecture)
2. [Technologies et Modèles Utilisés](#technologies-et-modèles-utilisés)
3. [Installation](#installation)
   - [Prérequis](#prérequis)
   - [Configuration du Backend](#configuration-du-backend)
   - [Configuration du Frontend](#configuration-du-frontend)
   - [Téléchargement des Modèles Ollama](#téléchargement-des-modèles-ollama)
   - [Variables d'Environnement (.env)](#variables-denvironnement-env)
4. [Exécution de l'Application](#exécution-de-lapplication)
5. [Utilisation](#utilisation)
   - [Création de Notebooks et Téléchargement de Fichiers](#création-de-notebooks-et-téléchargement-de-fichiers)
   - [Poser des Questions (RAG)](#poser-des-questions-rag)
   - [Connexion à une Base de Données MSSQL](#connexion-à-une-base-de-données-mssql)
6. [Formats de Fichier Supportés](#formats-de-fichier-supportés)
7. [Dépannage](#dépannage)
8. [Notes de Sécurité](#notes-de-sécurité)

---

## Aperçu de l'Architecture

Le projet se compose de deux composants principaux :

- **Frontend** : Une interface web basée sur Next.js (React). Les utilisateurs créent des notebooks, téléchargent des fichiers, discutent et configurent des connexions MSSQL.
- **Backend** : Une API REST basée sur Flask (Python). Gère le moteur RAG, l'indexation des documents, la recherche vectorielle, la connectivité MSSQL et la génération de réponses par LLM.

À l'intérieur du backend :
- La base de données **SQLite** (`app.db`) stocke les notebooks, conversations, salles et configurations MSSQL.
- La base de données vectorielle **Chroma** stocke les embeddings dans un dossier séparé pour chaque salle de documents.
- **LangChain / LangGraph** gère le pipeline RAG.
- Le **Rechercheur Hybride** (BM25 + recherche sémantique) et le **CrossEncoderReranker** sélectionnent les fragments les plus pertinents.

---

## Technologies et Modèles Utilisés

| Objectif | Technologie / Modèle |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| **Framework Web (Backend)** | Flask 3.0 |
| **Framework Web (Frontend)** | Next.js 16 + React 19 + Tailwind CSS 4 |
| **Base de Données Vectorielle** | Chroma (langchain-chroma) |
| **Modèle d'Embedding** | `bge-m3` (via OllamaEmbeddings) |
| **LLM (Génération de Réponses)** | `qwen2.5:7b-instruct` (via Ollama, également utilisé pour l'optimisation des requêtes et le re-ranking) |
| **Modèle OCR** | `tiiuae/Falcon-OCR` (Hugging Face transformers, pour les images et les PDF scannés) |
| **Traitement PDF** | PyMuPDF (fitz) + LangChain PyMuPDFLoader ; recours à Falcon-OCR pour les pages scannées |
| **Base de Données** | SQLite (Flask-SQLAlchemy) |
| **Connectivité MSSQL** | `pyodbc` + `ODBC Driver 18 for SQL Server` |
| **Chiffrement** | Fernet (cryptography) pour chiffrer les mots de passe MSSQL |
| **Conversions de Fichiers** | LibreOffice (headless) pour convertir les anciens .doc/.ppt et .docx/.pptx en PDF |

---

## Installation

### Prérequis

- **Python 3.10+** (backend)
- **Node.js 20+** et **pnpm** ou **npm** (frontend)
- **Ollama** installé et en cours d'exécution ([ollama.com](https://ollama.com))
- **LibreOffice** – pour convertir certains formats de fichiers en PDF :
  - Ubuntu/Debian : `sudo apt-get install -y libreoffice`
  - Windows/macOS : [Télécharger LibreOffice](https://www.libreoffice.org/download/)
- **ODBC Driver 18 for SQL Server** (si vous utilisez MSSQL) :
  - Instructions d'installation officielles de Microsoft : [Linux](https://learn.microsoft.com/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server), [Windows](https://learn.microsoft.com/sql/connect/odbc/windows/system-requirements-installation-and-driver-files)
- **Git** (optionnel)

### Configuration du Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration du Frontend

Depuis la racine du projet :

```bash
pnpm install     # ou npm install
```

### Téléchargement des Modèles Ollama

Avant de démarrer Ollama, téléchargez les modèles requis :

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b-instruct
```

> **Remarque :** `bge-m3` est utilisé pour les embeddings, `qwen2.5:7b-instruct` pour la génération de réponses et le re-ranking. Les tailles des modèles peuvent être importantes (bge-m3 ~1.2Go, qwen2.5:7b ~4.7Go).

Le modèle OCR **n'est pas disponible sur Ollama** ; il sera téléchargé automatiquement depuis Hugging Face lors de la première utilisation. Pour le télécharger manuellement :

```bash
python -c "from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('tiiuae/Falcon-OCR', trust_remote_code=True); model.save_pretrained('./models/falcon-ocr')"
```

### Variables d'Environnement (.env)

Le backend lit la configuration depuis `backend/rag.env`. Créez un fichier `rag.env` avec le contenu suivant :

```ini
# Paramètres Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Modèle d'embedding
EMBED_MODEL=bge-m3

# Dossier de la base de données vectorielle
RAG_ROOMS_ROOT=./rag_rooms

# Clé de chiffrement MSSQL (Fernet)
# Générer une nouvelle clé avec :
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MSSQL_ENC_KEY=votre_clé_générée_ici

# Pilote ODBC MSSQL (par défaut : ODBC Driver 18 for SQL Server)
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# Modèle OCR (optionnel)
FALCON_OCR_MODEL_ID=tiiuae/Falcon-OCR
FALCON_OCR_LOCAL_PATH=./models/falcon-ocr

# Paramètres supplémentaires optionnels
APP_BASE_URL=http://127.0.0.1:5000
DATABASE_URL=sqlite:///app.db
```

**Important :** La connectivité MSSQL ne fonctionnera pas sans `MSSQL_ENC_KEY`. Si laissé vide, l'application générera une erreur.

---

## Exécution de l'Application

### 1. Démarrer Ollama

```bash
ollama serve
```

Vérifiez qu'il fonctionne :

```bash
curl http://localhost:11434
```

ou visitez `http://localhost:11434` dans votre navigateur.

### 2. Démarrer le Backend

Dans un nouveau terminal :

```bash
cd backend
source venv/bin/activate   # Windows : venv\Scripts\activate
flask --app app.py run
```

Le backend écoute par défaut sur `http://127.0.0.1:5000`.

### 3. Démarrer le Frontend

Dans un autre terminal (depuis la racine du projet) :

```bash
npm run dev
```

ou

```bash
pnpm run dev
```

Le frontend est disponible sur `http://localhost:3000`.

---

## Utilisation

### Création de Notebooks et Téléchargement de Fichiers

1. Ouvrez `http://localhost:3000` dans votre navigateur.
2. Cliquez sur le bouton **"New Notebook"** en haut à droite et donnez-lui un nom.
3. Cliquez sur le notebook pour accéder à la page de chat.
4. Dans le panneau de gauche, sous **"Sources"**, faites glisser-déposer des fichiers ou cliquez sur la zone **"Drop files here"** pour sélectionner des fichiers.
5. Les documents téléchargés sont automatiquement ajoutés à la base de données vectorielle et **sélectionnés** par défaut. Vous pouvez sélectionner plusieurs documents pour les interroger simultanément.

### Poser des Questions (RAG)

- Tapez votre question dans l'interface de chat et appuyez sur Entrée.
- Le système effectue une recherche vectorielle, sélectionne les fragments les plus pertinents et génère une réponse en utilisant **qwen2.5:7b-instruct**.
- Les réponses incluent des balises `[[c:N]]` faisant référence aux sources ; cliquez dessus pour voir la page/le texte cité.

### Connexion à une Base de Données MSSQL

Pour connecter un notebook à MSSQL :

1. Dans la section **"Data Sources"** de la page principale, sélectionnez votre notebook.
2. Dans le panneau **MSSQL Configuration**, remplissez les champs suivants :
   1. **Server** – Nom du serveur ou adresse IP
   2. **Port** – Généralement 1433
   3. **Database Name** – Nom de la base de données
   4. **Username** – Nom d'utilisateur de la base de données
   5. **Password** – Mot de passe de la base de données (laissez vide lors d'une mise à jour pour conserver le mot de passe existant)
   6. **Table Name** – La table à interroger
   7. **Timestamp Column** – Colonne d'horodatage pour trier les enregistrements les plus récents
   8. **Text Columns** – Colonnes contenant des données texte (séparées par des virgules, ex : `message, level, source`)
3. Cliquez sur **"Save & Test Connection"**. Le backend teste la connexion et l'enregistre en cas de succès.
4. Allez dans le notebook et sélectionnez **"SQL Source"** dans la liste des sources.
5. Posez des questions en langage naturel ; le système génère des réponses en utilisant à la fois les documents et les données MSSQL.

---

## Formats de Fichier Supportés

Les formats suivants peuvent être téléchargés et utilisés dans RAG :

```
.pdf   .md    .txt   .docx  .pptx  .doc   .ppt
.jpg   .jpeg  .png
```

- **PDF** : Extrait directement si une couche texte existe ; les PDF scannés/images utilisent Falcon-OCR en recours.
- **Images** : OCR pleine page convertit les images en texte.
- **Word/PowerPoint** : Le texte et les images intégrées sont traités séparément (les images sont OCRisées).
- **.doc/.ppt anciens** : Convertir en .docx/.pptx en utilisant LibreOffice avant traitement.

---

## Dépannage

### Erreur de Connexion Ollama

- Vérifiez que `ollama serve` est en cours d'exécution.
- Assurez-vous que `OLLAMA_BASE_URL` est correct (par défaut : `http://localhost:11434`).
- Vérifiez que les modèles sont téléchargés (`ollama list` pour vérifier).

### Le Backend ne Démarre Pas

- Confirmez que toutes les dépendances de `requirements.txt` sont installées.
- Assurez-vous que `rag.env` est présent dans le répertoire `backend/`.
- Vérifiez les permissions d'écriture pour le fichier de base de données SQLite (`app.db`).

### Erreur de Connexion MSSQL

- `MSSQL_ENC_KEY` est-elle définie et est-ce une clé Fernet valide ?
- Le pilote ODBC Driver 18 est-il installé ?
- Le serveur, le port, le nom de la base de données et le nom de la table sont-ils corrects ?
- Les noms de tables/colonnes ne doivent pas contenir de caractères spéciaux ou d'espaces (uniquement des lettres, des chiffres et `_`).

### Erreur LibreOffice

La conversion de fichiers nécessite la commande `soffice`. Si elle n'est pas installée :

```bash
sudo apt-get install -y libreoffice
```

### OCR Lent ou Erreur GPU

Le modèle Falcon-OCR est volumineux et peut être lent sur CPU. Si vous n'avez pas de GPU, soyez patient ou envisagez d'utiliser un modèle OCR plus léger.

---

## Notes de Sécurité

- Les mots de passe MSSQL sont chiffrés avec **Fernet** et stockés dans la base de données ; l'API ne renvoie jamais le mot de passe en clair.
- Les requêtes SQL sont validées contre une liste blanche stricte pour les noms de tables/colonnes (empêchant les injections).
- Le système fonctionne entièrement en local ; vos documents et requêtes ne quittent jamais votre machine.
- Pour les données sensibles, il est recommandé de restreindre l'accès réseau à l'application.

---