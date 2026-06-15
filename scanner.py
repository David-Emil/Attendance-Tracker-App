import cv2
from pyzbar.pyzbar import decode


def start_scanner(callback):
    cap = cv2.VideoCapture(0)
    scanned_ids = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        for barcode in decode(frame):
            student_id = barcode.data.decode("utf-8")

            if student_id not in scanned_ids:
                callback(student_id)
                scanned_ids.add(student_id)

        cv2.imshow("QR Scanner", frame)

        if cv2.waitKey(1) == 27:  # ESC to exit
            break

    cap.release()
    cv2.destroyAllWindows()