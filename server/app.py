import os
import sys
import json
from flask import Flask, render_template, jsonify, request, send_file, abort
from flask_cors import CORS

# Agregar raíz al sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from server.inventory_manager import InventoryManager
from server.decision_manager import DecisionManager, VALID_CATEGORIES, VALID_DISCARD_REASONS
from server.thumbnail_service import ThumbnailService
from server.export_service import ExportService

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
CORS(app)

# Inicializar servicios
config_file = os.path.join(BASE_DIR, "config.json")
with open(config_file, "r", encoding="utf-8") as cf:
    config = json.load(cf)

inv_manager = InventoryManager(config_file)
inv_manager.load_inventory()

dec_manager = DecisionManager(config_file)
thumb_service = ThumbnailService(os.path.join(BASE_DIR, config.get("thumbnail_cache_dir", "data/cache/thumbnails")))
export_service = ExportService(inv_manager, dec_manager, os.path.join(BASE_DIR, config.get("export_dir", "clasificado")))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    decisions = dec_manager.get_all_decisions()
    total_images = inv_manager.get_total_images()
    total_batches = inv_manager.get_total_batches()

    cat_counts = {"R": 0, "S": 0, "D": 0, "X": 0}
    reviewed_fruits = set()

    for img_id, dec in decisions.items():
        cat = dec.get("category")
        if cat in cat_counts:
            cat_counts[cat] += 1
        item = inv_manager.get_image(img_id)
        if item:
            reviewed_fruits.add(item.get("fruit_id"))

    total_reviewed = len(decisions)
    total_pending = total_images - total_reviewed

    session = dec_manager.get_session()
    current_batch_id = session.get("current_batch_id", 1)
    completed_batches = dec_manager.get_completed_batches()

    return jsonify({
        "total_images": total_images,
        "total_reviewed": total_reviewed,
        "total_pending": total_pending,
        "total_fruits": len(inv_manager.inventory_by_fruit),
        "reviewed_fruits_count": len(reviewed_fruits),
        "total_batches": total_batches,
        "current_batch_id": current_batch_id,
        "completed_batches": completed_batches,
        "category_counts": cat_counts,
        "session": session
    })


@app.route("/api/batch/<int:batch_id>", methods=["GET"])
def get_batch(batch_id):
    items = inv_manager.get_batch(batch_id)
    if not items:
        return jsonify({"error": f"Lote {batch_id} no encontrado"}), 404

    decisions = dec_manager.get_all_decisions()
    batch_items = []
    stats = {"R": 0, "S": 0, "D": 0, "X": 0, "pending": 0, "total": len(items)}

    for item in items:
        img_id = item["image_id"]
        dec = decisions.get(img_id)
        item_copy = dict(item)
        if dec:
            item_copy["decision"] = dec
            cat = dec["category"]
            stats[cat] = stats.get(cat, 0) + 1
        else:
            item_copy["decision"] = None
            stats["pending"] += 1
        batch_items.append(item_copy)

    is_completed = (stats["pending"] == 0)
    summary = dec_manager.get_batch_summary(batch_id)

    # Si está completado y no tenía resumen, registrarlo
    if is_completed and not summary:
        dec_manager.record_batch_completion(batch_id, stats)
        summary = dec_manager.get_batch_summary(batch_id)

    return jsonify({
        "batch_id": batch_id,
        "stats": stats,
        "is_completed": is_completed,
        "summary": summary,
        "items": batch_items
    })


@app.route("/api/image/<path:image_id>", methods=["GET"])
def get_image_file(image_id):
    item = inv_manager.get_image(image_id)
    if not item:
        abort(404)
    file_path = os.path.join(BASE_DIR, item["file_path"])
    if not os.path.exists(file_path):
        abort(404)
    return send_file(file_path, mimetype="image/jpeg", max_age=86400)


