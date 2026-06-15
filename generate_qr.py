import pandas as pd
import qrcode
import os

# Load students
students = pd.read_excel("data/students.xlsx")

# Create folder
output_folder = "qrcodes"
os.makedirs(output_folder, exist_ok=True)

for _, row in students.iterrows():
    student_id = str(row["ID"])
    name = row["Name"]

    qr = qrcode.make(student_id)

    filename = f"{output_folder}/{student_id}_{name}.png"
    qr.save(filename)

    print(f"Created QR for {name}")

print("All QR codes generated ✅")