from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# SQLite database URL - this will create a file called "audio_learning.db"
# We used SQLite because it's simple and works offline
SQLALCHEMY_DATABASE_URL = "sqlite:///./audio_learning.db"

# Create database engine
# check_same_thread=False for SQLite only - allows multiple threads
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Create SessionLocal class - we use this to talk to database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class - all our database models inherit from this
Base = declarative_base()


# Dependency function - to get database session
def get_db():
    """
    This function gives us database session
    After use, it closes automatically
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")