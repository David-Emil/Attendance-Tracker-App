import pandas as pd
from datetime import datetime

ATTENDANCE_FILE = "data/attendance.xlsx"
STUDENTS_FILE = "data/students.xlsx"


def get_today_attendance():
    df = pd.read_excel(ATTENDANCE_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    return df[df["Date"] == today]


def get_absent_students():
    students = pd.read_excel(STUDENTS_FILE)
    today_att = get_today_attendance()

    return students[~students["ID"].isin(today_att["ID"])]


def get_late_students(cutoff="09:00:00"):
    df = get_today_attendance()
    return df[df["Time"] > cutoff]