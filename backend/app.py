# app.py - Coklu PDF ("oda") destekleyen Flask API

import os
import traceback

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from rag_chat import room_manager
from database import db, init_db
from models import Notebook, Conversation, Message

app = Flask(__name__)
CORS(app)

# Flask 3.x'te before_first_request kaldirildi; DB kurulumunu app olusturulur
# olusturulmaz yapiyoruz (ilk isteten once calismis olur).
init_db(app)

ALLOWED_EXT = {".pdf"}
BASE_URL = os.getenv("APP_BASE_URL", "http://sunucuIP:5000")


# ------------------------------------------------------------------
# Oda (Room) endpoint'leri - degismedi, mevcut room_manager sozlesmesi
# oldugu gibi kullaniliyor.
# ------------------------------------------------------------------
@app.route('/rooms', methods=['GET'])
def list_rooms():
    return jsonify({"rooms": room_manager.list_rooms()})


@app.route('/rooms', methods=['POST'])
def upload_room():
    if 'file' not in request.files:
        return jsonify({"error": "Dosya gonderilmedi (form alani: 'file')"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Dosya secilmedi"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "Sadece PDF dosyasi yuklenebilir"}), 400

    display_name = secure_filename(file.filename)
    tmp_path = os.path.join("/tmp", display_name)
    file.save(tmp_path)

    try:
        room = room_manager.create_room_from_upload(tmp_path, display_name)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return jsonify({"room": room.to_dict()}), 201


@app.route('/source-pdf/<room_id>')
def serve_pdf(room_id):
    try:
        room = room_manager.get_room(room_id)
    except FileNotFoundError:
        return jsonify({"error": "Oda bulunamadi"}), 404
    directory = os.path.dirname(room.pdf_path)
    filename = os.path.basename(room.pdf_path)
    return send_from_directory(directory, filename)


@app.route('/images/<room_id>/<path:filename>')
def serve_image(room_id, filename):
    try:
        room = room_manager.get_room(room_id)
    except FileNotFoundError:
        return jsonify({"error": "Oda bulunamadi"}), 404
    return send_from_directory(room.image_dir, filename)


# ------------------------------------------------------------------
# Notebook endpoint'leri
# ------------------------------------------------------------------
@app.route('/notebooks', methods=['POST'])
def create_notebook():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "name alani zorunlu"}), 400

    notebook = Notebook(name=name)
    db.session.add(notebook)
    db.session.commit()

    return jsonify({"id": notebook.id, "name": notebook.name}), 201


@app.route('/notebooks', methods=['GET'])
def list_notebooks():
    notebooks = Notebook.query.order_by(Notebook.created_at).all()
    return jsonify([{"id": nb.id, "name": nb.name} for nb in notebooks])


# ------------------------------------------------------------------
# Conversation endpoint'leri
# ------------------------------------------------------------------
@app.route('/notebooks/<int:nb_id>/conversations', methods=['POST'])
def create_conversation(nb_id):
    notebook = Notebook.query.get(nb_id)
    if notebook is None:
        return jsonify({"error": "Notebook bulunamadi"}), 404

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title alani zorunlu"}), 400

    conversation = Conversation(notebook_id=nb_id, title=title)
    db.session.add(conversation)
    db.session.commit()

    return jsonify({"id": conversation.id, "title": conversation.title}), 201


@app.route('/notebooks/<int:nb_id>/conversations', methods=['GET'])
def list_conversations(nb_id):
    notebook = Notebook.query.get(nb_id)
    if notebook is None:
        return jsonify({"error": "Notebook bulunamadi"}), 404

    conversations = Conversation.query.filter_by(notebook_id=nb_id).order_by(Conversation.created_at).all()
    return jsonify([{"id": c.id, "title": c.title} for c in conversations])


# ------------------------------------------------------------------
# Message endpoint'leri
# ------------------------------------------------------------------
@app.route('/conversations/<int:conv_id>/messages', methods=['POST'])
def create_message(conv_id):
    conversation = Conversation.query.get(conv_id)
    if conversation is None:
        return jsonify({"error": "Conversation bulunamadi"}), 404

    data = request.get_json(silent=True) or {}
    role = data.get("role")
    content = data.get("content")
    if not role:
        return jsonify({"error": "role alani zorunlu"}), 400
    if not content:
        return jsonify({"error": "content alani zorunlu"}), 400

    message = Message(conversation_id=conv_id, role=role, content=content)
    db.session.add(message)
    db.session.commit()

    return jsonify({
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "timestamp": message.timestamp.isoformat(),
    }), 201


@app.route('/conversations/<int:conv_id>/messages', methods=['GET'])
def list_messages(conv_id):
    conversation = Conversation.query.get(conv_id)
    if conversation is None:
        return jsonify({"error": "Conversation bulunamadi"}), 404

    messages = Message.query.filter_by(conversation_id=conv_id).order_by(Message.timestamp).all()
    return jsonify([
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in messages
    ])


# ------------------------------------------------------------------
# Chat - RAG mantigi degismedi, sadece opsiyonel conversation_id ile
# mesaj kaydi eklendi.
# ------------------------------------------------------------------
@app.route('/chat-client', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON verisi gonderilmedi"}), 400

        room_id = data.get("room")
        user_input = data.get("soru", "")
        conversation_id = data.get("conversation_id")

        if not room_id:
            return jsonify({"error": "room alani zorunlu"}), 400
        if not user_input:
            return jsonify({"error": "soru alani bos olamaz"}), 400

        conversation = None
        if conversation_id is not None:
            conversation = Conversation.query.get(conversation_id)
            if conversation is None:
                return jsonify({"error": "Conversation bulunamadi"}), 404

        print(f"[FLASK] Oda: {room_id} | Soru: {user_input}")

        room = room_manager.get_room(room_id)
        result = room.get_rag_answer(user_input)

        print(f"[FLASK] Result alindi, citations: {len(result.get('citations', {}))} adet")

        citations = {}
        for cid, info in (result.get("citations") or {}).items():
            image_url = None
            if info.get("image"):
                image_url = f"{BASE_URL}/images/{room_id}/{info['image']}"

            page = info.get("page")
            pdf_url = f"{BASE_URL}/source-pdf/{room_id}#page={page + 1}" if page is not None else None

            citations[cid] = {
                "page": page,
                "image": image_url,
                "text": info.get("text"),
                "pdf_url": pdf_url,
            }

        # conversation_id verildiyse kullanici sorusunu ve asistan cevabini kaydet.
        if conversation is not None:
            user_message = Message(conversation_id=conversation.id, role="user", content=user_input)
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=result["text"],
                citations=citations,
            )
            db.session.add(user_message)
            db.session.add(assistant_message)
            db.session.commit()

        return jsonify({"text": result["text"], "citations": citations, "status": "success"})

    except FileNotFoundError:
        return jsonify({"error": "Oda bulunamadi", "status": "error"}), 404
    except Exception as e:
        print(f"[FLASK HATA] {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
