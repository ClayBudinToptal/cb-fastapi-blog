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

router = APIRouter()

# get all posts
@router.get("", response_model=list[PostResponse])
async def get_posts (db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(
		select(database_models.Post)
		.options(selectinload(database_models.Post.author))
		.order_by(database_models.Post.id.desc())
	)
	posts = result.scalars().all()
	return posts

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
@router.put("/{post_id}", response_model=PostResponse)
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
@router.patch("/{post_id}", response_model=PostResponse)
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
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post (post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
	result = await db.execute(select(database_models.Post).where(database_models.Post.id == post_id))
	post = result.scalars().first()
	if not post: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

	# delete post from database and commit
	# should only allow author to delete post
	await db.delete(post)
	await db.commit()



