# Soccer Training App Schema Guide

This document outlines the data schema for the Soccer Training App, including models, API endpoints, and data structures.

## Core Concepts

- **Users**: Players who register and use the app
- **Drills**: Individual soccer training exercises
- **Training Sessions**: Collections of drills organized for a specific training purpose
- **Drill Groups**: User-created collections of drills (like playlists)
- **Completed Sessions**: Records of training sessions that users have completed

## Data Models

### Drill Structure

Drills are the fundamental building blocks of the app. Each drill has:

```json
{
  "id": 123,
  "title": "Still ball shot on 6 yard box",
  "description": "A focused shooting drill aimed at developing driven shots from the 6 yard box.",
  "type": "reps_based",
  "duration": null,
  "sets": 5,
  "reps": 5,
  "equipment": ["ball", "goals"],
  "suitable_locations": ["full_field", "small_field", "indoor_court"],
  "intensity": "medium",
  "training_styles": ["medium_intensity"],
  "difficulty": "beginner",
  "primary_skill": {
    "category": "shooting",
    "sub_skill": "driven_shots"
  },
  "secondary_skills": [
    {
      "category": "shooting",
      "sub_skill": "ball_striking"
    }
  ],
  "instructions": [
    "Place the ball at the center of the 6 yard line.",
    "Step back a few steps at an angle from the ball.",
    "Strike the ball down the middle of the goal using your laces.",
    "Focus on technique to ensure consistent driven shots."
  ],
  "tips": [
    "Keep your non-kicking foot beside the ball for balance.",
    "Follow through with your kicking leg for better accuracy.",
    "Experiment with slight adjustments in your angle and distance."
  ],
  "common_mistakes": [
    "Striking the ball with the wrong part of the foot.",
    "Lack of follow-through in the shot.",
    "Poor body positioning leading to inconsistent strikes."
  ],
  "progression_steps": [
    "Increase the distance from the ball for added challenge."
  ],
  "variations": [
    "Try shooting with your weaker foot."
  ],
  "video_url": "https://example.com/video.mp4",
  "thumbnail_url": "https://example.com/thumbnail.jpg"
}
```

### User Preferences

User preferences determine what kind of training sessions will be generated:

```json
{
  "selected_time": "30",
  "selected_equipment": ["ball", "cones"],
  "selected_training_style": "medium_intensity",
  "selected_location": "small_field",
  "selected_difficulty": "intermediate",
  "current_streak": 5,
  "highest_streak": 10,
  "completed_sessions_count": 25
}
```

### Session Preferences

More detailed preferences for generating specific training sessions:

```json
{
  "duration": 45,
  "available_equipment": ["ball", "cones", "goals"],
  "training_style": "high_intensity",
  "training_location": "full_field",
  "difficulty": "advanced",
  "target_skills": [
    {
      "category": "shooting",
      "sub_skills": ["driven_shots", "finishing"]
    },
    {
      "category": "dribbling",
      "sub_skills": ["close_control"]
    }
  ]
}
```

### Training Session

A complete training session with multiple drills:

```json
{
  "session_id": 456,
  "total_duration": 45,
  "focus_areas": ["shooting", "dribbling"],
  "drills": [
    {
      "id": 123,
      "title": "Still ball shot on 6 yard box",
      "description": "A focused shooting drill...",
      "type": "reps_based",
      "duration": null,
      "sets": 5,
      "reps": 5,
      "equipment": ["ball", "goals"],
      "suitable_locations": ["full_field", "small_field", "indoor_court"],
      "intensity": "medium",
      "training_styles": ["medium_intensity"],
      "difficulty": "beginner",
      "primary_skill": {
        "category": "shooting",
        "sub_skill": "driven_shots"
      },
      "secondary_skills": [
        {
          "category": "shooting",
          "sub_skill": "ball_striking"
        }
      ],
      "instructions": ["Place the ball...", "..."],
      "tips": ["Keep your non-kicking foot...", "..."],
      "common_mistakes": ["Striking the ball...", "..."],
      "progression_steps": ["Increase the distance...", "..."],
      "variations": ["Try shooting with...", "..."],
      "video_url": "https://example.com/video.mp4",
      "thumbnail_url": "https://example.com/thumbnail.jpg"
    },
    // Additional drills...
  ]
}
```

### Completed Session

Record of a completed training session:

```json
{
  "id": 789,
  "date": "2023-03-15T14:30:00Z",
  "total_completed_drills": 5,
  "total_drills": 6,
  "drills": [
    // Array of DrillResponse objects
  ]
}
```

### Drill Group

User-created collection of drills:

```json
{
  "id": 101,
  "name": "My Favorite Shooting Drills",
  "description": "Collection of shooting drills I like to practice",
  "drills": [
    // Array of DrillResponse objects
  ],
  "is_liked_group": false
}
```

## API Endpoints

### Drills

- `GET /api/drills` - List all drills (with pagination)
- `GET /api/drills/{id}` - Get a specific drill
- `GET /api/drills/search` - Search drills by criteria
- `POST /api/drills` - Create a new drill (admin only)
- `PUT /api/drills/{id}` - Update a drill (admin only)
- `DELETE /api/drills/{id}` - Delete a drill (admin only)

### Training Sessions

- `POST /api/sessions/generate` - Generate a new training session based on preferences
- `GET /api/sessions/{id}` - Get a specific training session
- `POST /api/sessions/completed` - Record a completed session

### User Preferences

- `GET /api/preferences` - Get current user preferences
- `PUT /api/preferences` - Update user preferences

### Drill Groups

- `GET /api/drill-groups` - List user's drill groups
- `POST /api/drill-groups` - Create a new drill group
- `GET /api/drill-groups/{id}` - Get a specific drill group
- `PUT /api/drill-groups/{id}` - Update a drill group
- `DELETE /api/drill-groups/{id}` - Delete a drill group
- `POST /api/drill-groups/{id}/drills` - Add a drill to a group
- `DELETE /api/drill-groups/{id}/drills/{drill_id}` - Remove a drill from a group

### User

- `POST /api/onboarding` - Register and onboard a new user
- `POST /api/login` - Log in a user
- `GET /api/user` - Get current user info
- `GET /api/user/completed-sessions` - Get user's completed sessions history

## Enums

### Skill Categories

- `passing`
- `shooting`
- `dribbling`
- `first_touch`
- `fitness`

### Drill Types

- `time_based` - Perform for a specific duration
- `reps_based` - Perform a specific number of repetitions
- `set_based` - Perform sets of repetitions
- `continuous` - Perform continuously until completion

### Difficulty Levels

- `beginner`
- `intermediate`
- `advanced`

### Training Styles

- `medium_intensity`
- `high_intensity`
- `game_prep`
- `game_recovery`
- `rest_day`

### Training Locations

- `full_field`
- `small_field`
- `indoor_court`
- `backyard`
- `small_room`

### Equipment

- `ball`
- `cones`
- `wall`
- `goals`

## Data Flow Examples

### Generating a Training Session

1. User sets their preferences (SessionPreferencesRequest)
2. Backend selects appropriate drills based on preferences
3. Backend returns a complete SessionResponse with drills

### Completing a Training Session

1. User completes drills in a session
2. Frontend sends CompletedSessionRequest with completion data
3. Backend stores the completed session and updates user stats
4. Backend returns CompletedSessionResponse with the stored data

### Creating a Drill Group

1. User selects drills they want to save
2. Frontend sends DrillGroupRequest with selected drills
3. Backend creates the group and returns DrillGroupResponse 