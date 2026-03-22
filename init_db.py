"""
Convenience script to run migrations and seed data.
Usage: python init_db.py
"""
import logging
from alembic.config import Config
from alembic import command
from app.database import get_session_local
from app.models.subscription import SubscriptionModel, DEFAULT_SUBSCRIPTIONS

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Running Alembic migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations complete.")

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        existing = db.query(SubscriptionModel).count()
        if existing == 0:
            logger.info("Seeding default subscription plans...")
            for plan in DEFAULT_SUBSCRIPTIONS:
                db.add(SubscriptionModel(**plan))
            db.commit()
            logger.info("Seeded %d subscription plans.", len(DEFAULT_SUBSCRIPTIONS))
        else:
            logger.info("Subscriptions already seeded (%d plans found).", existing)
    finally:
        db.close()
