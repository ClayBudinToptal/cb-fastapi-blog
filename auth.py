
from datetime import datetime, timedelta, UTC
import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from config import settings

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
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
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
def verify_access_token(token: str) -> str | None:
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



