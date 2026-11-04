#
# pydantic models for data validation and serialization
#
# separate from database models to avoid circular imports and to allow for different validation and serialization rules
#


# allow forward references
from __future__ import annotations

# pydantic is used for data validation and serialization
from pydantic import BaseModel, ConfigDict, Field, EmailStr

from datetime import datetime

# shared pydantic model for creating and returning posts, with validation and serialization
# pydantic will validate data based on type hints at runtime and raise a validation error if the data is invalid
class PostBase (BaseModel):
	#model_config = ConfigDict(extra="forbid")  # forbid extra fields in the input data
	#title: str = Field(..., min_length=1, max_length=100, description="The title of the post")
	#content: str = Field(..., min_length=1, description="The content of the post")

	title: str = Field(min_length=1, max_length=100, description="The title of the post")
	content: str = Field(min_length=1, description="The content of the post")

	# author is now User in the database - established by a relationship
	#author: str = Field(min_length=1, max_length=50, description="The author of the post")


class PostCreate (PostBase):
	#pass	# no additional fields for creating a post
	user_id: int	# TEMPORARY - will ulitmately come from user authentication system as current user id

# Update spec - patch mode - only update changed fields, make all fields optional
# if value specified then it is validated
# can't change user_id here - not included
# note inherits from BaseModel not PostBase
class PostUpdate (BaseModel):
	# same fields as PostBase but now optional with default value None
	title: str | None = Field(default=None, min_length=1, max_length=100)
	content: str | None = Field(default=None, min_length=1)


class PostResponse (PostBase):
	# configure the model to allow ORM objects to be returned as pydantic models
	# allow read from database models and return them as pydantic models
	#	also allows using dot notation: post.title instead of post["title"]
	model_config = ConfigDict(from_attributes=True)

	# additional fields for returning a post
	# id is a Python built-in type, but it is convention for databases

	# old params for dummy data
	#id: int
	#date_posted: str

	# new params from database
	id: int
	user_id: int
	date_posted: datetime		# serialized to standard automatically
	author: UserPublic		# this will automatically be retrieved from the database and validated





# in dummy data user was a string but now we have a User model in the database, so we can use that instead of a string
class UserBase (BaseModel):
	username: str = Field(min_length=1, max_length=50, description="The username of the user")
	email: EmailStr = Field(max_length=120, description="The email address of the user")	# validates correct email format

class UserCreate (UserBase):
	#pass
	password: str = Field(min_length=8, description="The password of the user")	# will be hashed before storing in database

# for patch updating user
# allow for updating user image
class UserUpdate (BaseModel):
	username: str | None = Field(default=None, min_length=1, max_length=50, description="The username of the user")
	email: EmailStr | None = Field(default=None, max_length=120, description="The email address of the user")	# validates correct email format
	image_file: str | None = Field(default=None, min_length=1, max_length=200)

# note that UserReponse will contain the user's email address - possibly a security concern for public data
#class UserResponse (UserBase):
#	model_config = ConfigDict(from_attributes=True)
#
#	id: int
#	image_file: str | None
#	image_path: str							# property on model - not stored in database

# split UserResponse into two models - one for public data and one for private data
# does not include email address - for public data
class UserPublic (BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	username: str
	image_file: str | None
	image_path: str							# property on model - not stored in database

class UserPrivate (UserPublic):
	email: EmailStr

# access tokens for authentication - will be used for JWT tokens
class Token (BaseModel):
	access_token: str
	token_type: str

