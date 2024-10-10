from sqlalchemy import Column, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    two_factor_secret = Column(String, nullable=True)
