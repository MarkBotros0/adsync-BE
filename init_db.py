"""
Convenience script to run migrations and seed data.
Usage: python init_db.py
"""
from alembic.config import Config
from alembic import command
from app.database import get_session_local
from app.models.subscription import SubscriptionModel, DEFAULT_SUBSCRIPTIONS

if __name__ == "__main__":
    print("Running Alembic migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Migrations complete.")

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        existing = db.query(SubscriptionModel).count()
        if existing == 0:
            print("Seeding default subscription plans...")
            for plan in DEFAULT_SUBSCRIPTIONS:
                db.add(SubscriptionModel(**plan))
            db.commit()
            print(f"Seeded {len(DEFAULT_SUBSCRIPTIONS)} subscription plans.")
        else:
            print(f"Subscriptions already seeded ({existing} plans found).")
    finally:
        db.close()
