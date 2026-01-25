from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database URL - this go create a file called "audio_learning.db"
# We dey use SQLite because e simple and work offline
SQLALCHEMY_DATABASE_URL = "sqlite:///./audio_learning.db"

# Create database engine
# check_same_thread=False na for SQLite only - e allow multiple threads
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Create SessionLocal class - we go use am to talk to database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class - all our database models go inherit from this
Base = declarative_base()

# Dependency function - to get database session
def get_db():
    """
    This function go give us database session
    When we done use am, e go close automatically
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()