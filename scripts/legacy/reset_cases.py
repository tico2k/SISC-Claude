from sqlalchemy.orm import Session
from backend.database import SessionLocal, engine
from backend import models

def reset_cases():
    db = SessionLocal()
    try:
        # Delete all cases. 
        # Due to ON DELETE CASCADE configuration in models, this should clean up:
        # - ClarificationSubmission
        # - ReviewHistory
        # - ClarificationAttachment
        num_deleted = db.query(models.ClarificationCase).delete()
        db.commit()
        print(f"Successfully deleted {num_deleted} cases and related data.")
    except Exception as e:
        print(f"Error resetting cases: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure tables exist (though they should)
    models.Base.metadata.create_all(bind=engine)
    reset_cases()
