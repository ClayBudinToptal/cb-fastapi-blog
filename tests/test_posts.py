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


@pytest.mark.anyio	# async plugin
async def test_get_posts_not_found (client: AsyncClient):	# pytest fixture injection - matches with fixures by name - in file then conftest.py
	response = await client.get("/api/posts/999")		# send the request to the route end point

	# assertions of what we get back
	assert response.status_code == 404

	data = response.json()["detail"] == "Post not found"


## Test Create Post Success
@pytest.mark.anyio
async def test_create_post_success (client: AsyncClient):
	# create and authenticate user - this will be rolled back (deleted) after test runs
	user = await create_test_user(client)
	token = await login_user(client)
	headers = auth_header(token)	# authenticated header to send

	response = await client.post(
		"/api/posts",
		json={"title": "My First Post", "content": "This is the content"},
		headers=headers,
	)

	assert response.status_code == 201
	data = response.json()
	assert data["title"] == "My First Post"
	assert data["content"] == "This is the content"
	assert data["user_id"] == user["id"]
	assert "id" in data
	assert "date_posted" in data
	assert data["author"]["username"] == "testuser"


## Test Create Post Unauthorized
@pytest.mark.anyio
async def test_create_post_unauthorized (client: AsyncClient):
	# no authorized user created - no header
	response = await client.post(
		"/api/posts",
		json={"title": "Test Post", "content": "Test content"},
	)

	assert response.status_code == 401
	assert response.json()["detail"] == "Not authenticated"		# FastAPI's OAuth2 error response


## Test Update Post Success
@pytest.mark.anyio
async def test_update_post_success (client: AsyncClient):
	await create_test_user(client)
	token = await login_user(client)
	headers = auth_header(token)

	response = await client.post(
		"/api/posts",
		json={"title": "Original Title", "content": "Original content"},
		headers=headers,
	)
	post_id = response.json()["id"]

	response = await client.patch(
		f"/api/posts/{post_id}",
		json={"title": "Updated Title"},
		headers=headers,
	)

	assert response.status_code == 200
	data = response.json()
	assert data["title"] == "Updated Title"
	assert data["content"] == "Original content"


## Test Update Post Wrong User
@pytest.mark.anyio
async def test_update_post_wrong_user (client: AsyncClient):
	await create_test_user(client, username="user1", email="user1@example.com")
	token1 = await login_user(client, email="user1@example.com")

	response = await client.post(
		"/api/posts",
		json={"title": "User 1's Post", "content": "Only user 1 can edit this"},
		headers=auth_header(token1),
	)
	post_id = response.json()["id"]

	# create a second user and try to update the post from first user
	await create_test_user(client, username="user2", email="user2@example.com")
	token2 = await login_user(client, email="user2@example.com")

	response = await client.patch(
		f"/api/posts/{post_id}",
		json={"title": "Hacked Title"},
		headers=auth_header(token2),
	)

	assert response.status_code == 403
	assert response.json()["detail"] == "Not authorized to update this post"


## Test Pagination
@pytest.mark.anyio
async def test_get_posts_with_pagination (client: AsyncClient):
	await create_test_user(client)
	token = await login_user(client)
	headers = auth_header(token)

	# create 5 posts
	for i in range(5):
		response = await client.post(
			"/api/posts",
			json={"title": f"Post {i}", "content": f"Content for post {i}"},
			headers=headers,
		)
		assert response.status_code == 201		# assert post succeeds

	# get posts without pagination
	response = await client.get("/api/posts")
	assert response.status_code == 200
	data = response.json()
	assert data["total"] == 5
	assert len(data["posts"]) == 5
	assert data["has_more"] is False

	# test limit parameter
	response = await client.get("/api/posts?limit=2")
	assert response.status_code == 200
	data = response.json()
	assert data["total"] == 5
	assert len(data["posts"]) == 2
	assert data["has_more"] is True

	# test limit and skip
	response = await client.get("/api/posts?skip=2&limit=2")
	assert response.status_code == 200
	data = response.json()
	assert data["total"] == 5
	assert len(data["posts"]) == 2
	assert data["skip"] == 2
	assert data["limit"] == 2
	# could test post contents



