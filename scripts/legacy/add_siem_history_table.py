import sqlite3

db_path = "sql_app.db"

def add_siem_history_table():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS siem_sync_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                siem_id INTEGER NOT NULL,
                execution_time DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                status VARCHAR(20) NOT NULL,
                records_fetched INTEGER DEFAULT 0,
                error_message TEXT,
                FOREIGN KEY(siem_id) REFERENCES siem_configuration(siem_id) ON DELETE CASCADE
            );
        """)
        
        # Create an index on execution_time for faster ordering
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_siem_sync_history_time ON siem_sync_history(execution_time);")
        
        conn.commit()
        print("Successfully created siem_sync_history table.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_siem_history_table()
