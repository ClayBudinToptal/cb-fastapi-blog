#
# Router for Users
#

# only need imports that pertain to Users
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import database_models
from database import get_db
from schemas import PostResponse, UserCreate, UserPublic, UserPrivate, UserUpdate, Token

# authentication imports - needed for login and token generation
from datetime import timedelta, datetime
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func		# allows for case-insensitive search with func.lower()
from auth import create_access_token, hash_password, verify_password, oauth2_scheme, verify_access_token
from config import settings

# create Router for User
router = APIRouter()

# only move /api/ routes here from main.py
# leave template-based web-served pages in main.py

# Create a new user in the database
#@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, name="create_user")

# use router - paths are relative to base prefix, main.py will have "/api/users" prefix when router is included
# function names can conflict across different routers
@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED, name="create_user")
async def create_user (user: UserCreate, db:Annotated[AsyncSession, Depends(get_db)]):
	# check for existing user
	result = await db.execute(
		select(database_models.User)
		.where(func.lower(database_models.User.username) == user.username.lower())	# case-insensitive search for username
		)
	existing_user = result.scalars().first()
	# database won't allow us to enter another user with the same name as existing (unique=True) but this is cleaner
	if existing_user: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

	# check for existing email
	result = await db.execute(select(database_models.User).where(func.lower(database_models.User.email) == user.email.lower()))
	existing_email = result.scalars().first()
	if existing_email: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

	# add to database
	new_user = database_models.User(
		username=user.username,
		email=user.email.lower(),
		password_hash=hash_password(user.password),	# hash the password before storing in database
	)
	db.add(new_user)			# stage add - don't need to await this - only adds object to pending list, no i/o
	await db.commit()			# execute and save database
	await db.refresh(new_user)	# reload object from database

	return new_user				# pydantic will convert this to UserResponse

## login_for_access_token
@router.post ("/token", response_model=Token)
async def login_for_access_token(
	form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
	db: Annotated[AsyncSession, Depends(get_db)],
):
	# Look up user by email (case-insensitive)
	# Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
	result = await db.execute(
		select(database_models.User).where(
			func.lower(database_models.User.email) == form_data.username.lower(),
		),
	)
	user = result.scalars().first()

	# Verify user exists and password is correct
	# Don't reveal which one failed (security best practice)
	if not user or not verify_password(form_data.password, user.password_hash):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Incorrect email or password",
			headers={"WWW-Authenticate": "Bearer"},
		)

	# Create access token with user id as subject
	access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
	access_token = create_access_token(
		data={"sub": str(user.id)},
		expires_delta=access_token_expires,
	)
	return Token(access_token=access_token, token_type="bearer")


## get_current_user
# best practice is to put unparameterized dependencies before parameterized dependencies in the function signature
#  should not matter with type hints, but just in case
# better than just accessing the token in JS because this will validate it as well and return the user object from the database
@router.get("/me", response_model=UserPrivate)
async def get_current_user(
	token: Annotated[str, Depends(oauth2_scheme)],
	db: Annotated[AsyncSession, Depends(get_db)],
):
	"""Get the currently authenticated user."""
	user_id = verify_access_token(token)
	if user_id is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired token",
			headers={"WWW-Authenticate": "Bearer"},
		)

	# Validate user_id is a valid integer (defense against malformed JWT)
	try:
		user_id_int = int(user_id)
	except (TypeError, ValueError):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired token",
			headers={"WWW-Authenticate": "Bearer"},
		)

	result = await db.execute(
		select(database_models.User).where(database_models.User.id == user_id_int),
	)
	user = result.scalars().first()
	if not user:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="User not found",
			headers={"WWW-Authenticate": "Bearer"},
		)
	return user



# get all users
@router.get("", response_model=list[UserPublic])
async def get_users (db: Annotated[AsyncSession, Depends(get_db)]):
	#result = await db.execute(select(database_models.User).options(selectinload(database_models.Post.author)))
	result = await db.execute(select(database_models.User))
	posts = result.scalars().all()
	return posts

# get all the posts by a user from the database
@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts (user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	# check user exists to differentiate between empty list bc no user or no posts
	result = await db.execute(select(database_models.User).where(func.lower(database_models.User.id) == user_id.lower()))
	user = result.scalars().first()
	if not user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
	result = await db.execute(select(database_models.Post)
							  .options(selectinload(database_models.Post.author))
							  .where(database_models.Post.user_id == user_id)
							  .order_by(database_models.Post.id.desc())
							  )
	posts = result.scalars().all()
	return posts

# get a user by id from the database
@router.get("/{user_id}", response_model=UserPublic, name="get_user")	# use pydantic model for validation and serialization
async def get_user (user_id: int, db:Annotated[AsyncSession, Depends(get_db)]):
	# get user
	result = await db.execute(select(database_models.User).where(func.lower(database_models.User.id) == user_id.lower()))
	user = result.scalars().first()
	if user:
		return user
	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

# patch update a user - don't really need a put
@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
	user_id: int,
	user_update: UserUpdate,
	db: Annotated[AsyncSession, Depends(get_db)],
):
	# find user
	result = await db.execute(select(database_models.User).where(func.lower(database_models.User.id) == user_id.lower()))
	user = result.scalars().first()
	if not user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	# if username is changing, make sure it is not already in use
	if user_update.username is not None and user_update.username != user.username:
		result = await db.execute(select(database_models.User).where(func.lower(database_models.User.username) == user_update.username.lower()))
		existing_user = result.scalars().first()
		if existing_user: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

	# check email not already in use
	if user_update.email is not None and user_update.email != user.email:
		result = await db.execute(select(database_models.User).where(func.lower(database_models.User.email) == user_update.email.lower()))
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
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user (user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.User).where(func.lower(database_models.User.id) == user_id.lower()))
	user = result.scalars().first()
	if not user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	await db.delete(user)	# unlike .add(), .delete() needs await
	await db.commit()



