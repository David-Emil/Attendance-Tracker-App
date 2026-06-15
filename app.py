import tkinter as tk
from attendance import log_attendance, init_attendance_file
from scanner import start_scanner
import threading

init_attendance_file()


def handle_scan(student_id):
    result = log_attendance(student_id)

    if result == "NOT_FOUND":
        update_status("Student not found ❌", "red")

    elif result == "DUPLICATE":
        update_status("Already scanned today ⚠️", "orange")

    else:
        update_status(f"{result} marked ✅", "green")


def update_status(message, color):
    status_label.config(text=message, fg=color)


def run_scanner():
    start_scanner(handle_scan)


root = tk.Tk()
root.title("Attendance Scanner")
root.geometry("500x300")

status_label = tk.Label(root, text="Scan QR...", font=("Arial", 20))
status_label.pack(pady=50)

start_button = tk.Button(root, text="Start Scanner", command=lambda: threading.Thread(target=run_scanner).start())
start_button.pack()

root.mainloop()