#
# Demo of synchronous testing in FastAPI
#
# Run test with:
# > uv run pytest tests/test_demo.py -v
#

from fastapi import FastAPI
from fastapi.testclient import TestClient

# simple FastAPI application - use this rather than our full app
demo_app = FastAPI()

@demo_app.get("/")
def demo_home ():
	return { "message" : "Hello!" }


# create testing client to test demo app
# this is synchronous
client = TestClient(demo_app)

def test_homepage ():
	response = client.get("/")

	# if False, raises an AssertionError
	assert response.status_code == 200



