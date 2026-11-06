from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuizOptionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_correct: bool = False


class QuizQuestionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    points: float = Field(default=1.0, ge=0.1)
    options: list[QuizOptionCreate] = Field(..., min_length=2)


class QuizCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(None, max_length=2000)
    time_limit_minutes: int = Field(default=30, ge=1, le=300)
    max_attempts: int = Field(default=1, ge=1, le=10)
    questions: list[QuizQuestionCreate] = Field(..., min_length=1)


class QuizOptionStudentOut(BaseModel):
    # LƯU Ý BẢO MẬT: Tuyệt đối không trả về is_correct cho sinh viên khi làm bài!
    id: int
    content: str

    model_config = ConfigDict(from_attributes=True)


class QuizQuestionStudentOut(BaseModel):
    id: int
    content: str
    points: float
    options: list[QuizOptionStudentOut]

    model_config = ConfigDict(from_attributes=True)


class QuizStudentDetailOut(BaseModel):
    id: int
    course_id: int
    title: str
    description: str | None = None
    time_limit_minutes: int
    max_attempts: int
    questions: list[QuizQuestionStudentOut]

    model_config = ConfigDict(from_attributes=True)


class QuizSubmitAnswer(BaseModel):
    question_id: int
    selected_option_id: int | None = None


class QuizSubmitRequest(BaseModel):
    answers: list[QuizSubmitAnswer]


class QuizAttemptResponse(BaseModel):
    id: int
    quiz_id: int
    attempt_number: int
    score: float
    max_score: float
    started_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
