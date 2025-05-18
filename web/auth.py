from database.db_connector import get_db_connection
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_admin(username, password, company_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admins WHERE username=%s AND company_id=%s", (username, company_id))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()
    if admin and admin['password_hash'] == hash_password(password):
        return admin
    return None

def create_admin(username, name, password, company_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO admins (username, name, password_hash, company_id) VALUES (%s, %s, %s, %s)",
        (username, name, hash_password(password), company_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
