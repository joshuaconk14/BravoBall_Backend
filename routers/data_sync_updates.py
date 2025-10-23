from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, timedelta
from models import User, CompletedSession, DrillGroup, OrderedSessionDrill, Drill, ProgressHistory, TrainingSession, CustomDrill, UserStoreItems
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
from routers.drill_groups import find_drill_by_uuid

router = APIRouter()

def calculate_enhanced_progress_metrics(completed_sessions: List[CompletedSession], user_position: str = None) -> dict:
    """
    Calculate enhanced progress metrics based on completed sessions.
    Now supports both drill training and mental training sessions.
    
    Args:
        completed_sessions: List of completed sessions for the user (both drill and mental training)
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
            'defending_drills_completed': 0,
            'goalkeeping_drills_completed': 0,
            'fitness_drills_completed': 0,  # ✅ NEW: Add fitness drills completed
            'most_improved_skill': '',
            'unique_drills_completed': 0,
            'beginner_drills_completed': 0,
            'intermediate_drills_completed': 0,
            'advanced_drills_completed': 0,
            # ✅ NEW: Mental training metrics
            'mental_training_sessions': 0,
            'total_mental_training_minutes': 0
        }
    
    # Initialize counters
    drill_counts = Counter()  # Track drill frequency
    unique_drills = set()  # Track unique drills completed
    total_drills = 0
    total_time = 0
    
    # ✅ NEW: Mental training counters
    mental_training_sessions = 0
    total_mental_training_minutes = 0
    
    # Skill-specific counters
    skill_counters = {
        'dribbling': 0,
        'first_touch': 0,
        'passing': 0,
        'shooting': 0,
        'defending': 0,
        'goalkeeping': 0,  # ✅ NEW: Add goalkeeping counter
        'fitness': 0,  # ✅ NEW: Add fitness counter
        'mental_training': 0  # ✅ NEW: Add mental training counter
    }
    
    # Difficulty counters
    difficulty_counters = {
        'beginner': 0,
        'intermediate': 0,
        'advanced': 0
    }
    
    # Process each completed session
    for session in completed_sessions:
        # Handle drill training sessions (existing logic)
        if not session.drills:
            continue
            
        session_drill_count = len(session.drills)
        total_drills += session_drill_count
        
        # Calculate estimated session time (if not provided)
        estimated_session_time = 0
        session_has_mental_training = False
        
        for drill_data in session.drills:
            drill_info = drill_data.get('drill', {})
            drill_title = drill_info.get('title', 'Unknown')
            drill_skill = drill_info.get('skill', '').lower()
            drill_difficulty = drill_info.get('difficulty', '').lower()
            
            # Count drill occurrences for favorite drill calculation
            drill_counts[drill_title] += 1
            unique_drills.add(drill_title)
            
            # Count by skill
            if drill_skill in skill_counters:
                skill_counters[drill_skill] += 1
            
            # Count by difficulty
            if drill_difficulty in difficulty_counters:
                difficulty_counters[drill_difficulty] += 1
            
            # ✅ NEW: Handle mental training drills specifically
            if session.session_type == 'mental_training':
                session_has_mental_training = True
                # Use the drill's totalDuration for mental training time
                drill_duration = drill_data.get('totalDuration')
                if drill_duration:
                    total_mental_training_minutes += drill_duration
                    estimated_session_time += drill_duration
            else:
                # Estimate time for non-mental training drills
                drill_duration = drill_data.get('totalDuration')
                if drill_duration:
                    estimated_session_time += drill_duration
        
        # ✅ NEW: Count mental training sessions
        if session_has_mental_training:
            mental_training_sessions += 1
        
        total_time += estimated_session_time
    
    # Calculate metrics
    drill_sessions_count = len(completed_sessions)  # All sessions are drill sessions now
    total_sessions_count = len(completed_sessions)
    
    # Favorite drill (most frequent drill)
    favorite_drill = drill_counts.most_common(1)[0][0] if drill_counts else ''
    
    # Average drills per session (only counting drill sessions)
    drills_per_session = total_drills / drill_sessions_count if drill_sessions_count > 0 else 0.0
    
    # Average minutes per session (including mental training)
    minutes_per_session = total_time / total_sessions_count if total_sessions_count > 0 else 0.0
    
    # Most improved skill (skill with most drills completed)
    most_improved_skill = max(skill_counters, key=skill_counters.get) if any(skill_counters.values()) else ''
    
    return {
        'favorite_drill': favorite_drill,
        'drills_per_session': round(drills_per_session, 1),
        'minutes_per_session': round(minutes_per_session, 1),
        'total_time_all_sessions': total_time,
        'dribbling_drills_completed': skill_counters['dribbling'],
        'first_touch_drills_completed': skill_counters['first_touch'],
        'passing_drills_completed': skill_counters['passing'],
        'shooting_drills_completed': skill_counters['shooting'],
        'defending_drills_completed': skill_counters['defending'],
        'goalkeeping_drills_completed': skill_counters['goalkeeping'],
        'fitness_drills_completed': skill_counters['fitness'],  # ✅ NEW: Add fitness drills completed
        'mental_training_drills_completed': skill_counters['mental_training'],  # ✅ NEW: Add mental training drills completed
        'most_improved_skill': most_improved_skill,
        'unique_drills_completed': len(unique_drills),
        'beginner_drills_completed': difficulty_counters['beginner'],
        'intermediate_drills_completed': difficulty_counters['intermediate'],
        'advanced_drills_completed': difficulty_counters['advanced'],
        # ✅ NEW: Mental training metrics
        'mental_training_sessions': mental_training_sessions,
        'total_mental_training_minutes': total_mental_training_minutes
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
        ).order_by(OrderedSessionDrill.position).all()

        # Include the associated drill data for each ordered drill
        result = []
        for ordered_drill in ordered_drills:
            # ✅ UPDATED: Use find_drill_by_uuid to get drill from either table
            drill = None
            if ordered_drill.drill_uuid:
                drill, is_custom = find_drill_by_uuid(db, str(ordered_drill.drill_uuid), current_user.id)
            
            if drill:
                # ✅ UPDATED: Handle skill focus differently for Drill vs CustomDrill
                if is_custom:
                    # CustomDrill uses primary_skill JSON field
                    primary_skill_data = drill.primary_skill or {}
                    main_skill = primary_skill_data.get('category', 'general')
                    sub_skills = [primary_skill_data.get('sub_skill', '')] if primary_skill_data.get('sub_skill') else []
                else:
                    # Regular Drill uses skill_focus relationship
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
                        "trainingStyle": drill.training_styles[0] if drill.training_styles else None,
                        "difficulty": drill.difficulty,
                        "videoUrl": drill.video_url,
                        "is_custom": is_custom  # ✅ Use the is_custom flag from find_drill_by_uuid
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
            drill.drill_uuid: drill
            for drill in db.query(OrderedSessionDrill).filter(
                OrderedSessionDrill.session_id == session_id
            ).all()
        }
        processed_drill_uuids = set()
        
        # Add or update ordered drills
        for position, drill_data in enumerate(ordered_drills.ordered_drills):
            # ✅ UPDATED: Use is_custom field for efficient drill lookup
            drill = None
            if drill_data.drill.uuid:
                drill, _ = find_drill_by_uuid(db, drill_data.drill.uuid, current_user.id, drill_data.drill.is_custom)

            if not drill:
                raise HTTPException(status_code=404, detail=f"Drill not found with uuid {drill_data.drill.uuid}")
            
            drill_uuid = drill.uuid if drill else None
            processed_drill_uuids.add(drill_uuid)
            
            if drill_uuid in existing_drills:
                # Update existing drill
                existing_drill = existing_drills[drill_uuid]
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
                    drill_uuid=drill_uuid,
                    position=position,
                    sets_done = drill_data.sets_done,
                    sets=drill_data.sets,
                    reps=drill_data.reps,
                    duration=drill_data.duration,
                    is_completed=drill_data.is_completed
                )
                db.add(ordered_drill)
        
        # Delete drills that were removed
        for drill_uuid, drill in existing_drills.items():
            if drill_uuid not in processed_drill_uuids:
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
            CompletedSession.total_completed_drills == session.total_completed_drills,
            CompletedSession.session_type == session.session_type
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
            session_type=session.session_type,
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
            } for drill in session.drills] if session.drills else None,
            duration_minutes=session.duration_minutes
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # ✅ NEW: Update streak in progress history when session is completed
        progress_history = db.query(ProgressHistory).filter(
            ProgressHistory.user_id == current_user.id
        ).first()
        
        session_date_only = session_date.date()
        
        # Get the previous session (before this one)
        previous_session = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id,
            CompletedSession.id != db_session.id
        ).order_by(CompletedSession.date.desc()).first()
        
        if progress_history:
            if previous_session:
                prev_date = previous_session.date.date() if hasattr(previous_session.date, 'date') else previous_session.date
                days_diff = (session_date_only - prev_date).days
                
                if days_diff == 0:
                    # Same day - no streak change
                    pass
                elif days_diff == 1:
                    # Consecutive day - increment streak
                    progress_history.current_streak += 1
                    progress_history.highest_streak = max(
                        progress_history.highest_streak,
                        progress_history.current_streak
                    )
                elif days_diff == 2:
                    # Gap of 1 day - check if it was frozen
                    yesterday = session_date_only - timedelta(days=1)
                    
                    # Get user's store items to check for active freeze
                    store_items = db.query(UserStoreItems).filter(
                        UserStoreItems.user_id == current_user.id
                    ).first()
                    
                    if store_items and store_items.active_freeze_date == yesterday:
                        # Freeze protected the gap - continue streak
                        progress_history.current_streak += 1
                        progress_history.highest_streak = max(
                            progress_history.highest_streak,
                            progress_history.current_streak
                        )
                    else:
                        # Gap not protected - reset streak
                        progress_history.previous_streak = progress_history.current_streak
                        progress_history.current_streak = 1
                else:
                    # Larger gap - streak broken, start new
                    progress_history.previous_streak = progress_history.current_streak
                    progress_history.current_streak = 1
            else:
                # First session ever - start streak at 1
                progress_history.current_streak = 1
                progress_history.highest_streak = max(
                    progress_history.highest_streak,
                    progress_history.current_streak
                )
            
            db.commit()
        
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

        # Use stored streak values (don't recalculate from scratch)
        # This preserves manual changes like streak revivers
        today = datetime.now().date()
        
        # Get the most recent session to check if streak should expire
        last_session = db.query(CompletedSession).filter(
            CompletedSession.user_id == current_user.id
        ).order_by(CompletedSession.date.desc()).first()
        
        last_session_date = last_session.date.date() if last_session and hasattr(last_session.date, 'date') else (last_session.date if last_session else None)

        if not progress_history:
            # Create default progress history if none exists
            # For a new user, calculate initial streak from sessions
            initial_streak = 0
            if last_session_date:
                days_since_last = (today - last_session_date).days
                if days_since_last <= 1:
                    # User has trained recently, set initial streak to 1
                    initial_streak = 1
            
            progress_history = ProgressHistory(
                user_id=current_user.id,
                current_streak=initial_streak,
                previous_streak=0,
                highest_streak=initial_streak,
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
                defending_drills_completed=enhanced_metrics['defending_drills_completed'],
                goalkeeping_drills_completed=enhanced_metrics['goalkeeping_drills_completed'],
                fitness_drills_completed=enhanced_metrics['fitness_drills_completed'],
                most_improved_skill=enhanced_metrics['most_improved_skill'],
                unique_drills_completed=enhanced_metrics['unique_drills_completed'],
                beginner_drills_completed=enhanced_metrics['beginner_drills_completed'],
                intermediate_drills_completed=enhanced_metrics['intermediate_drills_completed'],
                advanced_drills_completed=enhanced_metrics['advanced_drills_completed'],
                # ✅ NEW: Mental training metrics
                mental_training_sessions=enhanced_metrics['mental_training_sessions'],
                total_mental_training_minutes=enhanced_metrics['total_mental_training_minutes']
            )
            db.add(progress_history)
            db.commit()
            db.refresh(progress_history)
        else:
            # Get user's store items to check for active freeze
            store_items = db.query(UserStoreItems).filter(
                UserStoreItems.user_id == current_user.id
            ).first()
            
            # Check if streak should expire due to inactivity
            if progress_history.current_streak > 0 and last_session_date:
                days_since_last = (today - last_session_date).days
                
                if days_since_last > 1:
                    # More than 1 day since last session
                    # Check if yesterday was protected by a freeze
                    yesterday = today - timedelta(days=1)
                    
                    if days_since_last == 2 and store_items and store_items.active_freeze_date == yesterday:
                        # Yesterday was frozen - streak is protected
                        pass  # Keep the streak, don't clear freeze yet
                    else:
                        # Streak should expire - no freeze protection
                        progress_history.previous_streak = progress_history.current_streak
                        progress_history.current_streak = 0
            
            # Clear expired freeze dates (older than yesterday)
            if store_items and store_items.active_freeze_date:
                yesterday = today - timedelta(days=1)
                if store_items.active_freeze_date < yesterday:
                    store_items.active_freeze_date = None
            
            # Update session count and enhanced metrics (but NOT streak unless expired)
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
            progress_history.defending_drills_completed = enhanced_metrics['defending_drills_completed']
            progress_history.goalkeeping_drills_completed = enhanced_metrics['goalkeeping_drills_completed']
            progress_history.fitness_drills_completed = enhanced_metrics['fitness_drills_completed']
            progress_history.most_improved_skill = enhanced_metrics['most_improved_skill']
            progress_history.unique_drills_completed = enhanced_metrics['unique_drills_completed']
            progress_history.beginner_drills_completed = enhanced_metrics['beginner_drills_completed']
            progress_history.intermediate_drills_completed = enhanced_metrics['intermediate_drills_completed']
            progress_history.advanced_drills_completed = enhanced_metrics['advanced_drills_completed']
            # ✅ NEW: Update mental training metrics
            progress_history.mental_training_sessions = enhanced_metrics['mental_training_sessions']
            progress_history.total_mental_training_minutes = enhanced_metrics['total_mental_training_minutes']
            db.commit()
            db.refresh(progress_history)

        return progress_history

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get progress history: {str(e)}"
        )
