import sqlite3

db_path = 'c:/PATIENTPATH-AI/backend/patientpath.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Check if column exists
    cursor.execute("PRAGMA table_info(occupancy_logs)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'unique_ids' not in columns:
        print("Adding unique_ids column...")
        cursor.execute("ALTER TABLE occupancy_logs ADD COLUMN unique_ids TEXT")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column unique_ids already exists.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
