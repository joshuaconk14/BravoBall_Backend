"""
Utility script to import drills from text files containing JSON data.
Each file should contain drills for a specific category (e.g., first_touch_drills.txt, passing_drills.txt).

This script is used when restarting the database in testing environments and importing drills from the drills directory.
"""
import os
import sys

# Add the parent directory to the Python path so we can import from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import DrillCategory, Drill, DrillSkillFocus
from db import SessionLocal, engine
from config import get_logger

logger = get_logger(__name__)

def import_drills_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Read and parse drills from a text file containing JSON data.
    
    Args:
        file_path: Path to the text file containing drill JSON data
        
    Returns:
        List of parsed drill dictionaries
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            # Extract the JSON array from the text file
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON array found in file")
            
            json_content = content[start_idx:end_idx]
            drills_data = json.loads(json_content)
            
            # Infer category from filename
            filename = os.path.basename(file_path)
            category = filename.replace('_drills.txt', '').replace('_', ' ')
            
            # Validate all drills in file match the category
            for drill in drills_data:
                if "primary_skill" not in drill:
                    drill["primary_skill"] = {"category": category}
                elif drill["primary_skill"].get("category") != category:
                    logger.warning(f"Warning: Drill '{drill['title']}' has category '{drill['primary_skill']['category']}' but is in {filename}")
            
            return drills_data
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def upload_drills_to_db(drills_data: List[Dict[str, Any]], db: Session):
    """
    Upload parsed drills to the database, updating existing drills if they already exist.
    
    Args:
        drills_data: List of drill dictionaries
        db: Database session
    """
    try:
        drills_added = 0
        drills_updated = 0
        drills_skipped = 0
        
        for drill_data in drills_data:
            # Get or create category
            primary_skill = drill_data.get("primary_skill", {})
            category_name = primary_skill.get("category")
            
            if not category_name:
                logger.warning(f"Skipping drill '{drill_data.get('title')}': No category found")
                drills_skipped += 1
                continue
                
            category = db.query(DrillCategory).filter_by(name=category_name).first()
            if not category:
                category = DrillCategory(
                    name=category_name,
                    description=f"Drills focusing on {category_name} skills"
                )
                db.add(category)
                db.flush()
                logger.info(f"Created new category: {category_name}")

            # Check if drill already exists
            existing_drill = db.query(Drill).filter_by(title=drill_data["title"]).first()
            
            if existing_drill:
                # Update existing drill
                existing_drill.description = drill_data["description"]
                existing_drill.duration = drill_data["duration"]
                existing_drill.intensity = drill_data["intensity"]
                existing_drill.training_styles = drill_data["training_styles"]
                existing_drill.type = drill_data["type"]
                existing_drill.sets = drill_data.get("sets")
                existing_drill.reps = drill_data.get("reps")
                existing_drill.rest = drill_data.get("rest")
                existing_drill.equipment = drill_data["equipment"]
                existing_drill.suitable_locations = drill_data["suitable_locations"]
                existing_drill.difficulty = drill_data["difficulty"]
                existing_drill.instructions = drill_data["instructions"]
                existing_drill.tips = drill_data["tips"]
                existing_drill.common_mistakes = drill_data.get("common_mistakes", [])
                existing_drill.progression_steps = drill_data.get("progression_steps", [])
                existing_drill.variations = drill_data.get("variations", [])
                existing_drill.video_url = drill_data.get("video_url")
                existing_drill.thumbnail_url = drill_data.get("thumbnail_url")
                
                # Update category if needed
                if existing_drill.category_id != category.id:
                    existing_drill.category_id = category.id
                
                # Delete existing skill focus entries
                db.query(DrillSkillFocus).filter_by(drill_id=existing_drill.id).delete()
                
                # Add primary skill focus
                primary_skill_focus = DrillSkillFocus(
                    drill_id=existing_drill.id,
                    category=primary_skill["category"],
                    sub_skill=primary_skill["sub_skill"],
                    is_primary=True
                )
                db.add(primary_skill_focus)
                
                # Add secondary skills
                for skill in drill_data.get("secondary_skills", []):
                    if isinstance(skill["sub_skill"], list):
                        # Handle multiple sub-skills
                        for sub_skill in skill["sub_skill"]:
                            secondary_skill_focus = DrillSkillFocus(
                                drill_id=existing_drill.id,
                                category=skill["category"],
                                sub_skill=sub_skill,
                                is_primary=False
                            )
                            db.add(secondary_skill_focus)
                    else:
                        # Handle single sub-skill
                        secondary_skill_focus = DrillSkillFocus(
                            drill_id=existing_drill.id,
                            category=skill["category"],
                            sub_skill=skill["sub_skill"],
                            is_primary=False
                        )
                        db.add(secondary_skill_focus)
                
                logger.info(f"Updated existing drill: '{drill_data['title']}'")
                drills_updated += 1
            else:
                # Create new drill
                drill = Drill(
                    uuid=str(uuid.uuid4()),  # Generate UUID for new drill
                    category_id=category.id,
                    title=drill_data["title"],
                    description=drill_data["description"],
                    duration=drill_data["duration"],
                    intensity=drill_data["intensity"],
                    training_styles=drill_data["training_styles"],
                    type=drill_data["type"],
                    sets=drill_data.get("sets"),
                    reps=drill_data.get("reps"),
                    rest=drill_data.get("rest"),
                    equipment=drill_data["equipment"],
                    suitable_locations=drill_data["suitable_locations"],
                    difficulty=drill_data["difficulty"],
                    instructions=drill_data["instructions"],
                    tips=drill_data["tips"],
                    common_mistakes=drill_data.get("common_mistakes", []),
                    progression_steps=drill_data.get("progression_steps", []),
                    variations=drill_data.get("variations", []),
                    video_url=drill_data.get("video_url"),
                    thumbnail_url=drill_data.get("thumbnail_url")
                )
                db.add(drill)
                db.flush()
                logger.info(f"Added new drill: '{drill_data['title']}'")
                drills_added += 1

                # Add primary skill focus
                primary_skill_focus = DrillSkillFocus(
                    drill_id=drill.id,
                    category=primary_skill["category"],
                    sub_skill=primary_skill["sub_skill"],
                    is_primary=True
                )
                db.add(primary_skill_focus)

                # Add secondary skills
                for skill in drill_data.get("secondary_skills", []):
                    if isinstance(skill["sub_skill"], list):
                        # Handle multiple sub-skills
                        for sub_skill in skill["sub_skill"]:
                            secondary_skill_focus = DrillSkillFocus(
                                drill_id=drill.id,
                                category=skill["category"],
                                sub_skill=sub_skill,
                                is_primary=False
                            )
                            db.add(secondary_skill_focus)
                    else:
                        # Handle single sub-skill
                        secondary_skill_focus = DrillSkillFocus(
                            drill_id=drill.id,
                            category=skill["category"],
                            sub_skill=skill["sub_skill"],
                            is_primary=False
                        )
                        db.add(secondary_skill_focus)

        db.commit()
        logger.info(f"\nImport Summary:")
        logger.info(f"- Drills added: {drills_added}")
        logger.info(f"- Drills updated: {drills_updated}")
        logger.info(f"- Drills skipped: {drills_skipped}")
        logger.info(f"- Total drills processed: {drills_added + drills_updated + drills_skipped}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading drills to database: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Main function to import drills from a file and upload to database."""
    
    # Ensure a file for drills to process is provided
    if len(sys.argv) < 2:
        logger.error("Usage: python drill_importer.py <drills_file_path> [additional_files...]")
        sys.exit(1)
        
    db = SessionLocal()
    try:
        total_added = 0
        total_skipped = 0
        
        # Process each file provided
        for file_path in sys.argv[1:]:
            logger.info(f"\nProcessing {file_path}...")
            drills_data = import_drills_from_file(file_path)
            if not drills_data:
                logger.info("No drills found to import")
                continue
                
            logger.info(f"Found {len(drills_data)} drills to import")
            
            # Upload to database
            upload_drills_to_db(drills_data, db)
            
    finally:
        db.close()
        logger.info(f"\nOverall Import Summary:")
        logger.info(f"- Total files processed: {len(sys.argv[1:])}")

if __name__ == "__main__":
    main() 