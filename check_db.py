import sqlite3
import os

try:
    conn = sqlite3.connect('patientpath.db')
    cursor = conn.cursor()
    cursor.execute("SELECT last_action, updated_at FROM patients WHERE tracking_id='CV-12345'")
    row = cursor.fetchone()
    print(f"DB Result: {row}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
