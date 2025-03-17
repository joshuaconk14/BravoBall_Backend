import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal
from models import Drill

def check_drill_difficulty(title):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter_by(title=title).first()
        if drill:
            print(f"Drill: {drill.title}")
            print(f"Difficulty: {drill.difficulty}")
            print(f"Suitable locations: {drill.suitable_locations}")
        else:
            print(f"Drill with title '{title}' not found")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_drill_difficulty(sys.argv[1])
    else:
        print("Please provide a drill title to check") 