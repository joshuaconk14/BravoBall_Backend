from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, timedelta
from models import User, CompletedSession, DrillGroup, OrderedSessionDrill, Drill, ProgressHistory, TrainingSession
from schemas import (
    CompletedSession as CompletedSessionSchema,
    CompletedSessionCreate,
    DrillGroup as DrillGroupSchema,
    DrillGroupCreate,
    DrillGroupUpdate,
    OrderedSessionDrillUpdate,
    ProgressHistoryUpdate,
    ProgressHistoryResponse
)
from db import get_db
from auth import get_current_user
from collections import Counter

router = APIRouter()

def calculate_enhanced_progress_metrics(completed_sessions: List[CompletedSession], user_position: str = None) -> dict:
    """
    Calculate enhanced progress metrics based on completed sessions.
    
    Args:
        completed_sessions: List of completed sessions for the user
        user_position: User's position (optional, for position-specific metrics)
    
    Returns:
        Dictionary containing all calculated metrics
    """
    if not completed_sessions:
        return {
            'favorite_drill': '',
            'drills_per_session': 0.0,
            'minutes_per_session': 0.0,
            'total_time_all_sessions': 0,
            'dribbling_drills_completed': 0,
            'first_touch_drills_completed': 0,
            'passing_drills_completed': 0,
            'shooting_drills_completed': 0,
            'most_improved_skill': '',
            'unique_drills_completed': 0,
            'beginner_drills_completed': 0,
            'intermediate_drills_completed': 0,
            'advanced_drills_completed': 0
        }
    
    # Initialize counters
    drill_counts = Counter()  # Track drill frequency
    unique_drills = set()  # Track unique drills completed
    total_drills = 0
    total_time = 0
    skill_counts = {
        'dribbling': 0,
        'first_touch': 0,
        'passing': 0,
        'shooting': 0
    }
    difficulty_counts = {
        'beginner': 0,
        'intermediate': 0,
        'advanced': 0
    }
    skill_improvement_tracker = {
        'dribbling': 0,
        'first_touch': 0,
        'passing': 0,
        'shooting': 0
    }
    
    
    # Process each completed session
    for session in completed_sessions:
        if not session.drills:
            continue
            
        session_drills = 0
        session_time = 0
        
        for drill_data in session.drills:
            if isinstance(drill_data, dict):
                drill = drill_data.get('drill', {})
                sets_done = drill_data.get('setsDone', 0)
                total_duration = drill_data.get('totalDuration', 0)
                
                # Count drill frequency (for favorite drill)
                drill_title = drill.get('title', '')
                if drill_title:
                    drill_counts[drill_title] += 1
                
                # Count completed drills
                if sets_done > 0:
                    session_drills += 1
                    total_drills += 1
                    session_time += total_duration
                    
                    # Track unique drills
                    drill_uuid = drill.get('uuid', '')
                    if drill_uuid:
                        unique_drills.add(drill_uuid)
                    
                    # Count by skill category
                    skill = drill.get('skill', '')
                    skill_normalized = skill.lower().replace(' ', '_')
                    if skill_normalized in skill_counts:
                        skill_counts[skill_normalized] += 1
                        skill_improvement_tracker[skill_normalized] += 1
                    
                    # Count by difficulty
                    difficulty = drill.get('difficulty', '').lower()
                    if difficulty in difficulty_counts:
                        difficulty_counts[difficulty] += 1
    
        total_time += session_time
    
    # Calculate metrics
    num_sessions = len(completed_sessions)
    
    # Favorite drill (most frequently completed)
    favorite_drill = drill_counts.most_common(1)[0][0] if drill_counts else ''
    
    # Drills per session (average)
    drills_per_session = round(total_drills / num_sessions, 2) if num_sessions > 0 else 0.0
    
    # Minutes per session (average)
    minutes_per_session = round(total_time / num_sessions, 2) if num_sessions > 0 else 0.0
    
    # Total time across all sessions
    total_time_all_sessions = total_time
    
    # Most improved skill (skill with highest count)
    most_improved_skill = max(skill_improvement_tracker.items(), key=lambda x: x[1])[0] if skill_improvement_tracker else ''
    
    # Unique drills completed
    unique_drills_completed = len(unique_drills)
    
    return {
        'favorite_drill': favorite_drill,
        'drills_per_session': drills_per_session,
        'minutes_per_session': minutes_per_session,
        'total_time_all_sessions': total_time_all_sessions,
        'dribbling_drills_completed': skill_counts['dribbling'],
        'first_touch_drills_completed': skill_counts['first_touch'],
        'passing_drills_completed': skill_counts['passing'],
        'shooting_drills_completed': skill_counts['shooting'],
        'most_improved_skill': most_improved_skill,
        'unique_drills_completed': unique_drills_completed,
        'beginner_drills_completed': difficulty_counts['beginner'],
        'intermediate_drills_completed': difficulty_counts['intermediate'],
        'advanced_drills_completed': difficulty_counts['advanced']
    }

