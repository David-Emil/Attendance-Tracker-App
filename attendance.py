import os
from datetime import datetime

import pandas as pd

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# The roster ships with the code (read-only).
STUDENTS_FILE = os.path.join(APP_DIR, "data", "students.xlsx")

# Attendance is written at runtime. On a host with an ephemeral filesystem
# (e.g. Railway) point DATA_DIR at a mounted persistent volume so records
# survive restarts and redeploys. Defaults to the local ./data folder.
DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(APP_DIR, "data")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.xlsx")

# Students added manually from the app are stored here, on the same
# persistent volume as attendance, NOT in the shipped roster. This keeps the
# original students.xlsx untouched and makes manual additions survive redeploys.
ADDED_STUDENTS_FILE = os.path.join(DATA_DIR, "students_added.xlsx")

ATT_COLUMNS = ["ID", "Name", "Date", "Time"]
STUDENT_COLUMNS = ["ID", "Name"]


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------
def init_attendance_file():
    """Create the attendance workbook if it does not exist yet."""
    os.makedirs(os.path.dirname(ATTENDANCE_FILE), exist_ok=True)
    if not os.path.exists(ATTENDANCE_FILE):
        pd.DataFrame(columns=ATT_COLUMNS).to_excel(ATTENDANCE_FILE, index=False)


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _read_baseline_students():
    """The roster shipped with the code (read-only)."""
    df = pd.read_excel(STUDENTS_FILE)
    df["ID"] = df["ID"].astype(int)
    df["Name"] = df["Name"].astype(str)
    return df[STUDENT_COLUMNS]


def _read_added_students():
    """Students added manually from the app (stored on the volume)."""
    if not os.path.exists(ADDED_STUDENTS_FILE):
        return pd.DataFrame(columns=STUDENT_COLUMNS)
    df = pd.read_excel(ADDED_STUDENTS_FILE)
    if df.empty:
        return pd.DataFrame(columns=STUDENT_COLUMNS)
    df["ID"] = pd.to_numeric(df["ID"], errors="coerce").fillna(0).astype(int)
    df["Name"] = df["Name"].astype(str)
    return df[STUDENT_COLUMNS]


def added_student_ids():
    """Set of IDs that were added manually (so the UI can offer to remove them)."""
    return set(int(i) for i in _read_added_students()["ID"].tolist())


def _read_students():
    """Full roster = shipped baseline + manually added, sorted by ID.

    On an ID clash the shipped baseline wins (manual adds are blocked from
    clashing anyway, so this is purely defensive).
    """
    baseline = _read_baseline_students()
    added = _read_added_students()
    df = pd.concat([baseline, added], ignore_index=True)
    df = df.drop_duplicates(subset=["ID"], keep="first").reset_index(drop=True)
    df = df.sort_values("ID").reset_index(drop=True)
    return df


def _write_added_students(df):
    os.makedirs(DATA_DIR, exist_ok=True)
    df[STUDENT_COLUMNS].to_excel(ADDED_STUDENTS_FILE, index=False)


def next_student_id():
    """The next free ID (max existing + 1), for pre-filling the add form."""
    df = _read_students()
    if df.empty:
        return 1
    return int(df["ID"].max()) + 1


def _read_attendance():
    init_attendance_file()
    df = pd.read_excel(ATTENDANCE_FILE)
    if df.empty:
        return pd.DataFrame(columns=ATT_COLUMNS)
    # Normalise types so comparisons are reliable.
    df["ID"] = pd.to_numeric(df["ID"], errors="coerce").fillna(0).astype(int)
    df["Name"] = df["Name"].astype(str)
    df["Date"] = df["Date"].astype(str).str.slice(0, 10)
    df["Time"] = df["Time"].astype(str).str.slice(0, 8)
    return df


def _write_attendance(df):
    df.to_excel(ATTENDANCE_FILE, index=False)


# ---------------------------------------------------------------------------
# Core actions
# ---------------------------------------------------------------------------
def already_marked(df, student_id, date):
    return ((df["ID"] == int(student_id)) & (df["Date"] == date)).any()


