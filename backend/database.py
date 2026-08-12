import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "app.db")

def init_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        import models  # noqa: F401
        if os.getenv("RESET_DB") == "1":
            db.drop_all()
        db.create_all()

    print(f"[DB] Kullanilan dosya: {DEFAULT_DB_PATH}")  # tanılama için