# ordered drills endpoint
@router.get("/api/sessions/ordered_drills/")
async def get_ordered_session_drills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's current ordered drills and their progress.
    """
    try:
        # Join OrderedSessionDrill with TrainingSession to filter by user
        ordered_drills = db.query(OrderedSessionDrill).join(OrderedSessionDrill.session).filter(
            TrainingSession.user_id == current_user.id
        ).options(joinedload(OrderedSessionDrill.drill)).order_by(OrderedSessionDrill.position).all()

        # Include the associated drill data for each ordered drill
        result = []
        for ordered_drill in ordered_drills:
            drill = ordered_drill.drill
            if drill:
                # Get skill focus data
                skill_focus = drill.skill_focus
                primary_skill = next((sf for sf in skill_focus if sf.is_primary), None) if skill_focus else None
                secondary_skills = [sf for sf in skill_focus if not sf.is_primary] if skill_focus else []
                
                # Collect all sub-skills (primary + secondary)
                sub_skills = []
                if primary_skill:
                    sub_skills.append(primary_skill.sub_skill)
                sub_skills.extend([skill.sub_skill for skill in secondary_skills])
                
                # Get the main skill category (from primary skill)
                main_skill = primary_skill.category if primary_skill else "general"
                
                result.append({
                    "drill": {
                        "uuid": str(drill.uuid),  # Keep UUID field, remove backend_id
                        "title": drill.title,
                        "skill": main_skill,
                        "subSkills": sub_skills,
                        "sets": drill.sets,
                        "reps": drill.reps,
                        "duration": drill.duration,
                        "description": drill.description,
                        "instructions": drill.instructions,
                        "tips": drill.tips,
                        "equipment": drill.equipment,
                        "trainingStyle": drill.training_styles[0],
                        "difficulty": drill.difficulty,
                        "videoUrl": drill.video_url
                    },
                    # Add per-session fields as needed
                    "sets_done": ordered_drill.sets_done,
                    "sets": ordered_drill.sets,
                    "reps": ordered_drill.reps,
                    "duration": ordered_drill.duration,
                    "is_completed": ordered_drill.is_completed,
                    "position": ordered_drill.position # position in db
                })

        return {
            "ordered_drills": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ordered session drills: {str(e)}"
        )

@router.put("/api/sessions/ordered_drills/")
async def sync_ordered_session_drills(
    ordered_drills: OrderedSessionDrillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync the user's current drill progress. This only maintains the current state,
    not historical data. Historical data is saved to completed_sessions when a session
    is marked as complete.
    """
    try:
        # Get or create the user's training session
        user_session = db.query(TrainingSession).filter(TrainingSession.user_id == current_user.id).first()
        if not user_session:
            # Create a new training session for the user
            user_session = TrainingSession(
                user_id=current_user.id,
                total_duration=0,  # Will be calculated based on drills
                focus_areas=[]
            )
            db.add(user_session)
            db.commit()
            db.refresh(user_session)
        
        session_id = user_session.id
        
        # Get existing ordered drills for this user's session
        existing_drills = {
            drill.drill_id: drill
            for drill in db.query(OrderedSessionDrill).filter(
                OrderedSessionDrill.session_id == session_id
            ).all()
        }
        processed_drill_ids = set()
        
        # Add or update ordered drills
        for position, drill_data in enumerate(ordered_drills.ordered_drills):
            # Find drill by UUID
            drill = None
            if drill_data.drill.uuid:
                drill = db.query(Drill).filter(Drill.uuid == drill_data.drill.uuid).first()
            
            if not drill:
                raise HTTPException(status_code=404, detail=f"Drill not found with uuid {drill_data.drill.uuid}")
            
            drill_id = drill.id if drill else None
            processed_drill_ids.add(drill_id)
            
            if drill_id in existing_drills:
                # Update existing drill
                existing_drill = existing_drills[drill_id]
                existing_drill.position = position
                existing_drill.sets_done = drill_data.sets_done
                existing_drill.sets = drill_data.sets
                existing_drill.reps = drill_data.reps
                existing_drill.duration = drill_data.duration
                existing_drill.is_completed = drill_data.is_completed
            else:
                # Add new drill
                ordered_drill = OrderedSessionDrill(
                    session_id=session_id,
                    drill_id=drill_id,
                    position=position,
                    sets_done = drill_data.sets_done,
                    sets=drill_data.sets,
                    reps=drill_data.reps,
                    duration=drill_data.duration,
                    is_completed=drill_data.is_completed
                )
                db.add(ordered_drill)
        
        # Delete drills that were removed
        for drill_id, drill in existing_drills.items():
            if drill_id not in processed_drill_ids:
                db.delete(drill)
        
        db.commit()
        return {
            "message": "Current drill progress synced successfully",
            "total_drills": len(ordered_drills.ordered_drills),
            "completed_drills": sum(1 for drill in ordered_drills.ordered_drills if drill.is_completed)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync ordered session drills: {str(e)}"
        )
    

