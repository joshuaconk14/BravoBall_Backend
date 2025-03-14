import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from pathlib import Path
from drills.drill_importer import import_drills_from_file, upload_drills_to_db
from db import SessionLocal

def update_drills(category: str = None, reset: bool = False) -> None:
    """
    Update drills for specified category or all categories
    
    Args:
        category: Specific category to update (e.g., 'dribbling', 'passing')
        reset: Whether to reset the database before importing
    """
    drills_dir = Path("drills")
    
    if reset:
        # Optional: Add database reset logic here
        from reset_db import reset_database
        reset_database()
        print("Database reset complete")

    # Get database session
    db = SessionLocal()
    try:
        if category:
            # Update specific category
            file_path = drills_dir / f"{category}_drills.txt"
            if file_path.exists():
                print(f"\nProcessing {file_path}...")
                drills_data = import_drills_from_file(str(file_path))
                if drills_data:
                    print(f"Found {len(drills_data)} drills to import")
                    upload_drills_to_db(drills_data, db)
                else:
                    print(f"❌ No drills found in file: {file_path}")
            else:
                print(f"❌ No drill file found for category: {category}")
        else:
            # Update all categories
            for file_path in drills_dir.glob("*_drills.txt"):
                print(f"\nProcessing {file_path}...")
                drills_data = import_drills_from_file(str(file_path))
                if drills_data:
                    print(f"Found {len(drills_data)} drills to import")
                    upload_drills_to_db(drills_data, db)
                else:
                    print(f"❌ No drills found in file: {file_path}")
    finally:
        db.close()
        print("\nDrill update process completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage soccer drills database")
    parser.add_argument(
        "--category",
        help="Specific category to update (e.g., 'dribbling', 'passing'). Omit to update all.",
        required=False
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before importing"
    )
    
    args = parser.parse_args()
    update_drills(args.category, args.reset) 