import face_recognition
import cv2
import pickle
import numpy as np
import sys
import mysql.connector
import time
from database.db_connector import get_db_connection

def mark_attendance(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM attendance 
            WHERE user_id = %s 
            AND timestamp > NOW() - INTERVAL 5 MINUTE
        """, (user_id,))
        if not cursor.fetchone():
            try:
                cursor.execute("""
                    INSERT INTO attendance (user_id) 
                    VALUES (%s)
                """, (user_id,))
                conn.commit()
                cursor.close()
                conn.close()
                return "marked"
            except mysql.connector.IntegrityError as e:
                if e.errno == 1062:
                    cursor.close()
                    conn.close()
                    return "already_marked"
                else:
                    cursor.close()
                    conn.close()
                    return "db_error"
        else:
            cursor.close()
            conn.close()
            return "already_marked"
    except Exception as e:
        return "db_error"

def load_company_users(company_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, name FROM users WHERE company_id=%s", (company_id,))
    users = {str(row['user_id']): row['name'] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return users

def run_recognition(company_id, once=False):
    with open('models/encodings.pkl', 'rb') as f:
        data = pickle.load(f)
    allowed_users = load_company_users(company_id)
    filtered_encodings = []
    filtered_ids = []
    filtered_names = []
    for i, user_id in enumerate(data['ids']):
        if str(user_id) in allowed_users:
            filtered_encodings.append(data['encodings'][i])
            filtered_ids.append(user_id)
            filtered_names.append(data['names'][i])
    video_capture = cv2.VideoCapture(0)

    required_consistent_frames = 5
    frame_window = 7
    recent_names = []

    recognized_name = None
    recognized_user_id = None
    attendance_status = None
    start_time = time.time()
    duration = 10 if once else None
    face_detected_time = None

    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        name = "Unknown"
        user_id = None
        if face_encodings and filtered_encodings:
            face_encoding = face_encodings[0]
            matches = face_recognition.compare_faces(filtered_encodings, face_encoding)
            face_distances = face_recognition.face_distance(filtered_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                user_id = filtered_ids[best_match_index]
                name = filtered_names[best_match_index]

        recent_names.append(name)
        if len(recent_names) > frame_window:
            recent_names.pop(0)

        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.putText(frame, name, (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow('Face Recognition - Press Q to quit', frame)

        if once:
            elapsed = time.time() - start_time
            if name != "Unknown" and recent_names.count(name) >= required_consistent_frames:
                if recognized_name is None:
                    attendance_status = mark_attendance(user_id)
                    recognized_name = name
                    recognized_user_id = user_id
                    face_detected_time = time.time()
            if recognized_name:
                elapsed_since_detection = time.time() - face_detected_time
                if elapsed_since_detection > 5:
                    break
            elif elapsed > duration:
                break

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    if not recognized_name:
        end_time = time.time() + 5
        while time.time() < end_time:
            ret, frame = video_capture.read()
            if not ret:
                break
            cv2.imshow('Face Recognition - No face recognized', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    video_capture.release()
    cv2.destroyAllWindows()

    if once:
        if recognized_name:
            if attendance_status == "marked":
                print(f"Attendance marked for: {recognized_name}")
            elif attendance_status == "already_marked":
                print(f"Attendance already marked for: {recognized_name}")
            else:
                print("Database error. Please try again.")
        else:
            print("Face not recognized.")

if __name__ == "__main__":
    once = '--once' in sys.argv
    try:
        company_id = int(sys.argv[1])
    except (IndexError, ValueError):
        print("Error: company_id must be provided as the first argument.")
        sys.exit(1)
    run_recognition(company_id=company_id, once=once)
