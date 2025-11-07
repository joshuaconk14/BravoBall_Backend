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

# Helper to create progress history
def create_progress_history(db: Session, user_id: int, current_streak: int = 0, previous_streak: int = 0):
    progress_history = ProgressHistory(
        user_id=user_id,
        current_streak=current_streak,
        previous_streak=previous_streak,
        highest_streak=max(current_streak, previous_streak),
        completed_sessions_count=0,
        favorite_drill=None,
        drills_per_session=0.0,
        minutes_per_session=0.0,
        total_time_all_sessions=0,
        dribbling_drills_completed=0,
        first_touch_drills_completed=0,
        passing_drills_completed=0,
        shooting_drills_completed=0,
        defending_drills_completed=0,
        goalkeeping_drills_completed=0,
        fitness_drills_completed=0,
        most_improved_skill=None,
        unique_drills_completed=0,
        beginner_drills_completed=0,
        intermediate_drills_completed=0,
        advanced_drills_completed=0,
        mental_training_sessions=0,
        total_mental_training_minutes=0
    )
    db.add(progress_history)
    db.commit()
    db.refresh(progress_history)
    return progress_history

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
def test_progress_history(db_session, test_user):
    """Create a progress history record for the test user"""
    progress_history = create_progress_history(db_session, test_user.id, current_streak=0, previous_streak=0)
    yield progress_history
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


def test_streak_and_reset(db_session, test_user, test_progress_history, auth_headers):
    # Clean up any old sessions for this user
    db_session.query(CompletedSession).filter(CompletedSession.user_id == test_user.id).delete()
    db_session.commit()

    # Create two sessions using the API endpoint (which handles streak calculation)
    # Use explicit dates to avoid timing issues
    today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)  # Noon today
    yesterday = today - timedelta(days=1)  # Noon yesterday
    
    print(f"Creating sessions for: {yesterday.date()} and {today.date()}")
    
    # Create session for yesterday
    yesterday_session_data = {
        "date": yesterday.isoformat(),
        "total_completed_drills": 1,
        "total_drills": 1,
        "drills": [{
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
    }
    
    # Create session for today
    today_session_data = {
        "date": today.isoformat(),
        "total_completed_drills": 1,
        "total_drills": 1,
        "drills": [{
            "drill": {
                "uuid": "uuid-2",
                "title": "Drill 2",
                "skill": "shooting",
                "subSkills": ["accuracy"],
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
    }
    
    # Create sessions via API (this will properly calculate streaks)
    response1 = client.post("/api/sessions/completed/", json=yesterday_session_data, headers=auth_headers)
    assert response1.status_code == 200
    print(f"First session created: {response1.json()}")
    
    response2 = client.post("/api/sessions/completed/", json=today_session_data, headers=auth_headers)
    assert response2.status_code == 200
    print(f"Second session created: {response2.json()}")

    # 1. Streak should be 2 (incremented when creating sessions)
    response = client.get("/api/progress_history/")
    assert response.status_code == 200
    data = response.json()
    print(f"Progress history: {data}")
    assert data["current_streak"] == 2
    assert data["previous_streak"] in (0, 2)  # previous_streak may be 0 or 2 depending on prior state
    
    # Store the initial streak for later comparison
    initial_streak = data["current_streak"]

    # 2. Simulate a break: move both sessions to 3 and 2 days ago (streak should reset after 2+ days)
    old1 = today - timedelta(days=3)
    old2 = today - timedelta(days=2)
    sessions = db_session.query(CompletedSession).filter(CompletedSession.user_id == test_user.id).all()
    sessions[0].date = old1
    sessions[1].date = old2
    db_session.commit()

    # 3. Streak should reset to 0, previous_streak should be the initial streak
    # The API checks for streak expiration when days_since_last > 1
    response = client.get("/api/progress_history/")
    assert response.status_code == 200
    data = response.json()
    assert data["current_streak"] == 0
    assert data["previous_streak"] == initial_streak 