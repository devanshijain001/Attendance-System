import cv2
import os
import sys
import mysql.connector
from database.db_connector import get_db_connection

def collect_data(user_id=None, name=None):
    if user_id is None:
        user_id = input("Enter user ID: ")
    if name is None:
        name = input("Enter user name: ")

    # Add user to database is now handled in Streamlit, so skip here

    # Create image directory
    path = os.path.join('data', str(user_id))
    os.makedirs(path, exist_ok=True)
    
    cap = cv2.VideoCapture(0)
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow(f"Capturing {name} - Press 's' to save, 'q' to quit", frame)
        key = cv2.waitKey(1)
        if key == ord('s'):
            img_path = os.path.join(path, f"{count}.jpg")
            cv2.imwrite(img_path, frame)
            print(f"Saved {img_path}")
            count += 1
        elif key == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        collect_data(sys.argv[1], sys.argv[2])
    else:
        collect_data()
