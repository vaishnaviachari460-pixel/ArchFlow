from flask import Flask, render_template, request, jsonify, make_response

from analyzer import analyze_communication
from database import (
    init_database, init_action_table, save_analysis, get_history,
    get_previous_communications, save_actions, get_actions,
    update_action_status, get_latest_analysis_id, get_latest_analysis,
)
from memory import detect_changes

app = Flask(__name__)
init_database()
init_action_table()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/results/<int:analysis_id>")
def results_page(analysis_id):
    return render_template("results.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        communication = request.form.get("communication", "").strip()
        if not communication:
            return jsonify({"error": "Please enter some project communication."}), 400

        previous = get_previous_communications(limit=1)
        result = analyze_communication(communication)
        result["changes"] = detect_changes(communication, previous).get("changes", [])

        analysis_id = save_analysis(communication, result)
        saved_actions = save_actions(result.get("actions", []), analysis_id)
        result["actions"] = saved_actions
        result["analysis_id"] = analysis_id
        result["success"] = True
        return jsonify(result)
    except Exception as error:
        print("ARCHFLOW ERROR:", error)
        return jsonify({"error": str(error)}), 500


@app.route("/history", methods=["GET"])
def history():
    try:
        return jsonify({"history": get_history(20)})
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/history/<int:analysis_id>", methods=["GET"])
def history_item(analysis_id):
    try:
        from database import get_connection, _analysis_row_to_dict
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
        if not row:
            return jsonify({"error": "Analysis not found."}), 404
        result = _analysis_row_to_dict(row)
        result["actions"] = get_actions(analysis_id)
        return jsonify(result)
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/actions", methods=["GET"])
def actions():
    try:
        latest_id = get_latest_analysis_id()
        return jsonify({"actions": get_actions(latest_id) if latest_id else []})
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/actions/<int:action_id>", methods=["PUT"])
def update_action(action_id):
    try:
        data = request.get_json(silent=True) or {}
        status = str(data.get("status", "")).strip().upper().replace("_", " ")
        if status not in {"PENDING", "IN PROGRESS", "COMPLETED"}:
            return jsonify({"error": "Invalid action status."}), 400
        if not update_action_status(action_id, status):
            return jsonify({"error": "Action not found."}), 404
        return jsonify({"success": True, "id": action_id, "status": status})
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route("/latest", methods=["GET"])
def latest():
    try:
        result = get_latest_analysis()
        if not result:
            return jsonify({"analysis": None})
        latest_id = result["id"]
        result["actions"] = get_actions(latest_id)
        return jsonify({"analysis": result})
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.after_request
def add_no_cache_headers(response):
    if request.path.startswith(("/latest", "/history", "/actions")):
        response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(debug=True)