@app.route("/api/thumbnail/<path:image_id>", methods=["GET"])
def get_thumbnail_file(image_id):
    item = inv_manager.get_image(image_id)
    if not item:
        abort(404)
    file_path = os.path.join(BASE_DIR, item["file_path"])
    thumb_path = thumb_service.get_thumbnail_path(file_path, image_id)
    if not thumb_path or not os.path.exists(thumb_path):
        abort(404)
    return send_file(thumb_path, mimetype="image/jpeg", max_age=86400)


@app.route("/api/fruit_comparison/<fruit_id>", methods=["GET"])
def get_fruit_comparison(fruit_id):
    items = inv_manager.get_fruit_images(fruit_id)
    if not items:
        return jsonify({"error": f"Fruta {fruit_id} no encontrada"}), 404

    decisions = dec_manager.get_all_decisions()
    results = []
    for item in items:
        item_copy = dict(item)
        item_copy["decision"] = decisions.get(item["image_id"])
        results.append(item_copy)

    # Ordenar por día y vista
    results.sort(key=lambda r: (r["day"], r["view"]))
    return jsonify({
        "fruit_id": fruit_id,
        "total_images": len(results),
        "images": results
    })


@app.route("/api/decision", methods=["POST"])
def post_decision():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Datos requeridos"}), 400

    image_id = data.get("image_id")
    category = data.get("category")
    note = data.get("note", "")
    reason = data.get("reason", None)

    if not image_id or not category:
        return jsonify({"error": "image_id y category son obligatorios"}), 400

    item = inv_manager.get_image(image_id)
    if not item:
        return jsonify({"error": f"Imagen {image_id} no existe en inventario"}), 404

    try:
        saved = dec_manager.save_decision(
            image_id=image_id,
            category=category,
            note=note,
            reason=reason
        )
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Error al guardar decisión: {str(e)}"}), 500

    # Comprobar si el lote actual se completó
    batch_id = item["batch_id"]
    batch_items = inv_manager.get_batch(batch_id)
    all_decisions = dec_manager.get_all_decisions()

    pending_in_batch = sum(1 for it in batch_items if it["image_id"] not in all_decisions)
    batch_completed = (pending_in_batch == 0)

    if batch_completed:
        # Calcular estadísticas y guardar resumen de lote
        stats = {"R": 0, "S": 0, "D": 0, "X": 0, "pending": 0, "total": len(batch_items)}
        for it in batch_items:
            d = all_decisions.get(it["image_id"])
            if d:
                stats[d["category"]] += 1
        dec_manager.record_batch_completion(batch_id, stats)

    # Actualizar estado de sesión
    dec_manager.update_session(batch_id=batch_id, image_id=image_id)

    return jsonify({
        "status": "ok",
        "decision": saved,
        "batch_completed": batch_completed,
        "batch_id": batch_id,
        "pending_in_batch": pending_in_batch
    })


@app.route("/api/undo", methods=["POST"])
def post_undo():
    data = request.get_json(silent=True) or {}
    raw_steps = data.get("steps", 1) if isinstance(data, dict) else 1
    try:
        steps = int(raw_steps)
    except (ValueError, TypeError):
        steps = 1
    if steps < 1:
        steps = 1

    res = dec_manager.undo_last_decision(steps=steps)
    if not res:
        return jsonify({"status": "empty", "message": "No hay más acciones para deshacer"}), 200

    # Actualizar sesión para que apunte a la imagen restaurada
    restored_img = res.get("image_id")
    if restored_img:
        dec_manager.update_session(phase2_image_id=restored_img, image_id=restored_img)

    return jsonify({
        "status": "ok",
        "image_id": res["image_id"],
        "restored_state": res["restored_state"],
        "undone_count": res.get("undone_count", 1),
        "undone_items": res.get("undone_items", []),
        "remaining_undo_count": res.get("remaining_undo_count", 0)
    })


