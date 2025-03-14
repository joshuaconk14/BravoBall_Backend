#!/usr/bin/env python3
"""
Script to update all drill files to use the simplified enum values.
This script reads all drill files, standardizes the values, and writes them back.
"""

import os
import json
import sys
from typing import Dict, Any, List

# Mapping dictionaries for converting between frontend labels and backend enum values
LOCATION_MAPPING = {
    # Frontend to backend
    "Full-Size 11v11 Field": "full_field",
    "Medium-Sized Grass/Turf Field": "small_field",
    "Indoor Court (Futsal/Basketball)": "indoor_court",
    "Backyard/Small Outdoor Space": "backyard",
    "Small Indoor Room (Living Room/Hotel)": "small_room",
    # Legacy values
    "field": "full_field",
    "practice_area": "small_field",
    "indoor_court": "indoor_court",
    "backyard": "backyard",
    "small_indoor_room": "small_room"
}

EQUIPMENT_MAPPING = {
    # Frontend to backend
    "BALL": "ball",
    "CONES": "cones",
    "WALL": "wall",
    "GOALS": "goals",
    # Legacy values
    "soccer ball": "ball",
    "ball": "ball",
    "cones": "cones",
    "cone": "cones",
    "goal": "goals",
    "wall": "wall"
}

TRAINING_STYLE_MAPPING = {
    # Frontend to backend
    "beginner": "medium_intensity",
    "intermediate": "medium_intensity",
    "advanced": "high_intensity"
}

def standardize_drill_values(drill: Dict[str, Any]) -> None:
    """
    Standardize drill values to match the enum values in models.py
    
    Args:
        drill: Drill dictionary to standardize
    """
    # Standardize equipment
    if "equipment" in drill:
        drill["equipment"] = [EQUIPMENT_MAPPING.get(eq, eq) for eq in drill["equipment"]]
    
    # Standardize locations
    if "suitable_locations" in drill:
        drill["suitable_locations"] = [LOCATION_MAPPING.get(loc, loc) for loc in drill["suitable_locations"]]
    
    # Standardize training styles
    if "training_styles" in drill:
        drill["training_styles"] = [TRAINING_STYLE_MAPPING.get(style, style) for style in drill["training_styles"]]
    
    # Standardize difficulty (already in lowercase in models.py)
    if "difficulty" in drill and isinstance(drill["difficulty"], str):
        drill["difficulty"] = drill["difficulty"].lower()
    
    # Standardize skill categories and sub-skills
    if "primary_skill" in drill and isinstance(drill["primary_skill"], dict):
        if "category" in drill["primary_skill"]:
            drill["primary_skill"]["category"] = drill["primary_skill"]["category"].lower()
        if "sub_skill" in drill["primary_skill"]:
            # Handle case where sub_skill is None
            if drill["primary_skill"]["sub_skill"] is None:
                drill["primary_skill"]["sub_skill"] = "general"
            # Handle case where sub_skill is a list
            elif isinstance(drill["primary_skill"]["sub_skill"], list):
                drill["primary_skill"]["sub_skill"] = [
                    s.replace(" ", "_").lower() if s else "general" 
                    for s in drill["primary_skill"]["sub_skill"]
                ]
            # Normal case where sub_skill is a string
            elif isinstance(drill["primary_skill"]["sub_skill"], str):
                drill["primary_skill"]["sub_skill"] = drill["primary_skill"]["sub_skill"].replace(" ", "_").lower()
    
    if "secondary_skills" in drill and isinstance(drill["secondary_skills"], list):
        for skill in drill["secondary_skills"]:
            if isinstance(skill, dict):
                if "category" in skill:
                    skill["category"] = skill["category"].lower()
                if "sub_skill" in skill:
                    # Handle case where sub_skill is None
                    if skill["sub_skill"] is None:
                        skill["sub_skill"] = "general"
                    # Handle case where sub_skill is a list
                    elif isinstance(skill["sub_skill"], list):
                        skill["sub_skill"] = [
                            s.replace(" ", "_").lower() if s else "general" 
                            for s in skill["sub_skill"]
                        ]
                    # Normal case where sub_skill is a string
                    elif isinstance(skill["sub_skill"], str):
                        skill["sub_skill"] = skill["sub_skill"].replace(" ", "_").lower()

def update_drill_file(file_path: str) -> None:
    """
    Update a drill file to use the simplified enum values.
    
    Args:
        file_path: Path to the drill file
    """
    try:
        print(f"Processing {file_path}...")
        
        # Read the file
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Extract the JSON array
        start_idx = content.find('[')
        end_idx = content.rfind(']') + 1
        if start_idx == -1 or end_idx == 0:
            print(f"No JSON array found in {file_path}")
            return
        
        json_content = content[start_idx:end_idx]
        drills_data = json.loads(json_content)
        
        # Standardize the values
        for drill in drills_data:
            standardize_drill_values(drill)
        
        # Write the updated JSON back to the file
        updated_content = content[:start_idx] + json.dumps(drills_data, indent=4) + content[end_idx:]
        with open(file_path, 'w') as file:
            file.write(updated_content)
        
        print(f"Successfully updated {file_path}")
    
    except Exception as e:
        print(f"Error updating {file_path}: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to update all drill files."""
    # Get the drill files
    drill_dir = "drills"  # Use relative path
    drill_files = [
        os.path.join(drill_dir, f) 
        for f in os.listdir(drill_dir) 
        if f.endswith("_drills.txt")
    ]
    
    if not drill_files:
        print("No drill files found")
        return
    
    print(f"Found {len(drill_files)} drill files to update")
    
    # Update each file
    for file_path in drill_files:
        update_drill_file(file_path)
    
    print("Done!")

if __name__ == "__main__":
    main()
