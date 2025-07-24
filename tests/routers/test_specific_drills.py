import sys
import os
import logging

logging.basicConfig(level=logging.INFO)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db import SessionLocal
from models import Drill

def update_drill_video(drill_title: str, new_video_url: str, new_thumbnail_url: str = None):
    """
    Update only the video URL and thumbnail URL of a drill.
    
    Args:
        drill_title: The exact title of the drill to update
        new_video_url: The new video URL to test
        new_thumbnail_url: Optional new thumbnail URL
    """
    db = SessionLocal()
    try:
        # Find the drill by title
        drill = db.query(Drill).filter(Drill.title == drill_title).first()
        if not drill:
            logging.error(f"Drill not found: {drill_title}")
            return
            
        # Update only the video and thumbnail URLs
        drill.video_url = new_video_url
        if new_thumbnail_url:
            drill.thumbnail_url = new_thumbnail_url
            
        db.commit()
        logging.info(f"Successfully updated video URL for drill: {drill_title}")
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating drill: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    # Example usage
    drill_title = "Toe-Taps"  # Replace with the exact title of the drill you want to test
    new_video_url = "https://bravoball-drills-h264.s3.us-east-2.amazonaws.com/dribbling-drills/toe-taps.mp4"  # Replace with your test video URL
    new_thumbnail_url = "https://example.com/your-test-thumbnail.jpg"  # Optional
    
    update_drill_video(drill_title, new_video_url, new_thumbnail_url)