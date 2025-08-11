"""
A modular drill management system for handling drill data operations.

This script is used to update drill fields in the database from the drills directory.
"""
# System imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Standard library imports
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models import Drill, DrillCategory, DrillSkillFocus

# Database import
from db import SessionLocal

from ..config import get_logger

logger = get_logger(__name__)

@dataclass
class DrillUpdate:
    """Represents a drill update operation"""
    drill_uuid: Optional[str] = None  # Changed from drill_id to drill_uuid
    title: Optional[str] = None
    fields_to_update: Dict[str, Any] = None

class DrillRepository:
    """Handles database operations for drills"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_drill_by_title(self, title: str) -> Optional[Drill]:
        """Get a drill by its title"""
        return self.db.query(Drill).filter(Drill.title == title).first()
    
    def get_drill_by_id(self, drill_id: int) -> Optional[Drill]:
        """Get a drill by its ID (for backward compatibility)"""
        return self.db.query(Drill).filter(Drill.id == drill_id).first()
    
    def get_drill_by_uuid(self, drill_uuid: str) -> Optional[Drill]:
        """Get a drill by its UUID"""
        return self.db.query(Drill).filter(Drill.uuid == drill_uuid).first()
    
    def update_drill(self, drill: Drill, update_data: Dict[str, Any]) -> Drill:
        """Update specific fields of a drill"""
        for field, value in update_data.items():
            if hasattr(drill, field):
                setattr(drill, field, value)
        return drill
    
    def update_skill_focus(self, drill_uuid: str, primary_skill: Dict[str, str], 
                          secondary_skills: List[Dict[str, str]]) -> None:
        """Update skill focus for a drill using UUID"""
        # Get drill by UUID
        drill = self.get_drill_by_uuid(drill_uuid)
        if not drill:
            logger.error(f"Drill not found with UUID: {drill_uuid}")
            return
        
        # Delete existing skill focus
        self.db.query(DrillSkillFocus).filter(DrillSkillFocus.drill_uuid == drill_uuid).delete()
        
        # Add primary skill
        primary_skill_focus = DrillSkillFocus(
            drill_uuid=drill_uuid,
            category=primary_skill["category"],
            sub_skill=primary_skill["sub_skill"],
            is_primary=True
        )
        self.db.add(primary_skill_focus)
        
        # Add secondary skills
        for skill in secondary_skills:
            if isinstance(skill["sub_skill"], list):
                for sub_skill in skill["sub_skill"]:
                    secondary_skill_focus = DrillSkillFocus(
                        drill_uuid=drill_uuid,
                        category=skill["category"],
                        sub_skill=sub_skill,
                        is_primary=False
                    )
                    self.db.add(secondary_skill_focus)
            else:
                secondary_skill_focus = DrillSkillFocus(
                    drill_uuid=drill_uuid,
                    category=skill["category"],
                    sub_skill=skill["sub_skill"],
                    is_primary=False
                )
                self.db.add(secondary_skill_focus)

class DrillFileManager:
    """Handles reading and parsing drill data from files"""
    
    @staticmethod
    def read_drill_file(file_path: str) -> List[Dict[str, Any]]:
        """Read and parse drills from a text file"""
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx == -1 or end_idx == 0:
                    raise ValueError("No JSON array found in file")
                
                json_content = content[start_idx:end_idx]
                return json.loads(json_content)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return []

class DrillUpdateManager:
    """Manages drill update operations"""
    
    def __init__(self, db: Session):
        self.repository = DrillRepository(db)
        self.db = db
    
    def update_drill_from_data(self, drill_data: Dict[str, Any]) -> DrillUpdate:
        """Create an update operation from drill data"""
        existing_drill = self.repository.get_drill_by_title(drill_data["title"])
        
        if not existing_drill:
            logger.warning(f"Drill not found: {drill_data['title']}")
            return None
        
        # Determine which fields have changed
        fields_to_update = {}
        for field, new_value in drill_data.items():
            if field not in ["primary_skill", "secondary_skills"]:
                current_value = getattr(existing_drill, field, None)
                if current_value != new_value:
                    fields_to_update[field] = new_value
        
        return DrillUpdate(
            drill_uuid=existing_drill.uuid, # Changed from drill_id to drill_uuid
            title=drill_data["title"],
            fields_to_update=fields_to_update
        )
    
    def apply_update(self, update: DrillUpdate) -> None:
        """Apply an update operation to the database"""
        if not update or not update.fields_to_update:
            return
        
        drill = self.repository.get_drill_by_uuid(update.drill_uuid) # Changed from drill_id to drill_uuid
        if not drill:
            logger.warning(f"Drill not found for update: {update.title}")
            return
        
        # Update drill fields
        self.repository.update_drill(drill, update.fields_to_update)
        
        # Update skill focus if needed
        if "primary_skill" in update.fields_to_update or "secondary_skills" in update.fields_to_update:
            self.repository.update_skill_focus(
                drill.uuid, # Changed from drill.id to drill.uuid
                update.fields_to_update.get("primary_skill", drill.primary_skill),
                update.fields_to_update.get("secondary_skills", drill.secondary_skills)
            )
        
        self.db.commit()
        logger.info(f"Updated drill: {update.title}")

def update_drills_from_file(file_path: str, db: Session) -> None:
    """Update drills from a file, only updating changed fields"""
    file_manager = DrillFileManager()
    update_manager = DrillUpdateManager(db)
    
    # Read drills from file
    drills_data = file_manager.read_drill_file(file_path)
    if not drills_data:
        logger.warning(f"No drills found in file: {file_path}")
        return
    
    # Process each drill
    for drill_data in drills_data:
        update = update_manager.update_drill_from_data(drill_data)
        if update:
            update_manager.apply_update(update)

def main():
    """Main function to update drills from files"""
    
    if len(sys.argv) < 2:
        sys.exit(1)
    
    db = SessionLocal()
    try:
        for file_path in sys.argv[1:]:
            update_drills_from_file(file_path, db)
    finally:
        db.close()

if __name__ == "__main__":
    main() 