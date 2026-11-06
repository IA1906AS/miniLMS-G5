from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=5000)
    deadline: datetime
    max_score: float = Field(default=10.0, ge=0.0, le=100.0)


class AssignmentResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: str | None = None
    deadline: datetime
    max_score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    student_name: str | None = None
    filename: str
    submitted_at: datetime
    score: float | None = None
    feedback: str | None = None
    graded_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GradeSubmissionRequest(BaseModel):
    score: float = Field(..., ge=0.0)
    feedback: str | None = Field(None, max_length=2000)