@app.route("/api/session", methods=["GET", "POST"])
def handle_session():
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        batch_id = data.get("batch_id")
        image_id = data.get("image_id")
        active_filter = data.get("active_filter")
        active_phase = data.get("active_phase")
        phase2_category = data.get("phase2_category")
        phase2_image_id = data.get("phase2_image_id")
        dec_manager.update_session(
            batch_id=batch_id,
            image_id=image_id,
            active_filter=active_filter,
            active_phase=active_phase,
            phase2_category=phase2_category,
            phase2_image_id=phase2_image_id
        )
        return jsonify({"status": "ok", "session": dec_manager.get_session()})

    return jsonify(dec_manager.get_session())


@app.route("/api/phase2/pool", methods=["GET"])
def get_phase2_pool():
    target_cat = request.args.get("category", "R").strip().upper()
    if target_cat not in ("R", "S", "D"):
        target_cat = "R"

    status_filter = request.args.get("filter", "all").strip().lower()

    decisions = dec_manager.get_all_decisions()
    inv_items = inv_manager.inventory

    cat_counts = {"R": 0, "S": 0, "D": 0, "X": 0}
    phase2_stats = {
        "R": {"total": 0, "kept": 0, "pending": 0},
        "S": {"total": 0, "kept": 0, "pending": 0},
        "D": {"total": 0, "kept": 0, "pending": 0}
    }

    pool_items = []

    for item in inv_items:
        img_id = item["image_id"]
        dec = decisions.get(img_id)
        if not dec:
            continue
        cat = dec.get("category")
        if cat in cat_counts:
            cat_counts[cat] += 1

        if cat in ("R", "S", "D"):
            phase2_stats[cat]["total"] += 1
            is_kept = bool(dec.get("phase2_reviewed") and dec.get("phase2_action") == "kept")
            if is_kept:
                phase2_stats[cat]["kept"] += 1
            else:
                phase2_stats[cat]["pending"] += 1

            if cat == target_cat:
                if status_filter == "pending" and is_kept:
                    continue
                if status_filter == "kept" and not is_kept:
                    continue

                item_copy = dict(item)
                item_copy["decision"] = dec
                item_copy["phase2_reviewed"] = bool(dec.get("phase2_reviewed"))
                item_copy["phase2_action"] = dec.get("phase2_action")
                pool_items.append(item_copy)

    target_goal = int(request.args.get("target_goal", 1500))
    if target_goal < 1:
        target_goal = 1500

    total_r = cat_counts["R"]
    total_s = cat_counts["S"]
    diff = total_r - total_s
    surplus_r = max(0, total_r - target_goal)
    surplus_s = max(0, total_s - target_goal)
    is_goal_reached = (total_r == target_goal and total_s == target_goal)
    is_balanced = (total_r == total_s and total_r > 0)

    return jsonify({
        "category": target_cat,
        "filter": status_filter,
        "stats": {
            "total_r": total_r,
            "total_s": total_s,
            "total_d": cat_counts["D"],
            "total_x": cat_counts["X"],
            "target_goal": target_goal,
            "target_total": target_goal * 2,
            "surplus_r": surplus_r,
            "surplus_s": surplus_s,
            "is_goal_reached": is_goal_reached,
            "difference": diff,
            "abs_difference": abs(diff),
            "is_balanced": is_balanced,
            "ratio": round(total_r / total_s, 3) if total_s > 0 else 0,
            "pct_r": round((total_r / (total_r + total_s) * 100), 1) if (total_r + total_s) > 0 else 50.0,
            "pct_s": round((total_s / (total_r + total_s) * 100), 1) if (total_r + total_s) > 0 else 50.0,
            "pool_total": phase2_stats[target_cat]["total"],
            "pool_kept": phase2_stats[target_cat]["kept"],
            "pool_pending": phase2_stats[target_cat]["pending"]
        },
        "items": pool_items
    })


