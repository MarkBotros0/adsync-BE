from app.database import init_db, Base
from app.models.session import SessionModel

if __name__ == "__main__":
    print("Initializing database...")
    print("Creating tables for models...")
    init_db()
    print("Database initialized successfully!")
    print(f"Tables created: {', '.join([table.name for table in Base.metadata.sorted_tables])}")
