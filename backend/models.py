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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    messages = db.relationship(
        "Message",
        backref="conversation",
        cascade="all, delete-orphan",
        lazy=True,
    )


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