# Completed Sessions Endpoints
@router.post("/api/sessions/completed/", response_model=CompletedSessionSchema)
def create_completed_session(session: CompletedSessionCreate,
                           current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    try:
        # Parse the ISO8601 date string to datetime
        session_date = datetime.fromisoformat(session.date.replace('Z', '+00:00'))

        # Check for duplicate sessions (same user, same date, same drill count)
        existing_session = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id,
            CompletedSession.date == session_date,
            CompletedSession.total_drills == session.total_drills,
            CompletedSession.total_completed_drills == session.total_completed_drills
        ).first()
        
        if existing_session:
            # Return existing session instead of creating duplicate
            return existing_session
        
        # Create the completed session
        db_session = CompletedSession(
            user_id=current_user.id,
            date=session_date,
            total_completed_drills=session.total_completed_drills,
            total_drills=session.total_drills,
            drills=[{
                "drill": {
                    "uuid": drill.drill.uuid,  # Use UUID as primary identifier
                    "title": drill.drill.title,
                    "skill": drill.drill.skill,
                    "subSkills": drill.drill.subSkills,
                    "sets": drill.drill.sets,
                    "reps": drill.drill.reps,
                    "duration": drill.drill.duration,
                    "description": drill.drill.description,
                    "instructions": drill.drill.instructions,
                    "tips": drill.drill.tips,
                    "equipment": drill.drill.equipment,
                    "trainingStyle": drill.drill.trainingStyle,
                    "difficulty": drill.drill.difficulty,
                    "videoUrl": drill.drill.videoUrl
                },
                "setsDone": drill.setsDone,
                "totalSets": drill.totalSets,
                "totalReps": drill.totalReps,
                "totalDuration": drill.totalDuration,
                "isCompleted": drill.isCompleted
            } for drill in session.drills]
        )
        db.add(db_session)
        
        db.commit()
        db.refresh(db_session)
        return db_session
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create completed session: {str(e)}"
        )

