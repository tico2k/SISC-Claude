from backend.database import engine, Base
from backend import models

def recreate_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database recreated successfully.")

if __name__ == "__main__":
    recreate_database()
