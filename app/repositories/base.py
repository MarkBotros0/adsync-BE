from datetime import datetime
from typing import Generic, TypeVar, Type
from sqlalchemy.orm import Session

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository with common CRUD and soft-delete operations.

    All ``get``/``get_all`` queries automatically exclude soft-deleted rows
    (rows where ``deleted_at IS NOT NULL``).
    """

    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> T | None:
        """Get a single active (non-deleted) record by primary key."""
        return (
            self.db.query(self.model)
            .filter(self.model.id == id, self.model.deleted_at.is_(None))
            .first()
        )

    def get_by_field(self, **kwargs) -> T | None:
        """Get a single active record matching all given field values."""
        return (
            self.db.query(self.model)
            .filter_by(**kwargs)
            .filter(self.model.deleted_at.is_(None))
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Get all active records with pagination."""
        return (
            self.db.query(self.model)
            .filter(self.model.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, obj: T) -> T:
        """Persist a new record."""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: T) -> T:
        """Commit pending changes on an existing record."""
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def soft_delete(self, id: int) -> bool:
        """Soft-delete a record by setting ``deleted_at``. Returns True if found."""
        obj = self.get(id)
        if not obj:
            return False
        obj.deleted_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def delete(self, obj: T) -> None:
        """Hard-delete — use only for admin cleanup. Prefer ``soft_delete``."""
        self.db.delete(obj)
        self.db.commit()

    def delete_by_id(self, id: int) -> bool:
        """Hard-delete by id. Prefer ``soft_delete``."""
        obj = self.get(id)
        if obj:
            self.delete(obj)
            return True
        return False
