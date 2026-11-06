from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: int
    topic_id: int
    author_id: int
    author_name: str | None = None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=1, max_length=10000)


class TopicUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=255)
    content: str | None = Field(None, min_length=1, max_length=10000)


class TopicResponse(BaseModel):
    id: int
    course_id: int
    author_id: int
    author_name: str | None = None
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    comments: list[CommentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=1, max_length=10000)


class AnnouncementResponse(BaseModel):
    id: int
    course_id: int
    author_id: int
    author_name: str | None = None
    title: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
