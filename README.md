# Soccer Training App Backend

A FastAPI-based backend service that provides personalized soccer training recommendations and program generation.

## Core Features

### 1. Drill Recommendation System
- Personalized drill recommendations based on:
  - Player skill level
  - Position
  - Available equipment
  - Training goals
- Scoring algorithm that considers:
  - Difficulty match
  - Position-specific drills
  - Equipment availability
  - Goal alignment

### 2. Program Generation
- AI-powered training program creation
- Progressive weekly plans
- Customized based on:
  - Training availability
  - Player goals
  - Strengths/weaknesses
  - Skill level

## API Endpoints

### Drills
- `GET /drills/` - Get all drills with filtering and pagination
- `GET /drills/recommendations/` - Get personalized drill recommendations

### Onboarding
- `POST /api/onboarding` - Create new user profile and get initial recommendations

## Data Models

### User Profile
- Skill level (Beginner/Intermediate/Competitive/Professional)
- Position
- Available equipment
- Training preferences
- Goals and timeline

### Drills
- Categories: Dribbling, Shooting, Passing, First Touch, Physical
- Difficulty levels
- Required equipment
- Position recommendations
- Skill focus areas

## Setup

1. Install dependencies:
bash
```
pip install -r requirements.txt
```
bash
```
python create_tables.py
python seed_drills.py

# Run unit tests
pytest unit_tests/drills.py -v -s
pytest unit_tests/session_generator.py -v -s
pytest unit_tests/drill_scorer.py -v -s
pytest unit_tests/drill_scorer_db.py -v -s
```

3. Run the server:
bash
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Technologies
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic