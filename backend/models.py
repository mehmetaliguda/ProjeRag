# backend/models.py - SQLAlchemy modelleri

from datetime import datetime

from database import db


class Notebook(db.Model):
    __tablename__ = "notebooks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    conversations = db.relationship(
        "Conversation",
        backref="notebook",
        cascade="all, delete-orphan",
        lazy=True,
    )


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    notebook_id = db.Column(db.Integer, db.ForeignKey("notebooks.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    # Bu conversation'da secili olan room id'lerinin listesi (JSON dizi).
    # SQLite'ta JSON tipi TEXT olarak saklanir, SQLAlchemy otomatik
    # serialize/deserialize eder; None yerine her zaman liste donsun diye
    # default olarak bos liste kullaniyoruz.
    selected_room_ids = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    messages = db.relationship(
        "Message",
        backref="conversation",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def to_dict(self):
        """API yanitlarinda kullanilan ortak serialize fonksiyonu."""
        return {
            "id": self.id,
            "notebook_id": self.notebook_id,
            "title": self.title,
            "selected_room_ids": self.selected_room_ids or [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # ör: "user" / "assistant"
    content = db.Column(db.Text, nullable=False)
    citations = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.String(255), primary_key=True)
    display_name = db.Column(db.String(255), nullable=False)
    pdf_path = db.Column(db.String(500), nullable=False)
    image_dir = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notebook_id = db.Column(db.Integer, db.ForeignKey("notebooks.id"), nullable=True)


class MSSQLConfig(db.Model):
    """Notebook basina tek canli MSSQL log kaynagi konfigurasyonu (FAZ 3)."""

    __tablename__ = "mssql_configs"

    id = db.Column(db.Integer, primary_key=True)
    notebook_id = db.Column(db.Integer, db.ForeignKey("notebooks.id"), nullable=False, unique=True)

    server = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=1433)
    database_name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    # Fernet ile sifrelenmis parola (bkz. mssql_crypto.py); asla duz metin degil.
    password_encrypted = db.Column(db.Text, nullable=False)

    table_name = db.Column(db.String(255), nullable=False)
    timestamp_column = db.Column(db.String(255), nullable=False)
    # Log icinde aranacak metin kolonlarinin listesi (JSON dizi).
    text_columns = db.Column(db.JSON, nullable=False, default=list)

    fetch_batch_size = db.Column(db.Integer, nullable=False, default=200)
    max_rows = db.Column(db.Integer, nullable=False, default=2000)

    # qwen2.5:7b-instruct icin retrieval/context butce ayarlari (bkz. mssql_source.py).
    max_retrieval_tokens = db.Column(db.Integer, nullable=False, default=8192)
    max_retrieval_chars = db.Column(db.Integer, nullable=True)
    reserved_output_tokens = db.Column(db.Integer, nullable=False, default=1024)
    max_context_tokens = db.Column(db.Integer, nullable=False, default=32768)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """API yanitlarinda password_encrypted / parola ASLA donmez;
        sadece is_configured=True bilgisi verilir."""
        return {
            "notebook_id": self.notebook_id,
            "server": self.server,
            "port": self.port,
            "database_name": self.database_name,
            "username": self.username,
            "table_name": self.table_name,
            "timestamp_column": self.timestamp_column,
            "text_columns": self.text_columns or [],
            "fetch_batch_size": self.fetch_batch_size,
            "max_rows": self.max_rows,
            "max_retrieval_tokens": self.max_retrieval_tokens,
            "max_retrieval_chars": self.max_retrieval_chars,
            "reserved_output_tokens": self.reserved_output_tokens,
            "max_context_tokens": self.max_context_tokens,
            "is_configured": True,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }