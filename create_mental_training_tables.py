"""
create_mental_training_tables.py
Create mental training tables and seed with motivational quotes
"""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import models
from db import SQLALCHEMY_DATABASE_URL
from config import get_logger

logger = get_logger(__name__)

def create_mental_training_tables():
    """Create mental training tables and seed with quotes"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    
    # Create tables if they don't exist
    models.Base.metadata.create_all(bind=engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Clear existing quotes and add new motivational quotes
        existing_quotes = db.query(models.MentalTrainingQuote).count()
        if existing_quotes > 0:
            logger.info(f"Clearing {existing_quotes} existing mental training quotes...")
            db.query(models.MentalTrainingQuote).delete()
            db.commit()
            logger.info("✅ Cleared existing quotes")
        
        # Seed with motivational quotes
        quotes = [
            # Soccer Legends - Lionel Messi
            {"content": "You have to fight to reach your dream. You have to sacrifice and work hard for it.", "author": "Lionel Messi", "type": "motivational"},
            {"content": "I start early and I stay late, day after day, year after year. It took me 17 years and 114 days to become an overnight success.", "author": "Lionel Messi", "type": "motivational"},
            {"content": "You can overcome anything, if only you love something enough.", "author": "Lionel Messi", "type": "motivational"},
            {"content": "I've always really just liked football, and I've always devoted a lot of time to it.", "author": "Lionel Messi", "type": "motivational"},
            {"content": "The best decisions aren't made with your mind, but with your instincts.", "author": "Lionel Messi", "type": "motivational"},
            {"content": "Everything that's happened to me in my career has been special, even the tough times: they leave marks on you that shape your life.", "author": "Lionel Messi", "type": "motivational"},
            
            # Soccer Legends - Cristiano Ronaldo  
            {"content": "Dreams are not what you see in your sleep, dreams are things which do not let you sleep.", "author": "Cristiano Ronaldo", "type": "motivational"},
            {"content": "Your love makes me strong. Your hate makes me unstoppable.", "author": "Cristiano Ronaldo", "type": "motivational"},
            {"content": "Talent without working hard is nothing.", "author": "Cristiano Ronaldo", "type": "motivational"},
            {"content": "I've never tried to hide the fact that it is my intention to become the best.", "author": "Cristiano Ronaldo", "type": "motivational"},
            {"content": "We don't want to tell our dreams. We want to show them.", "author": "Cristiano Ronaldo", "type": "motivational"},
            {"content": "If you don't believe you are the best, then you will never achieve all that you are capable of.", "author": "Cristiano Ronaldo", "type": "motivational"},
            {"content": "Dedication, hard work all the time, and belief.", "author": "Cristiano Ronaldo", "type": "motivational"},
            
            # Soccer Legends - Pele
            {"content": "Success is no accident. It is hard work, perseverance, learning, studying, sacrifice and most of all, love of what you are doing.", "author": "Pele", "type": "motivational"},
            {"content": "Everything is practice.", "author": "Pele", "type": "motivational"},
            {"content": "Enthusiasm is everything. It must be taut and vibrating like a guitar string.", "author": "Pele", "type": "motivational"},
            {"content": "The more difficult the victory, the greater the happiness in winning.", "author": "Pele", "type": "motivational"},
            {"content": "A lot of people, when a guy scores a lot of goals, think, 'He's a great player', because a goal is very important, but a great player is a player who can do everything on the field.", "author": "Pele", "type": "motivational"},
            
            # Other Soccer Legends
            {"content": "To see the ball, to run after it, makes me the happiest man in the world.", "author": "Diego Maradona", "type": "motivational"},
            {"content": "When you win, you don't get carried away. But if you go step by step, with confidence, you can go far.", "author": "Diego Maradona", "type": "motivational"},
            {"content": "Playing football is very simple, but playing simple football is the hardest thing there is.", "author": "Johan Cruyff", "type": "motivational"},
            {"content": "Young players need freedom of expression to develop as creative players. They should be encouraged to try skills without fear of failure.", "author": "Arsene Wenger", "type": "motivational"},
            {"content": "Football is an art, like dancing. It requires whole-hearted concentration.", "author": "Arsene Wenger", "type": "motivational"},
            
            # Basketball Legends - Michael Jordan
            {"content": "I've missed more than 9000 shots in my career. I've lost almost 300 games. I've failed over and over and over again in my life. And that is why I succeed.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "Talent wins games, but teamwork and intelligence win championships.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "You must expect great things of yourself before you can do them.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "I can accept failure, everyone fails at something. But I can't accept not trying.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "If you're trying to achieve, there will be roadblocks. Figure out how to climb it, go through it, or work around it.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "Always turn a negative situation into a positive situation.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "Some people want it to happen, some wish it would happen, others make it happen.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "Obstacles don't have to stop you. If you run into a wall, don't turn around and give up.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "Never say never, because limits, like fears, are often just an illusion.", "author": "Michael Jordan", "type": "motivational"},
            
            # Tennis Legend - Serena Williams
            {"content": "I really think a champion is defined not by their wins but by how they can recover when they fall.", "author": "Serena Williams", "type": "motivational"},
            {"content": "You have to believe in yourself when no one else does.", "author": "Serena Williams", "type": "motivational"},
            {"content": "The success of every woman should be the inspiration to another. We should raise each other up.", "author": "Serena Williams", "type": "motivational"},
            
            # Other Athletes
            {"content": "I've failed over and over and over again in my life, and that is why I succeed.", "author": "Michael Jordan", "type": "motivational"},
            {"content": "The way I see it, if you want the rainbow, you gotta put up with the rain.", "author": "Dolly Parton", "type": "motivational"},
            {"content": "Champions keep playing until they get it right.", "author": "Billie Jean King", "type": "motivational"},
            {"content": "You miss 100% of the shots you don't take.", "author": "Wayne Gretzky", "type": "motivational"},
            {"content": "It's not whether you get knocked down; it's whether you get up.", "author": "Vince Lombardi", "type": "motivational"},
            {"content": "The will to win, the desire to succeed, the urge to reach your full potential... these are the keys that will unlock the door to personal excellence.", "author": "Confucius", "type": "motivational"},
            
            # Business and Entrepreneurship
            {"content": "Your work is going to fill a large part of your life, and the only way to be truly satisfied is to do what you believe is great work.", "author": "Steve Jobs", "type": "motivational"},
            {"content": "Innovation distinguishes between a leader and a follower.", "author": "Steve Jobs", "type": "motivational"},
            {"content": "The way to get started is to quit talking and begin doing.", "author": "Walt Disney", "type": "motivational"},
            {"content": "Don't be afraid to give up the good to go for the great.", "author": "John D. Rockefeller", "type": "motivational"},
            {"content": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill", "type": "motivational"},
            {"content": "The only impossible journey is the one you never begin.", "author": "Tony Robbins", "type": "motivational"},
            {"content": "What lies behind us and what lies before us are tiny matters compared to what lies within us.", "author": "Ralph Waldo Emerson", "type": "motivational"},
            {"content": "Success is going from failure to failure without losing your enthusiasm.", "author": "Winston Churchill", "type": "motivational"},
            {"content": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt", "type": "motivational"},
            {"content": "It does not matter how slowly you go as long as you do not stop.", "author": "Confucius", "type": "motivational"},
            
            # Additional Soccer Players
            {"content": "I once cried because I had no shoes to play football with my friends, but one day I saw a man who had no feet, and I realized how rich I am.", "author": "Zinedine Zidane", "type": "motivational"},
            {"content": "My game is based on improvisation. Often a forward does not know what he will do until he sees the defenders' reactions.", "author": "Ronaldinho", "type": "motivational"},
            {"content": "If there is one thing more than others that a successful footballer needs, it is energy.", "author": "Michel Platini", "type": "motivational"},
            {"content": "Failure happens all the time. It happens every day in practice. What makes you better is how you react to it.", "author": "Mia Hamm", "type": "motivational"},
            {"content": "As someone who loves football, I want to give something back to the game and help it develop further.", "author": "Franz Beckenbauer", "type": "motivational"},
            
            # Life and Success Quotes
            {"content": "The difference between ordinary and extraordinary is that little extra.", "author": "Jimmy Johnson", "type": "motivational"},
            {"content": "Excellence is not a skill, it's an attitude.", "author": "Ralph Marston", "type": "motivational"},
            {"content": "Champions aren't made in the gyms. Champions are made from something deep inside them - a desire, a dream, a vision.", "author": "Muhammad Ali", "type": "motivational"},
            {"content": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson", "type": "motivational"},
            {"content": "The harder you work, the harder it is to surrender.", "author": "Vince Lombardi", "type": "motivational"},
            {"content": "Success is where preparation and opportunity meet.", "author": "Bobby Unser", "type": "motivational"},
            {"content": "Confidence comes from discipline and training.", "author": "Robert Kiyosaki", "type": "motivational"},
            
            # More Inspirational Business Quotes
            {"content": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb", "type": "motivational"},
            {"content": "Whether you think you can or you think you can't, you're right.", "author": "Henry Ford", "type": "motivational"},
            {"content": "Don't let yesterday take up too much of today.", "author": "Will Rogers", "type": "motivational"},
            {"content": "You learn more from failure than from success. Don't let it stop you. Failure builds character.", "author": "Unknown", "type": "motivational"},
            {"content": "If you are not willing to risk the usual, you will have to settle for the ordinary.", "author": "Jim Rohn", "type": "motivational"},
            {"content": "All our dreams can come true if we have the courage to pursue them.", "author": "Walt Disney", "type": "motivational"},
            {"content": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt", "type": "motivational"},
        ]
        
        # Add quotes to database
        for quote_data in quotes:
            quote = models.MentalTrainingQuote(**quote_data)
            db.add(quote)
        
        db.commit()
        logger.info(f"✅ Successfully created mental training tables and seeded {len(quotes)} quotes")
        
    except Exception as e:
        logger.error(f"❌ Error creating mental training tables: {str(e)}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    create_mental_training_tables() 