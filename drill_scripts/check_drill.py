import sys
import os
from config import get_logger

logger = get_logger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal
from models import Drill

def check_drill_difficulty(title):
    db = SessionLocal()
    try:
        drill = db.query(Drill).filter_by(title=title).first()
        if drill:
            logger.info(f"Drill: {drill.title}")
            logger.info(f"Difficulty: {drill.difficulty}")
            logger.info(f"Suitable locations: {drill.suitable_locations}")
        else:
            logger.warning(f"Drill with title '{title}' not found")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_drill_difficulty(sys.argv[1])
    else:
        logger.info("Please provide a drill title to check") 