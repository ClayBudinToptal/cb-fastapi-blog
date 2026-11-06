#
# Router for Posts
#

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import database_models
from database import get_db
from schemas import PostCreate, PostResponse, PostUpdate

from auth import CurrentUser

# imports for pagination
from fastapi import Query
from sqlalchemy import func
from schemas import PaginatedPostsResponse




router = APIRouter()

# get all posts
#@router.get("", response_model=list[PostResponse])
#async def get_posts (db: Annotated[AsyncSession, Depends(get_db)]):
#	result = await db.execute(
#		select(database_models.Post)
#		.options(selectinload(database_models.Post.author))
#		.order_by(database_models.Post.id.desc())
#	)
#	posts = result.scalars().all()
#	return posts

# paginated version
@router.get("", response_model=PaginatedPostsResponse)
async def get_posts (
	db: Annotated[AsyncSession, Depends(get_db)],
	skip: Annotated[int, Query(ge=0)] = 0,
	limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
	# query the db to get the total number of posts
	count_result = await db.execute(select(func.count()).select_from(database_models.Post))
	total = count_result.scalar() or 0

	# retrieve posts using skip and limit
	result = await db.execute(
		select(database_models.Post)
		.options(selectinload(database_models.Post.author))
		.order_by(database_models.Post.id.desc())		# important for consistent pagination
		.offset(skip)
		.limit(limit)
	)
	posts = result.scalars().all()

	has_more = skip + len(posts) < total

	return PaginatedPostsResponse(
		# normally fastapi will validate the output automatically, but since we are building a list we need to manually do it
		posts=[PostResponse.model_validate(post) for post in posts], 
		total=total,
		skip=skip,
		limit=limit,
		has_more=has_more,
	)




# get post by id
@router.get("/{post_id}", response_model=PostResponse)
async def get_post (post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	if post:
		return post
	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

# create a new post
@router.post(
	"",
	response_model=PostResponse,
	status_code=status.HTTP_201_CREATED,
)
# adding current_user: CurrentUser as a dependency will automatically get the current user from the token and pass it to the function
#  if the user is not authenticated, it will raise a 401 error
async def create_post (post: PostCreate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
	# don't need to check if user exists - current_user is already validated and retrieved from the database
	#result = await db.execute(select(database_models.User).where(database_models.User.id == post.user_id))
	#user = result.scalars().first()
	#if not user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	new_post = database_models.Post(
		title=post.title,
		content=post.content,
		#user_id=post.user_id,
		user_id=current_user.id,	# get the user id from the current user object instead of the post data
	)
	db.add(new_post)
	await db.commit()
	await db.refresh(new_post, attribute_names=["author"])	# similar to selectinload force relationships to refresh as well
	return new_post

# update a post - full update - replace all (put) - need all fields so use PostCreate
@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full (post_id: int, current_user: CurrentUser, post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
	# retrieve the post by its id
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	if not post:
		# here we raise error if post not found
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

	# if updaing user, check new user exists
	#if post_data.user_id != post.user_id:
	#	result = await db.execute(select(database_models.User).where(database_models.User.id == post_data.user_id))
	#	user = result.scalars().first()
	#	if not user:
	#		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	# check if the current user is the author of the post - only allow author to update post
	if post.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this post")

	# update post full - all fields
	post.title = post_data.title
	post.content = post_data.content
	#post.user_id = post_data.user_id

	# update database
	await db.commit()
	await db.refresh(post, attribute_names=["author"])
	return post

# update a post - partial update - replace only changed fields (patch)
@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial (post_id: int, current_user: CurrentUser, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
	# retrieve the post by its id
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	# here we raise error if post not found
	if not post: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

	# check if the current user is the author of the post - only allow author to update post
	if post.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this post")

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
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post (post_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	if not post: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

	# check if the current user is the author of the post - only allow author to delete post
	if post.user_id != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this post")

	# delete post from database and commit
	await db.delete(post)
	await db.commit()



