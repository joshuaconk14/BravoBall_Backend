"""
Test configuration file for pytest
Contains fixtures and setup for testing
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import sys
import jwt
from datetime import datetime, timedelta
from typing import Dict, Generator
import json

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import Base, get_db
from models import User, DrillGroup, Drill, DrillCategory, DrillSkillFocus
from main import app
from config import UserAuth

# Use JSON type for SQLite instead of ARRAY which is not supported
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa
from sqlalchemy.types import TypeDecorator

# Custom type to handle arrays in SQLite
class ArrayAdapter(TypeDecorator):
    impl = JSON
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

# Replace ARRAY types with our custom type for SQLite
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.sql.sqltypes import ARRAY

@compiles(ARRAY, 'sqlite')
def compile_array(element, compiler, **kw):
    return compiler.visit_JSON(element, **kw)

# Override array implementation in User model for testing
for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, ARRAY):
            column.type = ArrayAdapter()

# In-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Test client with a fresh database."""
    def _get_test_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = _get_test_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db):
    """Create a test user."""
    # Hash a password for the test user
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("testpassword")
    
    # Create test user in database
    user = User(
        first_name="Test", 
        last_name="User", 
        email="test@example.com", 
        hashed_password=hashed_password,
        primary_goal="improve_skill",
        biggest_challenge=["lack_of_time"],
        training_experience="intermediate",
        position="striker",
        playstyle=["offensive"],
        age_range="adult",
        strengths=["shooting", "dribbling"],
        areas_to_improve=["passing", "first_touch"],
        training_location=["small_field", "backyard"],
        available_equipment=["ball", "cones"],
        daily_training_time="30",
        weekly_training_days="3"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@pytest.fixture(scope="function")
def test_user_token(test_user):
    """Create a JWT token for the test user."""
    # Define the token expiration (e.g., 30 minutes)
    expiration = datetime.utcnow() + timedelta(minutes=30)
    
    # Create the JWT payload
    payload = {
        "sub": test_user.email,
        "user_id": test_user.id,
        "exp": expiration
    }
    
    # Encode the JWT token
    token = jwt.encode(payload, UserAuth.SECRET_KEY, algorithm=UserAuth.ALGORITHM)
    
    return token

@pytest.fixture(scope="function")
def auth_headers(test_user_token):
    """Create authorization headers for the test user."""
    return {"Authorization": f"Bearer {test_user_token}"}

@pytest.fixture(scope="function")
def test_drill_category(db):
    """Create a test drill category."""
    category = DrillCategory(
        name="dribbling",
        description="Drills focusing on dribbling skills"
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category

@pytest.fixture(scope="function")
def test_drill(db, test_drill_category):
    """Create a test drill."""
    drill = Drill(
        title="Test Dribbling Drill",
        description="A drill to practice dribbling",
        category_id=test_drill_category.id,
        duration=10,
        intensity="medium",
        training_styles=["medium_intensity"],
        type="time_based",
        sets=None,
        reps=None,
        rest=None,
        equipment=["ball", "cones"],
        suitable_locations=["small_field", "backyard"],
        difficulty="intermediate",
        instructions=["Step 1", "Step 2"],
        tips=["Tip 1", "Tip 2"],
        common_mistakes=["Mistake 1"],
        progression_steps=["Progress 1"],
        variations=["Variation 1"],
        video_url=None,
        thumbnail_url=None
    )
    db.add(drill)
    db.commit()
    db.refresh(drill)
    
    # Add skill focus
    primary_skill = DrillSkillFocus(
        drill_id=drill.id,
        category="dribbling",
        sub_skill="close_control",
        is_primary=True
    )
    db.add(primary_skill)
    
    secondary_skill = DrillSkillFocus(
        drill_id=drill.id,
        category="dribbling",
        sub_skill="ball_mastery",
        is_primary=False
    )
    db.add(secondary_skill)
    
    db.commit()
    
    return drill

@pytest.fixture(scope="function")
def test_drill_group(db, test_user):
    """Create a test drill group."""
    group = DrillGroup(
        user_id=test_user.id,
        name="Test Group",
        description="A test drill group",
        drills=[],
        is_liked_group=False
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return group 