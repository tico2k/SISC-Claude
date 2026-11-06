import sqlite3
import os
from pathlib import Path

def migrate():
    # Check multiple possible locations for the database
    possible_paths = [
        Path("sql_app.db"),
        Path("../sql_app.db"),
        Path("backend/sql_app.db")
    ]
    
    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        print("Database file sql_app.db not found in common locations.")
        print("Please run this script from the project root or backend directory.")
        return

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check for missing columns in clarification_case
    cursor.execute("PRAGMA table_info(clarification_case)")
    columns = [column[1] for column in cursor.fetchall()]

    # Add incident_num if missing
    if "incident_num" not in columns:
        print("Adding 'incident_num' column to 'clarification_case' table...")
        try:
            cursor.execute("ALTER TABLE clarification_case ADD COLUMN incident_num INTEGER")
            print("Successfully added 'incident_num'.")
        except sqlite3.Error as e:
            print(f"Error adding 'incident_num': {e}")
    else:
        print("'incident_num' column already exists.")

    # Add original_log_link if missing
    if "original_log_link" not in columns:
        print("Adding 'original_log_link' column to 'clarification_case' table...")
        try:
            cursor.execute("ALTER TABLE clarification_case ADD COLUMN original_log_link TEXT")
            print("Successfully added 'original_log_link'.")
        except sqlite3.Error as e:
            print(f"Error adding 'original_log_link': {e}")
    else:
        print("'original_log_link' column already exists.")

    conn.commit()
    
    # 2. Enum Migration (Fix ResponseValidationError)
    print("\nStarting Enum migration (aligning names with Korean values)...")
    
    enums_to_migrate = {
        "users": {
            "role": {
                "USER": "일반",
                "SECURITY_ADMIN": "보안관리자",
                "AUDIT_TEAM": "감사팀",
                "SYSTEM_ADMIN": "시스템관리자"
            }
        },
        "clarification_case": {
            "case_type": {
                "INFO_LEAK": "정보유출",
                "SECURITY_VIOLATION": "보안위반",
                "SYSTEM_ACCESS": "시스템접근",
                "AUTH_ABUSE": "권한오남용"
            },
            "case_status": {
                "UNCLASSIFIED": "미확인",
                "REQUEST": "요청",
                "SUBMIT": "제출",
                "APPROVE": "승인",
                "REJECT": "반려",
                "CLOSE": "종결"
            },
            "priority": {
                "LOW": "낮음",
                "MEDIUM": "보통",
                "HIGH": "높음"
            },
            "case_result": {
                "JUSTIFIED": "정당 사유",
                "FALSE_POSITIVE": "오탐",
                "MINOR_VIOLATION": "경미한 위반",
                "INSUFFICIENT": "소명 불충분",
                "EDUCATION_NEEDED": "교육 필요",
                "DISCIPLINARY_ACTION": "징계 요청"
            }
        },
        "review_history": {
            "case_status": {
                "UNCLASSIFIED": "미확인",
                "REQUEST": "요청",
                "SUBMIT": "제출",
                "APPROVE": "승인",
                "REJECT": "반려",
                "CLOSE": "종결"
            },
            "case_result": {
                "JUSTIFIED": "정당 사유",
                "FALSE_POSITIVE": "오탐",
                "MINOR_VIOLATION": "경미한 위반",
                "INSUFFICIENT": "소명 불충분",
                "EDUCATION_NEEDED": "교육 필요",
                "DISCIPLINARY_ACTION": "징계 요청"
            }
        }
    }

    for table, columns_map in enums_to_migrate.items():
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            print(f"Table '{table}' not found. Skipping.")
            continue
            
        for column, mapping in columns_map.items():
            # Check if column exists
            cursor.execute(f"PRAGMA table_info({table})")
            table_cols = [c[1] for c in cursor.fetchall()]
            if column not in table_cols:
                print(f"Column '{column}' in table '{table}' not found. Skipping.")
                continue
                
            print(f"Migrating {table}.{column} values...")
            for old_val, new_val in mapping.items():
                try:
                    cursor.execute(f"UPDATE {table} SET {column} = ? WHERE {column} = ?", (new_val, old_val))
                    if cursor.rowcount > 0:
                        print(f"  Updated {cursor.rowcount} rows: {old_val} -> {new_val}")
                except sqlite3.Error as e:
                    print(f"  Error updating {old_val}: {e}")

    conn.commit()
    conn.close()
    print("\nMigration completed successfully.")

if __name__ == "__main__":
    migrate()
