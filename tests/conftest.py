#
# recognized by pytest automatically
#
# fixtures and other shared setup - imported automatically
#

# set fake env vars for testing - don't use real ones
# must match env vars in .env
# this needs to happen before we load settings with the app below
import os
from collections.abc import AsyncGenerator

## Test DB and Bucket
os.environ["DATABASE_URL"] = (
	"postgresql+psycopg://bloguser:blogpass@localhost/test_blog"	# need to create new test database
)
os.environ["S3_BUCKET_NAME"] = "test-bucket"						# dummy S3 bucket - used with moto
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

## Dummy S3/AWS Credentials
os.environ["S3_ACCESS_KEY_ID"] = "testing"
os.environ["S3_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_REGION"] = "us-east-2"

# not in .env but boto3 might create these
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-2"


## App Imports
import boto3
import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database import DBBase, get_db
from main import app

# fix Windows issue with asyncio
import sys
import asyncio
if sys.platform == "win32":
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())




# enable pytest plugins - appear as decorators
pytest_plugins = ["anyio"]

# pytest fixture - defines backend used by anyio - could be others
@pytest.fixture(scope="session")
def anyio_backend ():
	return "asyncio"


## Test Engine fixture - creates test db engine
# session scoped - done once per entire test session
@pytest.fixture(scope="session")
def test_engine ():
	engine = create_async_engine(
		os.environ["DATABASE_URL"],
		poolclass=NullPool,			# disable connection pooling - prevents problems
	)
	return engine

## Setup Database - create all the tables at start, drop all tables at end and dispose of the engine
@pytest.fixture(scope="session")
async def setup_database (test_engine):
	# run at start of testing
	async with test_engine.begin() as conn:
		await conn.run_sync(DBBase.metadata.create_all)	# create_all() is sync
	yield

	# tests run here...

	# run at end of testing
	async with test_engine.begin() as conn:
		await conn.run_sync(DBBase.metadata.drop_all)		# drop_all() is also sync
	await test_engine.dispose()


## DB Session (Transactional Rollback)
# default scoping: function scoped (run each test)
@pytest.fixture
async def db_session(
	test_engine,
	setup_database,
) -> AsyncGenerator[AsyncSession]:
	# create connection and transaction per test
	conn = await test_engine.connect()
	trans = await conn.begin()

	test_async_session = async_sessionmaker(
		bind=conn,										# bind to the current connection
		class_=AsyncSession,
		expire_on_commit=False,
		join_transaction_mode="create_savepoint",		# fake commit - creates savepoint instead of actual commit - allows for rollback
	)

	async with test_async_session() as session:
		try:
			yield session

		# end of test - close session, rollback changes, close connection
		finally:
			await session.close()
			await trans.rollback()
			await conn.close()


## Mocked AWS - sync
# intercepts boto3 calls and re-routes to S3 emulator in memory
@pytest.fixture
def mocked_aws():
	with mock_aws():
		s3 = boto3.client("s3", region_name="us-east-1")	# this has to be "us-east-1"
		s3.create_bucket(Bucket=os.environ["S3_BUCKET_NAME"])
		yield s3


## Client Fixture
@pytest.fixture
async def client(
	db_session: AsyncSession,
	mocked_aws,
) -> AsyncGenerator[AsyncClient]:

	async def override_get_db():
		yield db_session

	# overrides get_db with test version
	app.dependency_overrides[get_db] = override_get_db

	# httpx async client - mocks network connection with local
	# won't run lifespan function
	async with AsyncClient(
		transport=ASGITransport(app=app),	# override network transport
		base_url="http://test",				# required but not used
	) as ac:
		yield ac

	app.dependency_overrides.clear()


## Auth Helpers
async def create_test_user(
	client: AsyncClient,
	username: str = "testuser",
	email: str = "test@example.com",
	password: str = "testpassword123",
) -> dict:
	response = await client.post(
		"/api/users",
		json={
			"username": username,
			"email": email,
			"password": password,
		},
	)
	assert response.status_code == 201, f"Failed to create user: {response.text}"	# assert with failure message
	return response.json()


async def login_user(
	client: AsyncClient,
	email: str = "test@example.com",
	password: str = "testpassword123",
) -> str:
	response = await client.post(
		"/api/users/token",
		data={							# form data, not JSON
			"username": email,
			"password": password,
		},
	)
	assert response.status_code == 200, f"Failed to login: {response.text}"
	return response.json()["access_token"]


def auth_header (token: str) -> dict[str, str]:
	return {"Authorization": f"Bearer {token}"}




