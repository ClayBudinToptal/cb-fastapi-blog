#
# uv run pytest tests/test_posts.py -v
#

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_user

# starts with clean (empty) database

# simplest test - no posts in db at start
@pytest.mark.anyio	# async plugin
async def test_get_posts_empty (client: AsyncClient):	# pytest fixture injection - matches with fixures by name - in file then conftest.py
	response = await client.get("/api/posts")		# send the request to the route end point

	# assertions of what we get back
	assert response.status_code == 200

	data = response.json()
	assert data["posts"] == []
	assert data["total"] == 0
	assert data["has_more"] is False