@router.get("/api/sessions/completed/", response_model=List[CompletedSessionSchema])
def get_completed_sessions(current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    return db.query(CompletedSession).filter(CompletedSession.user_id == current_user.id).all()




# Progress History Endpoints
@router.get("/api/progress_history/", response_model=ProgressHistoryResponse)
async def get_progress_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's progress history (streaks and completed sessions count)
    """
    try:
        progress_history = db.query(ProgressHistory).filter(
            ProgressHistory.user_id == current_user.id
        ).first()

        # Fetch all completed sessions for the user, ordered by date ascending
        completed_sessions = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id
        ).order_by(CompletedSession.date.asc()).all()
        completed_sessions_count = len(completed_sessions)


        # Calculate enhanced progress metrics
        enhanced_metrics = calculate_enhanced_progress_metrics(completed_sessions, current_user.position)


        # Calculate streaks
        streak = 0
        highest_streak = 0
        previous_streak = progress_history.current_streak if progress_history else 0
        today = datetime.now().date()
        last_session_date = None

        for session in completed_sessions:
            session_date = session.date.date() if hasattr(session.date, 'date') else session.date
            if last_session_date is None:
                # First session in completed sessions loop is set to 1
                streak = 1
            else:
                days_diff = (session_date - last_session_date).days
                if days_diff == 1:
                    # Sessions have diff date, increment streak
                    streak += 1
                elif days_diff == 0:
                    # Same day, don't increment streak
                    pass
                else:
                    streak = 1
            highest_streak = max(highest_streak, streak)
            last_session_date = session_date

        # Check if the last session was today or yesterday
        streak_should_reset = True
        if last_session_date:
            if (today - last_session_date).days in [0, 1]:
                streak_should_reset = False

        if streak_should_reset:
            previous_streak = streak
            streak = 0

        if not progress_history:
            # Create default progress history if none exists
            progress_history = ProgressHistory(
                user_id=current_user.id,
                current_streak=streak,
                previous_streak=previous_streak,
                highest_streak=highest_streak,
                completed_sessions_count=completed_sessions_count,
                # ✅ NEW: Enhanced progress metrics
                favorite_drill=enhanced_metrics['favorite_drill'],
                drills_per_session=enhanced_metrics['drills_per_session'],
                minutes_per_session=enhanced_metrics['minutes_per_session'],
                total_time_all_sessions=enhanced_metrics['total_time_all_sessions'],
                dribbling_drills_completed=enhanced_metrics['dribbling_drills_completed'],
                first_touch_drills_completed=enhanced_metrics['first_touch_drills_completed'],
                passing_drills_completed=enhanced_metrics['passing_drills_completed'],
                shooting_drills_completed=enhanced_metrics['shooting_drills_completed'],
                most_improved_skill=enhanced_metrics['most_improved_skill'],
                unique_drills_completed=enhanced_metrics['unique_drills_completed'],
                beginner_drills_completed=enhanced_metrics['beginner_drills_completed'],
                intermediate_drills_completed=enhanced_metrics['intermediate_drills_completed'],
                advanced_drills_completed=enhanced_metrics['advanced_drills_completed']
            )
            db.add(progress_history)
            db.commit()
            db.refresh(progress_history)
        else:
            progress_history.previous_streak = previous_streak
            progress_history.current_streak = streak
            progress_history.highest_streak = highest_streak
            progress_history.completed_sessions_count = completed_sessions_count
            # ✅ NEW: Update enhanced progress metrics
            progress_history.favorite_drill = enhanced_metrics['favorite_drill']
            progress_history.drills_per_session = enhanced_metrics['drills_per_session']
            progress_history.minutes_per_session = enhanced_metrics['minutes_per_session']
            progress_history.total_time_all_sessions = enhanced_metrics['total_time_all_sessions']
            progress_history.dribbling_drills_completed = enhanced_metrics['dribbling_drills_completed']
            progress_history.first_touch_drills_completed = enhanced_metrics['first_touch_drills_completed']
            progress_history.passing_drills_completed = enhanced_metrics['passing_drills_completed']
            progress_history.shooting_drills_completed = enhanced_metrics['shooting_drills_completed']
            progress_history.most_improved_skill = enhanced_metrics['most_improved_skill']
            progress_history.unique_drills_completed = enhanced_metrics['unique_drills_completed']
            progress_history.beginner_drills_completed = enhanced_metrics['beginner_drills_completed']
            progress_history.intermediate_drills_completed = enhanced_metrics['intermediate_drills_completed']
            progress_history.advanced_drills_completed = enhanced_metrics['advanced_drills_completed']
            db.commit()
            db.refresh(progress_history)

        return progress_history

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get progress history: {str(e)}"
        )
