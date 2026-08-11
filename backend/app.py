# app.py - Coklu PDF ("oda") destekleyen Flask API

import os
import traceback

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from rag_chat import room_manager
from database import db, init_db
from models import Notebook, Conversation, Message, Room

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
    rooms = room_manager.list_rooms()
    # room_manager RAM'deki oda listesini dondurur, notebook_id icermez.
    # DB'deki Room satirlariyla id uzerinden eslestirip zenginlestiriyoruz;
    # geriye donuk kirilma olmasin diye mevcut alanlar oldugu gibi kaliyor.
    notebook_ids_by_room = {
        row.id: row.notebook_id for row in Room.query.all()
    }
    for room in rooms:
        room_id = room.get("id")
        room["notebook_id"] = notebook_ids_by_room.get(room_id)
    return jsonify({"rooms": rooms})


@app.route('/notebooks/<int:nb_id>/rooms', methods=['GET'])
def list_notebook_rooms(nb_id):
    notebook = Notebook.query.get(nb_id)
    if notebook is None:
        return jsonify({"error": "Notebook bulunamadi"}), 404

    rows = Room.query.filter_by(notebook_id=nb_id).order_by(Room.created_at).all()
    rooms = []
    for row in rows:
        document_count = None
        try:
            document_count = room_manager.get_room(row.id).document_count
        except (FileNotFoundError, AttributeError):
            pass
        rooms.append({
            "id": row.id,
            "name": row.display_name,
            "notebook_id": row.notebook_id,
            "document_count": document_count,
            "created_at": row.created_at.isoformat(),
        })

    return jsonify({"rooms": rooms})


@app.route('/rooms', methods=['POST'])
def upload_room():
    if 'file' not in request.files:
        return jsonify({"error": "Dosya gonderilmedi (form alani: 'file')"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Dosya secilmedi"}), 400

    notebook_id = request.form.get("notebook_id")
    if not notebook_id:
        return jsonify({"error": "notebook_id alani zorunlu"}), 400
    notebook = Notebook.query.get(notebook_id)
    if notebook is None:
        return jsonify({"error": "Notebook bulunamadi"}), 404

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "Sadece PDF dosyasi yuklenebilir"}), 400

    display_name = secure_filename(file.filename)
    tmp_path = os.path.join("/tmp", display_name)
    file.save(tmp_path)

    try:
        room = room_manager.create_room_from_upload(tmp_path, display_name, notebook_id=notebook.id)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    return jsonify({"id": room.room_id, "name": room.display_name}), 201


@app.route('/rooms/<room_id>', methods=['DELETE'])
def delete_room(room_id):
    try:
        room_manager.delete_room(room_id)
    except FileNotFoundError:
        return jsonify({"error": "Oda bulunamadi"}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "success"}), 200


@app.route('/source-pdf/<room_id>')
def serve_pdf(room_id):
    try:
        room = room_manager.get_room(room_id)
    except FileNotFoundError:
        return jsonify({"error": "Oda bulunamadi"}), 404
    directory = os.path.dirname(room.pdf_path)
    filename = os.path.basename(room.pdf_path)
    return send_from_directory(directory, filename)


@app.route('/notebooks/<int:nb_id>', methods=['DELETE'])
def delete_notebook(nb_id):
    notebook = Notebook.query.get(nb_id)
    if notebook is None:
        return jsonify({"error": "Notebook bulunamadi"}), 404

    # Notebook'a bagli tum room'lari RAM + disk + DB'den temizle
    # (Conversation/Message'lar zaten model relationship'inde
    # cascade="all, delete-orphan" ile otomatik silinir).
    room_rows = Room.query.filter_by(notebook_id=nb_id).all()
    for row in room_rows:
        try:
            room_manager.delete_room(row.id)
        except FileNotFoundError:
            pass

    db.session.delete(notebook)
    db.session.commit()

    return jsonify({"status": "success"}), 200


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

    selected_room_ids = data.get("selected_room_ids") or []

    conversation = Conversation(notebook_id=nb_id, title=title, selected_room_ids=selected_room_ids)
    db.session.add(conversation)
    db.session.commit()

    return jsonify(conversation.to_dict()), 201


@app.route('/notebooks/<int:nb_id>/conversations', methods=['GET'])
def list_conversations(nb_id):
    notebook = Notebook.query.get(nb_id)
    if notebook is None:
        return jsonify({"error": "Notebook bulunamadi"}), 404

    conversations = Conversation.query.filter_by(notebook_id=nb_id).order_by(Conversation.created_at).all()
    return jsonify([c.to_dict() for c in conversations])


@app.route('/conversations/<int:conv_id>', methods=['PATCH'])
def update_conversation(conv_id):
    conversation = Conversation.query.get(conv_id)
    if conversation is None:
        return jsonify({"error": "Conversation bulunamadi"}), 404

    data = request.get_json(silent=True) or {}
    if "selected_room_ids" not in data:
        return jsonify({"error": "selected_room_ids alani zorunlu"}), 400

    selected_room_ids = data.get("selected_room_ids")
    if not isinstance(selected_room_ids, list):
        return jsonify({"error": "selected_room_ids bir liste olmali"}), 400

    conversation.selected_room_ids = selected_room_ids
    db.session.commit()

    return jsonify(conversation.to_dict()), 200


@app.route('/conversations/<int:conv_id>', methods=['GET'])
def get_conversation(conv_id):
    conversation = Conversation.query.get(conv_id)
    if conversation is None:
        return jsonify({"error": "Conversation bulunamadi"}), 404

    return jsonify(conversation.to_dict())


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

@app.route('/conversations/<int:conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    conversation = Conversation.query.get(conv_id)
    if conversation is None:
        return jsonify({"error": "Conversation bulunamadi"}), 404

    # Message'lar cascade="all, delete-orphan" sayesinde otomatik silinir.
    db.session.delete(conversation)
    db.session.commit()

    return jsonify({"status": "success"}), 200

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

        user_input = data.get("soru", "")
        conversation_id = data.get("conversation_id")

        room_ids = data.get("rooms")
        if not room_ids:
            single = data.get("room")
            room_ids = [single] if single else []
        if not room_ids:
            return jsonify({"error": "room veya rooms alani zorunlu"}), 400
        if not user_input:
            return jsonify({"error": "soru alani bos olamaz"}), 400

        # conversation_id opsiyonel: gecersiz/bulunamayan bir id gelirse
        # sohbeti engellemiyoruz, sadece mesaj kaydini atliyoruz.
        conversation = None
        if conversation_id is not None:
            conversation = Conversation.query.get(conversation_id)
            if conversation is None:
                print(f"[FLASK] Uyari: conversation_id={conversation_id} bulunamadi, mesaj kaydi atlanacak")

        print(f"[FLASK] Oda(lar): {', '.join(room_ids)} | Soru: {user_input}")

        if len(room_ids) == 1:
            room = room_manager.get_room(room_ids[0])
            result = room.get_rag_answer(user_input)
        else:
            from rag_chat import get_multi_room_answer
            result = get_multi_room_answer(room_ids, user_input)

        print(f"[FLASK] Result alindi, citations: {len(result.get('citations', {}))} adet")

        citations = {}
        for cid, info in (result.get("citations") or {}).items():
            cite_room_id = info.get("room_id", room_ids[0])

            page = info.get("page")
            pdf_url = f"{BASE_URL}/source-pdf/{cite_room_id}#page={page + 1}" if page is not None else None

            citations[cid] = {
                "page": page,
                "text": info.get("text"),
                "pdf_url": pdf_url,
                "room_id": cite_room_id,
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
    app.run(debug=True, port=5000, use_reloader=False)