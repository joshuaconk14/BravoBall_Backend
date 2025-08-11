import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from main import app
from models import User, CompletedSession, ProgressHistory
from db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user
import uuid

client = TestClient(app)

# Helper to create a user and return user + auth headers (mocked)
def create_test_user(db: Session, email=None):
    if email is None:
        email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        first_name="Test",
        last_name="User",
        email=email,
        hashed_password="fakehashed",
        primary_goal="improve_skill",
        biggest_challenge=[],
        training_experience="beginner",
        position="winger",
        playstyle=[],
        age_range="teen",
        strengths=[],
        areas_to_improve=[],
        training_location=[],
        available_equipment=[],
        daily_training_time="30",
        weekly_training_days="moderate"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Helper to create a completed session
def create_completed_session(db: Session, user_id: int, date: datetime):
    session = CompletedSession(
        user_id=user_id,
        date=date,
        total_completed_drills=1,
        total_drills=1,
        drills=[{
            "drill": {
                "uuid": "uuid-1",
                "title": "Drill 1",
                "skill": "dribbling",
                "subSkills": ["ball_mastery"],
                "sets": 1,
                "reps": 1,
                "duration": 10,
                "description": "desc",
                "instructions": ["step1"],
                "tips": ["tip1"],
                "equipment": ["ball"],
                "trainingStyle": "low_intensity",
                "difficulty": "beginner",
                "videoUrl": ""
            },
            "setsDone": 1,
            "totalSets": 1,
            "totalReps": 1,
            "totalDuration": 10,
            "isCompleted": True
        }]
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@pytest.fixture
def db_session():
    db = next(get_db())
    yield db
    # Clean up any test data in correct order (respect foreign keys)
    db.query(ProgressHistory).filter(ProgressHistory.user_id.in_(
        db.query(User.id).filter(User.email.like("testuser_%@example.com"))
    )).delete(synchronize_session=False)
    db.query(CompletedSession).filter(CompletedSession.user_id.in_(
    db.query(User.id).filter(User.email.like("testuser_%@example.com"))
    )).delete(synchronize_session=False)
    db.query(User).filter(User.email.like("testuser_%@example.com")).delete()
    db.commit()

@pytest.fixture
def test_user(db_session):
    user = create_test_user(db_session)
    yield user
    # Cleanup is handled in db_session fixture

@pytest.fixture
def auth_headers(test_user):
    # Mock authentication dependency (replace with your actual auth if needed)
    return {"Authorization": f"Bearer testtoken-{test_user.id}"}

@pytest.fixture(autouse=True)
def override_get_current_user(test_user):
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_streak_and_reset(db_session, test_user, auth_headers):
    # Clean up any old sessions for this user
    db_session.query(CompletedSession).filter(CompletedSession.user_id == test_user.id).delete()
    db_session.commit()

    # Create two sessions: yesterday and today
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    create_completed_session(db_session, test_user.id, yesterday)
    create_completed_session(db_session, test_user.id, today)

    # 1. Streak should be 2
    response = client.get("/api/progress_history/")
    assert response.status_code == 200
    data = response.json()
    assert data["current_streak"] == 2
    assert data["previous_streak"] in (0, 2)  # previous_streak may be 0 or 2 depending on prior state

    # 2. Simulate a break: move both sessions to 3 and 2 days ago (streak should reset after 2+ days)
    old1 = today - timedelta(days=3)
    old2 = today - timedelta(days=2)
    sessions = db_session.query(CompletedSession).filter(CompletedSession.user_id == test_user.id).all()
    sessions[0].date = old1
    sessions[1].date = old2
    db_session.commit()

    # 3. Streak should reset to 0, previous_streak should be 2 (since last session was 2 days ago)
    response = client.get("/api/progress_history/")
    assert response.status_code == 200
    data = response.json()
    assert data["current_streak"] == 0
    assert data["previous_streak"] == 2 