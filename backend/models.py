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