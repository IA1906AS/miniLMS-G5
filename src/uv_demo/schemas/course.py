from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)


class CourseUpdate(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)


class CourseResponse(BaseModel):
    id: int
    code: str
    title: str
    description: str | None = None
    instructor_id: int
    instructor_name: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnrollmentCreate(BaseModel):
    course_code: str = Field(..., min_length=2, max_length=50)


class EnrollStudentByInstructor(BaseModel):
    student_email: EmailStr


class MaterialResponse(BaseModel):
    id: int
    course_id: int
    title: str
    filename: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
