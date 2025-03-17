# BravoBall - Personalized Soccer Training App

BravoBall is an intelligent soccer training app that generates personalized training sessions based on player profiles, equipment availability, and skill development goals.

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
  - Driven shots
  - Ball striking
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
  - Completed Sessions
  - Drill Groups

### API Endpoints
- `/api/onboarding`: Register and onboard new users
- `/api/login`: User authentication
- `/api/sessions/generate`: Generate personalized training sessions
- `/api/drills`: Query and filter available drills
- `/api/drill-groups`: Manage user-created drill collections
- `/api/preferences`: Manage user preferences
- `/api/sessions/completed`: Record completed training sessions

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

3. **User Management**
   - Authentication and authorization
   - User profile management
   - Training history tracking
   - Custom drill collections

## Setup and Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd bravoball
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

5. Import drill data:
```bash
# Import all drills
./scripts/manage_drills.sh --all

# Or update a specific drill category if changes to some drills were made
./scripts/manage_drills.sh --category dribbling
```

## Development

### Data Management

#### Drill Management Script
The project includes a drill management script for importing and updating drills:

```bash
# Import all drill categories
./scripts/manage_drills.sh --all

# Update drills for a specific category
./scripts/manage_drills.sh --category dribbling

# Display help
./scripts/manage_drills.sh --help
```

### Running Tests
```bash
pytest unit_tests/session_generator.py -v -s
```

### Starting the Server
```bash
python main.py
```

### Deployment
The project uses a Git-based deployment workflow:
```bash
./scripts/deploy.sh
```

## Project Structure
```
bravoball/
├── main.py                # FastAPI application entry point
├── db.py                  # Database connection and session management
├── models.py              # SQLAlchemy and Pydantic models
├── routers/               # API route handlers
├── services/              # Business logic services
├── drills/                # Drill data and import scripts
├── scripts/               # Utility scripts for development and deployment
│   ├── deploy.sh          # Git-based deployment script
│   └── manage_drills.sh   # Drill import and management script
├── unit_tests/            # Test suite
└── SCHEMA_GUIDE.md        # API schema documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
