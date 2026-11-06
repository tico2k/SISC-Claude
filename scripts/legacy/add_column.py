import sqlite3

def add_column():
    try:
        conn = sqlite3.connect('sql_app.db')
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE siem_configuration ADD COLUMN test_query TEXT")
        conn.commit()
        print("Column 'test_query' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
