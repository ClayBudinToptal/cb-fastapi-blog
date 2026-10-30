
# pydantic is used for data validation and serialization
from pydantic import BaseModel, ConfigDict, Field

# shared pydantic model for creating and returning posts, with validation and serialization
# pydantic will validate data based on type hints at runtime and raise a validation error if the data is invalid
class PostBase (BaseModel):
	#model_config = ConfigDict(extra="forbid")  # forbid extra fields in the input data
	#title: str = Field(..., min_length=1, max_length=100, description="The title of the post")
	#content: str = Field(..., min_length=1, description="The content of the post")

	title: str = Field(min_length=1, max_length=100, description="The title of the post")
	content: str = Field(min_length=1, description="The content of the post")
	author: str = Field(min_length=1, max_length=50, description="The author of the post")


class PostCreate (PostBase):
	pass	# no additional fields for creating a post


class PostResponse (PostBase):
	# configure the model to allow ORM objects to be returned as pydantic models
	# allow read from database models and return them as pydantic models
	#	also allows using dot notation: post.title instead of post["title"]
	model_config = ConfigDict(from_attributes=True)

	# additional fields for returning a post
	# id is a Python built-in type, but it is convention for databases
	id: int
	date_posted: str


