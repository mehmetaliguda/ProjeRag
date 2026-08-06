# app.py - Coklu PDF ("oda") destekleyen Flask API

import os
import traceback

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from rag_chat import room_manager

app = Flask(__name__)
CORS(app)

ALLOWED_EXT = {".pdf"}
BASE_URL = os.getenv("APP_BASE_URL", "http://sunucuIP:5000")


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


@app.route('/chat-client', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON verisi gonderilmedi"}), 400

        room_id = data.get("room")
        user_input = data.get("soru", "")

        if not room_id:
            return jsonify({"error": "room alani zorunlu"}), 400
        if not user_input:
            return jsonify({"error": "soru alani bos olamaz"}), 400

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

        return jsonify({"text": result["text"], "citations": citations, "status": "success"})

    except FileNotFoundError:
        return jsonify({"error": "Oda bulunamadi", "status": "error"}), 404
    except Exception as e:
        print(f"[FLASK HATA] {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
