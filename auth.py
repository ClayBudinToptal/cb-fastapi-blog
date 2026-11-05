
from datetime import datetime, timedelta, UTC
import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from config import settings

from typing import Annotated	# allows us to use Annotated types
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import database_models
from database import get_db


password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")

# hash a password using Argon2
# better to hash a password than to encrypt it, because hashing is one-way and cannot be reversed
#  while encryption can be decrypted if the key is known, or can be brute-forced if the key is weak
def hash_password (password: str) -> str:
	"""Hash a password using Argon2."""
	return password_hash.hash(password)

def verify_password (plain_password: str, hashed_password: str) -> bool:
	"""Verify a password against its hash."""
	return password_hash.verify(plain_password, hashed_password)

## create_access_token
def create_access_token (data: dict, expires_delta: timedelta | None = None) -> str:
	"""Create a JWT access token."""
	to_encode = data.copy()
	if expires_delta:
		expire = datetime.now(UTC) + expires_delta
	else:
		expire = datetime.now(UTC) + timedelta(
			minutes=settings.access_token_expire_minutes,
		)
	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(
		to_encode,
		settings.secret_key.get_secret_value(),		# use get_secret_value() to get the actual string value of the SecretStr
		algorithm=settings.algorithm,
	)
	return encoded_jwt

## verify_access_token
def verify_access_token (token: str) -> str | None:
	"""Verify a JWT access token and return the subject (user id) if valid."""
	try:
		payload = jwt.decode(
			token,
			settings.secret_key.get_secret_value(),
			algorithms=[settings.algorithm],
			options={"require": ["exp", "sub"]},
		)
	except jwt.InvalidTokenError:
		return None
	else:
		return payload.get("sub")

# get the current user from database using the jwt access token
# this will be used as a dependency in routes that require authentication
async def get_current_user(
	token: Annotated[str, Depends(oauth2_scheme)],
	db: Annotated[AsyncSession, Depends(get_db)],
) -> database_models.User:
	# get the user id from the token
	user_id = verify_access_token(token)
	if user_id is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired token",
			headers={"WWW-Authenticate": "Bearer"},
		)

	# convert it from a string to an int - if it fails then the token is invalid
	try:
		user_id_int = int(user_id)
	except (TypeError, ValueError):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid or expired token",
			headers={"WWW-Authenticate": "Bearer"},
		)

	# query the database for the user with the given id
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

# create an alias for the current user type to be used in route dependencies
#  Annotated is used to add metadata to the type, in this case to specify that it is a dependency on the get_current_user function
CurrentUser = Annotated[database_models.User, Depends(get_current_user)]


