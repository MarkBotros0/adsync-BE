from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: Type[T], db: Session):
        self.model = model
        self.db = db
    
    def get(self, id: int) -> Optional[T]:
        """Get single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_by_field(self, **kwargs) -> Optional[T]:
        """Get single record by field"""
        return self.db.query(self.model).filter_by(**kwargs).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, obj: T) -> T:
        """Create new record"""
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def update(self, obj: T) -> T:
        """Update existing record"""
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def delete(self, obj: T) -> None:
        """Delete record"""
        self.db.delete(obj)
        self.db.commit()
    
    def delete_by_id(self, id: int) -> bool:
        """Delete record by ID"""
        obj = self.get(id)
        if obj:
            self.delete(obj)
            return True
        return False

