#
# new main.py after to reorganization in Tutorial #8
#


# app imports
from fastapi import FastAPI, Request 			# Request is needed to pass to the template for generating URLs for static files
#from fastapi.responses import HTMLResponse   	# don't need this any more since we are using Jinja2Templates
from fastapi.templating import Jinja2Templates	# templating system for HTML responses
from fastapi.staticfiles import StaticFiles		# to serve static files like CSS, JS, images, etc. - mounted below

# import pydantic models (schemas) for data validation and serialization
from schemas import PostCreate, PostUpdate, PostResponse, UserCreate, UserUpdate, UserResponse

# database support
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends						# dependency injection
from sqlalchemy import select					# queries
#from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

# enable eager loads (not lazy loads)
# with synchronous db access, associations and relationships are lazy loaded automatically
#  eg authors (Users) are loaded for each Post retrieved
# with async these must be loaded explicitly (eager loading)
from sqlalchemy.orm import selectinload

import database_models
from database import DBBase, engine, get_db


# error handling imports
from fastapi import HTTPException, status		# HTTPException is needed to return 404 error, status gives us access to standard HTTP status codes
from fastapi.exceptions import RequestValidationError	# RequestValidationError is needed to handle validation errors and return a custom response
#from fastapi.responses import JSONResponse		# JSONResponse is needed to return a custom JSON response for validation errors
# fastapi is built on top of starlette, so we can also import from starlette if needed
from starlette.exceptions import HTTPException as StarletteHTTPException	# needed to handle 404 errors and return a custom response
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler



# create database tables - if don't already exist
#DBBase.metadata.create_all(bind=engine)

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


# regular routes - return HTML

# home - get all posts
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home (request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
	# get all posts without filter
	# await on this since we are running async
	# must explicitly specify to load (eager load) associated author (User) data for each Post that we load
	result = await db.execute(select(database_models.Post).options(selectinload(database_models.Post.author)))
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
	                    	  .where(database_models.Post.user_id == user_id))
	posts = result.scalars().all()
	return templates.TemplateResponse(request, "user_posts_template.html", {"posts": posts, "user": user, "title": f"{user.username}'s Posts"})



# /api/* routes will return JSON


@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts (db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.Post).options(selectinload(database_models.Post.author)))
	posts = result.scalars().all()
	return posts


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post (post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	if post:
		return post
	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

@app.post(
	"/api/posts",
	response_model=PostResponse,
	status_code=status.HTTP_201_CREATED,
)
async def create_post (post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.User).where(database_models.User.id == post.user_id))
	user = result.scalars().first()
	if not user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	new_post = database_models.Post(
		title=post.title,
		content=post.content,
		user_id=post.user_id,
	)
	db.add(new_post)
	await db.commit()
	await db.refresh(new_post, attribute_names=["author"])	# similar to selectinload force relationships to refresh as well
	return new_post


# update a post - full update - replace all (put) - need all fields so use PostCreate
@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_full (post_id: int, post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
	# retrieve the post by its id
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	if not post:
		# here we raise error if post not found
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

	# if updaing user, check new user exists
	if post_data.user_id != post.user_id:
		result = await db.execute(select(database_models.User).where(database_models.User.id == post_data.user_id))
		user = result.scalars().first()
		if not user:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	# update post full - all fields
	post.title = post_data.title
	post.content = post_data.content
	post.user_id = post_data.user_id

	# update database
	await db.commit()
	await db.refresh(post, attribute_names=["author"])
	return post


# update a post - partial update - replace only changed fields (patch)
@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_partial (post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
	# retrieve the post by its id
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	# here we raise error if post not found
	if not post: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

	# no user_id in PostUpdate, so no user check

	# get new data - only set fields
	update_data = post_data.model_dump(exclude_unset=True)

	# update post partial - only set fields
	for field, value in update_data.items():
		setattr(post, field, value)		# set values with dynamic fields

	# update database
	await db.commit()
	await db.refresh(post, attribute_names=["author"])
	return post

# delete a post
# no response object, just 204 NO CONTENT
@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post (post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	if not post: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

	# delete post from database and commit
	# should only allow author to delete post
	await db.delete(post)
	await db.commit()

# get all users
@app.get("/api/users", response_model=list[UserResponse])
async def get_users (db: Annotated[AsyncSession, Depends(get_db)]):
	#result = await db.execute(select(database_models.User).options(selectinload(database_models.Post.author)))
	result = await db.execute(select(database_models.User))
	posts = result.scalars().all()
	return posts



# get all the posts by a user from the database
@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts (user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	# check user exists to differentiate between empty list bc no user or no posts
	result = await db.execute(select(database_models.User).where(database_models.User.id == user_id))
	user = result.scalars().first()
	if not user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
	result = await db.execute(select(database_models.Post)
	                          .options(selectinload(database_models.Post.author))
	                          .where(database_models.Post.user_id == user_id))
	posts = result.scalars().all()
	return posts



# Create a new user in the database
@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, name="create_user")
async def create_user (user: UserCreate, db:Annotated[AsyncSession, Depends(get_db)]):
	# check for existing user
	result = await db.execute(select(database_models.User).where(database_models.User.username == user.username))
	existing_user = result.scalars().first()
	# database won't allow us to enter another user with the same name as existing (unique=True) but this is cleaner
	if existing_user: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

	# check for existing email
	result = await db.execute(select(database_models.User).where(database_models.User.email == user.email))
	existing_email = result.scalars().first()
	if existing_email: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

	# add to database
	new_user = database_models.User(username=user.username, email=user.email)
	db.add(new_user)			# stage add - don't need to await this - only adds object to pending list, no i/o
	await db.commit()			# execute and save database
	await db.refresh(new_user)	# reload object from database

	return new_user				# pydantic will convert this to UserResponse


# get a user by id from the database
@app.get("/api/users/{user_id}", response_model=UserResponse, name="get_user")	# use pydantic model for validation and serialization
async def get_user (user_id: int, db:Annotated[AsyncSession, Depends(get_db)]):
	# get user
	result = await db.execute(select(database_models.User).where(database_models.User.id == user_id))
	user = result.scalars().first()
	if user:
		return user
	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")



# patch update a user - don't really need a put
@app.patch("/api/users/{user_id}", response_model=UserResponse)
async def update_user(
	user_id: int,
	user_update: UserUpdate,
	db: Annotated[AsyncSession, Depends(get_db)],
):
	# find user
	result = await db.execute(select(database_models.User).where(database_models.User.id == user_id))
	user = result.scalars().first()
	if not user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	# if username is changing, make sure it is not already in use
	if user_update.username is not None and user_update.username != user.username:
		result = await db.execute(select(database_models.User).where(database_models.User.username == user_update.username))
		existing_user = result.scalars().first()
		if existing_user: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

	# check email not already in use
	if user_update.email is not None and user_update.email != user.email:
		result = await db.execute(select(database_models.User).where(database_models.User.email == user_update.email))
		existing_email = result.scalars().first()
		if existing_email: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

	# update set values
	if user_update.username is not None:
		user.username = user_update.username
	if user_update.email is not None:
		user.email = user_update.email
	if user_update.image_file is not None:
		user.image_file = user_update.image_file

	await db.commit()
	await db.refresh(user)
	return user

# delete a user
# set up in database_models to automatically delete all posts by this user (cascade delete)
@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user (user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(database_models.User).where(database_models.User.id == user_id))
    user = result.scalars().first()
    if not user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)	# unlike .add(), .delete() needs await
    await db.commit()



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


