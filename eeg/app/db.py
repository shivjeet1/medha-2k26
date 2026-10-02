import sqlite3
import hashlib
import os

# Database will be created in the main eeg/ directory when run
DB_PATH = "patients.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dev_id TEXT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            gmail TEXT UNIQUE,
            password_hash TEXT
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_or_create_patient(dev_id, name, age, gender, gmail, password):
    """
    Returns (success_boolean, message, patient_data_dict)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM patients WHERE gmail = ?', (gmail,))
    row = c.fetchone()
    
    pwd_hash = hash_password(password)
    
    if row:
        # Patient exists, verify password
        if row[6] == pwd_hash:
            patient_data = {
                "id": row[1], # dev_id
                "name": row[2],
                "age": row[3],
                "gender": row[4],
                "gmail": row[5]
            }
            conn.close()
            return True, "Login successful", patient_data
        else:
            conn.close()
            return False, "Incorrect password for this email", None
    else:
        # Register new patient
        c.execute('''
            INSERT INTO patients (dev_id, name, age, gender, gmail, password_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (dev_id, name, age, gender, gmail, pwd_hash))
        conn.commit()
        conn.close()
        
        patient_data = {
            "id": dev_id,
            "name": name,
            "age": age,
            "gender": gender,
            "gmail": gmail
        }
        return True, "Registration successful", patient_data
