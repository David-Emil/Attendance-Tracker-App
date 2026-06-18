import io
import os
from datetime import datetime

import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file

from attendance import (
    init_attendance_file,
    log_attendance,
    remove_attendance,
    get_day_data,
    get_summary,
    add_student,
    remove_added_student,
    next_student_id,
)

app = Flask(__name__)
init_attendance_file()


def _date_arg():
    """Return a validated YYYY-MM-DD date from the request, or today."""
    raw = request.values.get("date")
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now().strftime("%Y-%m-%d")


@app.route("/")
def home():
    return render_template("index.html")


# ----- actions -------------------------------------------------------------
@app.route("/checkin", methods=["POST"])
def checkin():
    data = request.get_json(silent=True) or {}
    student_id = data.get("id")
    date = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    result = log_attendance(student_id, date)

    if result == "NOT_FOUND":
        return jsonify({"status": "not_found", "id": student_id})
    if result == "DUPLICATE":
        return jsonify({"status": "duplicate", "id": student_id})
    return jsonify({"status": "ok", "id": student_id, "name": result})


@app.route("/uncheck", methods=["POST"])
def uncheck():
    data = request.get_json(silent=True) or {}
    ok = remove_attendance(data.get("id"), data.get("date"))
    return jsonify({"status": "ok" if ok else "missing"})


# ----- roster management ---------------------------------------------------
@app.route("/api/next_id")
def api_next_id():
    return jsonify({"next_id": next_student_id()})


@app.route("/add_student", methods=["POST"])
def add_student_route():
    data = request.get_json(silent=True) or {}
    result = add_student(data.get("name"), data.get("id"))
    return jsonify(result)


@app.route("/remove_student", methods=["POST"])
def remove_student_route():
    data = request.get_json(silent=True) or {}
    ok = remove_added_student(data.get("id"))
    # ok is False either because the id is unknown or because it belongs to the
    # shipped roster, which must never be modified.
    return jsonify({"status": "ok" if ok else "protected"})


# Backwards-compatible alias for the old endpoint name.
@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json(silent=True) or {}
    return jsonify({"result": log_attendance(data.get("id"))})


# ----- read models ---------------------------------------------------------
@app.route("/api/day")
def api_day():
    return jsonify(get_day_data(_date_arg()))


@app.route("/api/summary")
def api_summary():
    return jsonify(get_summary())


# Old endpoint kept for compatibility (today's records).
@app.route("/attendance")
def get_attendance():
    return jsonify(get_day_data()["present"])


# ----- exports -------------------------------------------------------------
def _send_xlsx(df, filename):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/export/day")
def export_day():
    date = _date_arg()
    data = get_day_data(date)
    df = pd.DataFrame(data["present"]).rename(
        columns={"id": "ID", "name": "Name", "time": "Time"}
    )
    if df.empty:
        df = pd.DataFrame(columns=["ID", "Name", "Time"])
    return _send_xlsx(df, f"attendance_{date}.xlsx")


@app.route("/export/summary")
def export_summary():
    data = get_summary()
    df = pd.DataFrame(data["students"]).rename(
        columns={"id": "ID", "name": "Name", "count": "Sessions Attended", "rate": "Rate %"}
    )
    return _send_xlsx(df, "attendance_summary.xlsx")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
