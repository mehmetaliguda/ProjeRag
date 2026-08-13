# ------------------------------------------------------------------
# Notebook endpoint'leri
# ------------------------------------------------------------------
@app.route('/notebooks', methods=['POST'])
def create_notebook():
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        if not name:
            return jsonify({"error": "name alani zorunlu"}), 400

        notebook = Notebook(name=name)
        db.session.add(notebook)
        db.session.commit()

        return jsonify({"id": notebook.id, "name": notebook.name}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error", "traceback": traceback.format_exc()}), 500

@app.route('/notebooks/<int:nb_id>', methods=['DELETE'])
def delete_notebook(nb_id):
    notebook = Notebook.query.get(nb_id)
    if notebook is None:
        return jsonify({"error": "Notebook bulunamadi"}), 404

    room_rows = Room.query.filter_by(notebook_id=nb_id).all()
    for row in room_rows:
        try:
            room_manager.delete_room(row.id)
        except FileNotFoundError:
            pass
        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": f"Room silinemedi ({row.id}): {e}"}), 500

    db.session.delete(notebook)
    db.session.commit()

    # Notebook'a ait ust klasor (rag_rooms/<notebook_id>/) rooms silindikten
    # sonra bos kalir ama kendisi silinmez - onu da temizle.
    notebook_dir = os.path.join(rag_chat.ROOMS_ROOT, str(nb_id))
    if os.path.isdir(notebook_dir):
        shutil.rmtree(notebook_dir)

    print(f"[delete_notebook] notebook {nb_id} silindi ({len(room_rows)} room ile birlikte)")

    return jsonify({"status": "success"}), 200


@app.route('/notebooks', methods=['GET'])
def list_notebooks():
    try:
        notebooks = Notebook.query.order_by(Notebook.created_at).all()
        return jsonify([{"id": nb.id, "name": nb.name} for nb in notebooks])
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e), "status": "error", "traceback": traceback.format_exc()}), 500