@app.route("/api/phase2/action", methods=["POST"])
def post_phase2_action():
    data = request.get_json(force=True) or {}
    image_id = data.get("image_id")
    action = data.get("action")  # 'keep' or 'discard'
    note = data.get("note", "")

    if not image_id or not action:
        return jsonify({"error": "image_id y action son obligatorios"}), 400

    item = inv_manager.get_image(image_id)
    if not item:
        return jsonify({"error": f"Imagen {image_id} no encontrada"}), 404

    try:
        if action == "keep":
            saved = dec_manager.mark_phase2_keep(image_id)
        elif action == "discard":
            saved = dec_manager.mark_phase2_discard(image_id, note)
        elif action == "transfer":
            target_cat = data.get("target_category")
            saved = dec_manager.mark_phase2_transfer(image_id, target_cat, note)
        else:
            return jsonify({"error": f"Accion desconocida: {action}"}), 400

        category = data.get("category", "R")
        dec_manager.update_session(
            active_phase="phase2",
            phase2_category=category,
            phase2_image_id=image_id
        )

        decisions = dec_manager.get_all_decisions()
        r_cnt = sum(1 for d in decisions.values() if d.get("category") == "R")
        s_cnt = sum(1 for d in decisions.values() if d.get("category") == "S")
        x_cnt = sum(1 for d in decisions.values() if d.get("category") == "X")
        d_cnt = sum(1 for d in decisions.values() if d.get("category") == "D")

        target_goal = int(data.get("target_goal", 1500))
        if target_goal < 1:
            target_goal = 1500
        surplus_r = max(0, r_cnt - target_goal)
        surplus_s = max(0, s_cnt - target_goal)

        return jsonify({
            "status": "ok",
            "action": action,
            "decision": saved,
            "stats": {
                "total_r": r_cnt,
                "total_s": s_cnt,
                "total_d": d_cnt,
                "total_x": x_cnt,
                "target_goal": target_goal,
                "target_total": target_goal * 2,
                "surplus_r": surplus_r,
                "surplus_s": surplus_s,
                "difference": r_cnt - s_cnt,
                "abs_difference": abs(r_cnt - s_cnt),
                "is_goal_reached": (r_cnt == target_goal and s_cnt == target_goal),
                "is_balanced": (r_cnt == s_cnt and r_cnt > 0),
                "ratio": round(r_cnt / s_cnt, 3) if s_cnt > 0 else 0,
                "pct_r": round((r_cnt / (r_cnt + s_cnt) * 100), 1) if (r_cnt + s_cnt) > 0 else 50.0,
                "pct_s": round((s_cnt / (r_cnt + s_cnt) * 100), 1) if (r_cnt + s_cnt) > 0 else 50.0
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/phase2/reset_round", methods=["POST"])
def post_phase2_reset_round():
    data = request.get_json(silent=True) or {}
    category = data.get("category", None)
    res = dec_manager.start_phase2_new_round(category)
    return jsonify({
        "status": "ok",
        "message": f"Nueva ronda iniciada. Se reinició el estado para {res['reset_count']} imágenes.",
        "result": res
    })


@app.route("/api/export", methods=["POST"])
def post_export():
    try:
        report = export_service.run_export()
        return jsonify({"status": "ok", "report": report})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/protocol", methods=["GET"])
def get_protocol():
    proto_path = os.path.join(BASE_DIR, "PROTOCOLO_REVISION.md")
    if os.path.exists(proto_path):
        with open(proto_path, "r", encoding="utf-8") as pf:
            content = pf.read()
        return jsonify({"status": "ok", "content": content})
    return jsonify({"status": "error", "content": "Protocolo no encontrado"}), 404


def run():
    host = config.get("server_host", "127.0.0.1")
    port = int(config.get("server_port", 5000))
    print(f"\n" + "=" * 65)
    print(f"  SERVIDOR DE CLASIFICACIÓN VISUAL - HASS AVOCADO DATASET")
    print(f"  Enlazado a: http://{host}:{port}/")
    print(f"  Presiona Ctrl+C en la terminal para detener el servidor.")
    print("=" * 65 + "\n")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    run()
