
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# path to file-based SQLite database - relative path to current working directory (.) - will create the database file if it does not exist
SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},	# sqlite specific argument to allow multiple threads to access the database - needed for FastAPI
)

# factory for creating new database sessions - will be used in the dependency injection system of FastAPI to get a database session for each request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DBBase (DeclarativeBase):
    pass


# generator to get a database session for each request - will be used in the dependency injection system of FastAPI
def get_db ():
    with SessionLocal() as db:
        yield db




