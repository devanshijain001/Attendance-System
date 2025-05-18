from database.db_connector import get_db_connection

def get_company_by_name(company_name):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM companies WHERE company_name=%s", (company_name,))
    company = cursor.fetchone()
    cursor.close()
    conn.close()
    return company

def create_company(company_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO companies (company_name) VALUES (%s)", (company_name,))
    conn.commit()
    company_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return company_id

def get_company_by_id(company_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM companies WHERE company_id=%s", (company_id,))
    company = cursor.fetchone()
    cursor.close()
    conn.close()
    return company
