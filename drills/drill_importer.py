"""
Utility script to import drills from text files containing JSON data.
Each file should contain drills for a specific category (e.g., first_touch_drills.txt, passing_drills.txt).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import DrillCategory, Drill, DrillSkillFocus
from db import SessionLocal, engine

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
                    print(f"Warning: Drill '{drill['title']}' has category '{drill['primary_skill']['category']}' but is in {filename}")
            
            return drills_data
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return []

def upload_drills_to_db(drills_data: List[Dict[str, Any]], db: Session):
    """
    Upload parsed drills to the database, checking for existing drills first.
    
    Args:
        drills_data: List of drill dictionaries
        db: Database session
    """
    try:
        drills_added = 0
        drills_skipped = 0
        
        for drill_data in drills_data:
            # Check if drill already exists
            existing_drill = db.query(Drill).filter_by(title=drill_data["title"]).first()
            if existing_drill:
                print(f"Skipping drill '{drill_data['title']}': Already exists in database")
                drills_skipped += 1
                continue

            # Get or create category
            primary_skill = drill_data.get("primary_skill", {})
            category_name = primary_skill.get("category")
            
            if not category_name:
                print(f"Skipping drill '{drill_data.get('title')}': No category found")
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
                print(f"Created new category: {category_name}")

            # Create drill
            drill = Drill(
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
                difficulty=drill_data["difficulty"].lower(),
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
            print(f"Added new drill: {drill_data['title']}")
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
        print(f"\nImport Summary:")
        print(f"- Drills added: {drills_added}")
        print(f"- Drills skipped (already exist): {drills_skipped}")
        print(f"- Total drills processed: {drills_added + drills_skipped}")
        
    except Exception as e:
        db.rollback()
        print(f"Error uploading drills to database: {str(e)}")
        raise

def main():
    """Main function to import drills from a file and upload to database."""
    import sys
    
    # Ensure a file for drills to process is provided
    if len(sys.argv) < 2:
        print("Usage: python drill_importer.py <drills_file_path> [additional_files...]")
        sys.exit(1)
        
    db = SessionLocal()
    try:
        total_added = 0
        total_skipped = 0
        
        # Process each file provided
        for file_path in sys.argv[1:]:
            print(f"\nProcessing {file_path}...")
            drills_data = import_drills_from_file(file_path)
            if not drills_data:
                print("No drills found to import")
                continue
                
            print(f"Found {len(drills_data)} drills to import")
            
            # Upload to database
            upload_drills_to_db(drills_data, db)
            
    finally:
        db.close()
        print(f"\nOverall Import Summary:")
        print(f"- Total files processed: {len(sys.argv[1:])}")

if __name__ == "__main__":
    main() 