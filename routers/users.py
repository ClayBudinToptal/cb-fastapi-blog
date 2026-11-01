#
# Router for Users
#

# only need imports that pertain to Users
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import PostResponse, UserCreate, UserResponse, UserUpdate

# create Router
router = APIRouter()

# only move /api/ routes here from main.py
# leave template-based web-served pages in main.py