def log_attendance(student_id, date=None):
    """Mark a student present.

    Returns the student's name on success, or one of the sentinel strings
    "NOT_FOUND" / "DUPLICATE". Backward compatible with the desktop scanner
    (date defaults to today).
    """
    try:
        sid = int(str(student_id).strip())
    except (TypeError, ValueError):
        return "NOT_FOUND"

    date = date or _today()
    students = _read_students()
    att = _read_attendance()

    student = students[students["ID"] == sid]
    if student.empty:
        return "NOT_FOUND"

    if already_marked(att, sid, date):
        return "DUPLICATE"

    name = student.iloc[0]["Name"]
    now = datetime.now()
    new_row = {
        "ID": sid,
        "Name": name,
        "Date": date,
        "Time": now.strftime("%H:%M:%S"),
    }
    att = pd.concat([att, pd.DataFrame([new_row])], ignore_index=True)
    _write_attendance(att)
    return name


def remove_attendance(student_id, date=None):
    """Undo a check-in for the given student/date. Returns True if removed."""
    try:
        sid = int(str(student_id).strip())
    except (TypeError, ValueError):
        return False

    date = date or _today()
    att = _read_attendance()
    mask = (att["ID"] == sid) & (att["Date"] == date)
    if not mask.any():
        return False
    _write_attendance(att[~mask].reset_index(drop=True))
    return True


def add_student(name, student_id=None):
    """Add a student manually. Stored on the volume, never in the shipped file.

    Returns a dict:
      {"status": "ok", "id": int, "name": str}
      {"status": "invalid_name"}
      {"status": "invalid_id"}
      {"status": "exists", "id": int}   # ID already in the roster
    """
    name = ("" if name is None else str(name)).strip()
    if not name:
        return {"status": "invalid_name"}

    # ID: use the given one, or auto-assign the next free ID.
    if student_id is None or str(student_id).strip() == "":
        sid = next_student_id()
    else:
        try:
            sid = int(str(student_id).strip())
        except (TypeError, ValueError):
            return {"status": "invalid_id"}
        if sid <= 0:
            return {"status": "invalid_id"}

    if (_read_students()["ID"] == sid).any():
        return {"status": "exists", "id": sid}

    added = _read_added_students()
    new_row = {"ID": sid, "Name": name}
    added = pd.concat([added, pd.DataFrame([new_row])], ignore_index=True)
    _write_added_students(added)
    return {"status": "ok", "id": sid, "name": name}


def remove_added_student(student_id):
    """Remove a manually-added student. Only the added file is touched; the
    shipped roster can never be modified. Returns True if removed."""
    try:
        sid = int(str(student_id).strip())
    except (TypeError, ValueError):
        return False

    added = _read_added_students()
    mask = added["ID"] == sid
    if not mask.any():
        return False  # not a manually-added student → refuse
    _write_added_students(added[~mask].reset_index(drop=True))
    return True


# ---------------------------------------------------------------------------
# Read models for the UI
# ---------------------------------------------------------------------------
def get_day_data(date=None):
    """Everything the dashboard needs for one date in a single payload."""
    date = date or _today()
    students = _read_students()
    att = _read_attendance()
    day = att[att["Date"] == date]
    added_ids = added_student_ids()

    # id -> time present
    present_times = dict(zip(day["ID"], day["Time"]))

    roster = []
    present = []
    absent = []
    for _, s in students.iterrows():
        sid = int(s["ID"])
        name = s["Name"]
        time = present_times.get(sid)
        is_present = time is not None
        entry = {"id": sid, "name": name, "present": is_present, "time": time,
                 "added": sid in added_ids}
        roster.append(entry)
        if is_present:
            present.append({"id": sid, "name": name, "time": time})
        else:
            absent.append({"id": sid, "name": name})

    present.sort(key=lambda r: r["time"] or "")
    total = len(students)
    npresent = len(present)
    rate = round(npresent / total * 100) if total else 0

    return {
        "date": date,
        "stats": {"present": npresent, "absent": total - npresent,
                  "total": total, "rate": rate},
        "present": present,
        "absent": absent,
        "roster": roster,
    }


def get_summary():
    """Per-student attendance across every recorded session."""
    students = _read_students()
    att = _read_attendance()

    sessions = sorted(att["Date"].dropna().unique().tolist())
    nsessions = len(sessions)
    counts = att.groupby("ID").size().to_dict()

    rows = []
    for _, s in students.iterrows():
        sid = int(s["ID"])
        c = int(counts.get(sid, 0))
        rate = round(c / nsessions * 100) if nsessions else 0
        rows.append({"id": sid, "name": s["Name"], "count": c, "rate": rate})

    rows.sort(key=lambda r: (-r["count"], r["id"]))
    return {"sessions": nsessions, "dates": sessions, "students": rows}
