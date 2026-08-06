# backend/database.py - Flask-SQLAlchemy kurulumu

import os

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """
    Flask app'e SQLAlchemy'yi baglar ve tablolari (yoksa) olusturur.
    DATABASE_URL ortam degiskeni verilmezse varsayilan olarak
    'sqlite:///app.db' kullanilir.
    """
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        import models  # noqa: F401 - modellerin db.Model'e kaydolmasi icin gerekli
        db.create_all()
