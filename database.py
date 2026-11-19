
#from sqlalchemy import create_engine
#from sqlalchemy.orm import DeclarativeBase, sessionmaker

# import async versions of sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


# path to file-based SQLite database - relative path to current working directory (.) - will create the database file if it does not exist
#SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"
#SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"   # async version
#
##engine = create_engine(
#engine = create_async_engine(
#	SQLALCHEMY_DATABASE_URL,
#	connect_args={"check_same_thread": False},	# sqlite specific argument to allow multiple threads to access the database - needed for FastAPI
#)

# connect to PostgreSQL db with user and pw
#print(f"{settings.database_url=}")
engine = create_async_engine(settings.database_url)


# factory for creating new database sessions - will be used in the dependency injection system of FastAPI to get a database session for each request
#SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class DBBase (DeclarativeBase):
	pass


# generator to get a database session for each request - will be used in the dependency injection system of FastAPI
#def get_db ():
#	with SessionLocal() as db:
#		yield db

async def get_db ():
	async with AsyncSessionLocal() as session:
		yield session



