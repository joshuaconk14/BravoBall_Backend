"""
db.py
This file defintes the database URL and starts the engine to initialize the db
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://jordinho:m44YMQsbrxpewhTJRzzX@localhost/tekkdb"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# from databases import Database
# from sqlalchemy import create_engine, MetaData

# DATABASE_URL = "postgresql+asyncpg://jordinho:m44YMQsbrxpewhTJRzzX@localhost/tekkdb"

# database = Database(DATABASE_URL)
# engine = create_engine(DATABASE_URL)
# metadata = MetaData()

# from sqlalchemy import Table, Column, Integer, String, ForeignKey
# from sqlalchemy.orm import relationship
# from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()

# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True, index=True)
#     username = Column(String, unique=True, index=True)
#     email = Column(String, unique=True, index=True)
#     hashed_password = Column(String)
#     chat_history = relationship("ChatHistory", back_populates="user")

# class ChatHistory(Base):
#     __tablename__ = "chat_history"
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"))
#     session_id = Column(String, index=True)
#     message = Column(String)
#     user = relationship("User", back_populates="chat_history")


