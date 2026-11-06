import sqlite3

db_path = "sql_app.db"

def add_cron_column():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE siem_configuration ADD COLUMN cron_expression VARCHAR(50);")
        conn.commit()
        print("Successfully added cron_expression column to siem_configuration table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'cron_expression' already exists.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_cron_column()
