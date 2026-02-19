
import sqlite3
import os

DB_PATH = "patientpath.db"

def add_mobile_column():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(patients)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "mobile" in columns:
            print("Column 'mobile' already exists in 'patients' table.")
        else:
            print("Adding 'mobile' column to 'patients' table...")
            cursor.execute("ALTER TABLE patients ADD COLUMN mobile VARCHAR(20)")
            conn.commit()
            print("Successfully added 'mobile' column.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_mobile_column()
