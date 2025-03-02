# Tekk - Personalized Soccer Training App

Tekk is an intelligent soccer training application that generates personalized training sessions based on player profiles, equipment availability, and skill development goals.

## Features

### 1. Personalized Training Sessions
- Adapts to player's skill level (Beginner to Advanced)
- Considers available equipment and training location
- Customizes session duration and intensity
- Focuses on targeted skill development

### 2. Smart Drill Selection
- Scores and ranks drills based on multiple factors:
  - Primary and secondary skill relevance
  - Equipment availability and adaptability
  - Location suitability
  - Player skill level vs. drill difficulty
  - Training style compatibility
  - Session duration constraints

### 3. Equipment Flexibility
- Adapts drills based on available equipment
- Supports various training environments:
  - Full-size fields
  - Small outdoor spaces
  - Indoor courts
  - Small rooms
- Equipment categories:
  - Ball
  - Cones
  - Wall
  - Goals

### 4. Skill Categories
- Passing
  - Short passing
  - Long passing
  - Wall passing
- Shooting
  - Power
  - Finishing
  - Volleys
  - Long shots
- Dribbling
  - Ball mastery
  - Close control
  - Speed dribbling
  - 1v1 moves
- First Touch
  - Ground control
  - Aerial control
  - Turning with ball
  - One-touch control
- Fitness
  - Speed
  - Agility
  - Endurance

## Technical Architecture

### Database Structure
- PostgreSQL database with SQLAlchemy ORM
- Models for:
  - Users
  - Drills
  - Training Sessions
  - Session Preferences
  - Drill Categories
  - Skill Focus Areas

### API Endpoints
- `/api/session/generate`: Generate personalized training sessions
- `/drills/`: Query and filter available drills
- `/drill-categories/`: Get all drill categories

### Core Components
1. **Session Generator**
   - Intelligent drill selection algorithm
   - Duration adjustment and normalization
   - Equipment availability validation
   - Skill relevance scoring

2. **Drill Scorer**
   - Multi-factor scoring system
   - Weighted criteria evaluation
   - Adaptable equipment handling
   - Location compatibility checking

3. **Preference Service**
   - User preference management
   - Profile-based session customization
   - Equipment and location tracking

## Setup and Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd tekk-app
```

2. Set up Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python reset_db.py
```

## Development

### Running Tests
```bash
pytest unit_tests/session_generator.py -v -s
```

### Starting the Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
