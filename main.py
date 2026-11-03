#
# new main.py after to reorganization in Tutorial #8
#


from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
	http_exception_handler,
	request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

import database_models
from database import DBBase, engine, get_db

# import individual routers from routers module
from routers import posts, users


# create database tables - if don't already exist
@asynccontextmanager
async def lifespan (_app: FastAPI):
	# startup
	async with engine.begin() as conn:
		await conn.run_sync(DBBase.metadata.create_all)	# run synchronous call async
	yield

	# shutdown
	await engine.dispose()


# create app object
#app = FastAPI()
app = FastAPI(lifespan=lifespan)

# create templates object to use Jinja2Templates for HTML responses
templates = Jinja2Templates(directory="templates")	# tell Jinja2 where to find our HTML templates

# mount the static and media files directories
app.mount("/static", StaticFiles(directory="static"), name="static")	# tell FastAPI where to find our static files
app.mount("/media", StaticFiles(directory="media"), name="media")

# include the routers
# API doc will now be organized under tags and collapseable
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


# regular routes - return HTML

# home - get all posts
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home (request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
	# get all posts without filter
	# await on this since we are running async
	# must explicitly specify to load (eager load) associated author (User) data for each Post that we load
	result = await db.execute(select(database_models.Post).options(selectinload(database_models.Post.author)).order_by(database_models.Post.id.desc()))
	posts = result.scalars().all()
	return templates.TemplateResponse(
		request,
		"home_template4.html",
		{"posts": posts, "title": "Home"},
	)

# get a post by id from the database
@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page (request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.Post)
								.options(selectinload(database_models.Post.author))		# eager load of author data
								.where(database_models.Post.id == post_id))
	post = result.scalars().first()
	if post:
		title = post.title[:50]
		return templates.TemplateResponse(
			request,
			"post_template.html",
			{"post": post, "title": title},
		)
	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


# get all posts from a user by id from database
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts_page")
async def user_posts_page (request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	# doesn't need selectinload bc don't need associated Post data
	result = await db.execute(select(database_models.User).where(database_models.User.id == user_id))
	user = result.scalars().first()
	if not user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	# here we do need selectinload
	result = await db.execute(select(database_models.Post)
							  .options(selectinload(database_models.Post.author))		# before where()
							  .where(database_models.Post.user_id == user_id)
							  .order_by(database_models.Post.id.desc())					# sort by id descending so newest posts first
							  )
	posts = result.scalars().all()
	return templates.TemplateResponse(request, "user_posts_template.html", {"posts": posts, "user": user, "title": f"{user.username}'s Posts"})



# /api/* routes will return JSON
#
# moved to routers/ sub-module
#


# exception handlers for custom error responses
# handle 404 errors for HTML responses
# using StarletteHTTPException Handler automatically handles cases where the route is not found like http://127.0.0.1:8000/xxxxx
# fastapi.HTTPException is a subclass so it will also get handled here
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler (request: Request, exception: StarletteHTTPException):
	# error message
	message = (
		exception.detail
		if exception.detail
		else "An error occurred. Please check your request and try again."
	)

	# if from api route, return JSON response
	if request.url.path.startswith("/api"):
		# use FastAPI's handler - async and cleaner
		return await http_exception_handler(request, exception)

	# otherwise return HTML response
	return templates.TemplateResponse(
		request,
		"error_template.html",
		{
			"status_code": exception.status_code,
			"title": exception.status_code,
			"message": message,
		},
		status_code=exception.status_code,
	)


### handle validation errors for HTML and JSON responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler (request: Request, exception: RequestValidationError):
	if request.url.path.startswith("/api"):
		return await request_validation_exception_handler(request, exception)
	
	return templates.TemplateResponse(
		request,
		"error_template.html",
		{
			"status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
			"title": status.HTTP_422_UNPROCESSABLE_CONTENT,
			"message": "Invalid request. Please check your input and try again.",
		},
		status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
	)


