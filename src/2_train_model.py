import face_recognition
import os
import pickle
import mysql.connector
from database.db_connector import get_db_connection

def train_model():
    known_encodings = []
    known_ids = []
    known_names = []
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    for user_id in os.listdir('data'):
        user_path = os.path.join('data', user_id)
        if os.path.isdir(user_path):
            cursor.execute("SELECT name FROM users WHERE user_id=%s", (user_id,))
            user = cursor.fetchone()
            name = user['name'] if user else user_id
            for img_name in os.listdir(user_path):
                img_path = os.path.join(user_path, img_name)
                image = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    encoding = encodings[0]
                    known_encodings.append(encoding)
                    known_ids.append(int(user_id))
                    known_names.append(name)
    cursor.close()
    conn.close()
    data = {
        "encodings": known_encodings,
        "ids": known_ids,
        "names": known_names
    }
    os.makedirs('models', exist_ok=True)
    with open('models/encodings.pkl', 'wb') as f:
        pickle.dump(data, f)
    print("Training completed. Encodings saved.")

if __name__ == "__main__":
    train_model()
