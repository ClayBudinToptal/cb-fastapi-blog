#
# database models are kept separate from pydantic schemas mainly because they serve different purposes
#
# there is a module called sqlmodel that combines pydantic and sqlalchemy, but it is not as widely used as sqlalchemy and pydantic separately
# 

# allow for forward references in type hints, which is useful for defining relationships between models that refer to each other
from __future__ import annotations

from datetime import UTC, datetime		# timestamps

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import DBBase


# User model for the database - represents a user in the system
class User (DBBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

	# just store the filename of the image in the database, not the full path - easier to change path later
    image_file: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
    )

	# list of posts by this user - relationship to Post model - back_populates is used to define the reverse relationship in the Post model
    # one-to-many relationship: one user can have many posts, but each post has only one author
    # note that Post is a forward reference here, since Post is defined later in the file - that's why we need to import annotations from __future__ at the top of the file
    #  standard in Python 3.14+
    #posts: Mapped[list[Post]] = relationship(back_populates="author")
    
	# updated to have cascaded deletion
    # all means delete all posts if user is delted, delete-orphan cleans up posts which don't have users assigned
    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")

	# property method to generate the full path to the user's profile image - if no image is set, return a default image path
    @property
    def image_path (self) -> str:
        if self.image_file:
            return f"/media/profile_pics/{self.image_file}"		# save user pics here
        return "/static/profile_pics/default.jpg"


# Post model for the database - represents a blog post in the system
class Post (DBBase):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),		# links posts to users table - user_id is a foreign key that references the id column in the users table
        nullable=False,				# user_id cannot be null - every post must have an author
        index=True,					# index the foreign key column for faster lookups
    )
    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

	# many-to-one relationship: many posts can have the same author, but each post has only one author
    author: Mapped[User] = relationship(back_populates="posts")


	