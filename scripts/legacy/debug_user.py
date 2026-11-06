from backend.database import SessionLocal
from backend import models, dependencies

def debug_user():
    db = SessionLocal()
    try:
        user_email = "security@fleitlab.com"
        user = db.query(models.User).filter(models.User.user_email == user_email).first()
        
        if not user:
            print(f"User {user_email} NOT FOUND!")
        else:
            print(f"User {user_email} FOUND.")
            print(f"ID: {user.user_id}")
            print(f"Role: {user.role}")
            print(f"Hashed Password: {user.hashed_password}")
            
            is_valid = dependencies.verify_password("password", user.hashed_password)
            print(f"Password 'password' valid?: {is_valid}")
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_user()
