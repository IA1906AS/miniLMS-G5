from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from uv_demo.database import get_db
from uv_demo.models.course import Course, Enrollment
from uv_demo.models.forum import Announcement, ForumComment, ForumTopic
from uv_demo.models.user import User, UserRole
from uv_demo.schemas.auth import MessageResponse
from uv_demo.schemas.forum import (
    AnnouncementCreate,
    AnnouncementResponse,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    TopicCreate,
    TopicResponse,
    TopicUpdate,
)
from uv_demo.security.audit import log_audit
from uv_demo.security.dependencies import (
    check_course_access,
    get_current_user,
    require_roles,
)
from uv_demo.services.email import email_service

router = APIRouter(tags=["6. Trao đổi và Thông báo"])


# ---------------- Diễn đàn (Forum) ----------------


@router.post(
    "/api/courses/{course_id}/topics",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_topic(
    course_id: int,
    req: TopicCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TopicResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    # Kiểm tra quyền truy cập khóa học
    check_course_access(course, current_user, db)

    topic = ForumTopic(
        course_id=course.id,
        author_id=current_user.id,
        title=req.title.strip(),
        content=req.content.strip(),
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)

    return TopicResponse(
        id=topic.id,
        course_id=topic.course_id,
        author_id=topic.author_id,
        author_name=current_user.full_name,
        title=topic.title,
        content=topic.content,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
        comments=[],
    )


@router.get("/api/courses/{course_id}/topics", response_model=list[TopicResponse])
def list_topics(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TopicResponse]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    check_course_access(course, current_user, db)

    topics = (
        db.query(ForumTopic)
        .filter(ForumTopic.course_id == course_id)
        .order_by(ForumTopic.created_at.desc())
        .all()
    )

    results: list[TopicResponse] = []
    for t in topics:
        comments_out = [
            CommentResponse(
                id=c.id,
                topic_id=c.topic_id,
                author_id=c.author_id,
                author_name=c.author.full_name if c.author else None,
                content=c.content,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in t.comments
        ]
        results.append(
            TopicResponse(
                id=t.id,
                course_id=t.course_id,
                author_id=t.author_id,
                author_name=t.author.full_name if t.author else None,
                title=t.title,
                content=t.content,
                created_at=t.created_at,
                updated_at=t.updated_at,
                comments=comments_out,
            )
        )
    return results


@router.put("/api/topics/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: int,
    req: TopicUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TopicResponse:
    topic = db.query(ForumTopic).filter(ForumTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chủ đề không tồn tại."
        )

    # BẢO VỆ CHIA QUYỀN: Người dùng chỉ được sửa bài viết của chính mình (hoặc QT)
    if current_user.role != UserRole.QT and topic.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền chỉnh sửa chủ đề của người khác.",
        )

    if req.title is not None:
        topic.title = req.title.strip()
    if req.content is not None:
        topic.content = req.content.strip()

    db.commit()
    db.refresh(topic)

    return TopicResponse(
        id=topic.id,
        course_id=topic.course_id,
        author_id=topic.author_id,
        author_name=topic.author.full_name if topic.author else None,
        title=topic.title,
        content=topic.content,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
        comments=[],
    )


@router.delete("/api/topics/{topic_id}", response_model=MessageResponse)
def delete_topic(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    topic = db.query(ForumTopic).filter(ForumTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chủ đề không tồn tại."
        )

    # BẢO VỆ CHIA QUYỀN: Người dùng chỉ được xóa bài của chính mình (hoặc QT)
    if current_user.role != UserRole.QT and topic.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xóa chủ đề của người khác.",
        )

    db.delete(topic)
    db.commit()
    return MessageResponse(message="Xóa chủ đề thành công.")


@router.post(
    "/api/topics/{topic_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    topic_id: int,
    req: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommentResponse:
    topic = db.query(ForumTopic).filter(ForumTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chủ đề không tồn tại."
        )

    course = db.query(Course).filter(Course.id == topic.course_id).first()
    if course:
        check_course_access(course, current_user, db)

    comment = ForumComment(
        topic_id=topic.id,
        author_id=current_user.id,
        content=req.content.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        topic_id=comment.topic_id,
        author_id=comment.author_id,
        author_name=current_user.full_name,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.put("/api/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    req: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommentResponse:
    comment = db.query(ForumComment).filter(ForumComment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bình luận không tồn tại."
        )

    # BẢO VỆ CHIA QUYỀN: Người dùng chỉ được sửa bình luận của chính mình (hoặc QT)
    if current_user.role != UserRole.QT and comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền chỉnh sửa bình luận của người khác.",
        )

    comment.content = req.content.strip()
    db.commit()
    db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        topic_id=comment.topic_id,
        author_id=comment.author_id,
        author_name=comment.author.full_name if comment.author else None,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.delete("/api/comments/{comment_id}", response_model=MessageResponse)
def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    comment = db.query(ForumComment).filter(ForumComment.id == comment_id).first()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bình luận không tồn tại."
        )

    if current_user.role != UserRole.QT and comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xóa bình luận của người khác.",
        )

    db.delete(comment)
    db.commit()
    return MessageResponse(message="Xóa bình luận thành công.")


# ---------------- Thông báo (Announcements) ----------------


@router.post(
    "/api/courses/{course_id}/announcements",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_announcement(
    course_id: int,
    req: AnnouncementCreate,
    current_user: User = Depends(require_roles(UserRole.GV, UserRole.QT)),
    db: Session = Depends(get_db),
) -> AnnouncementResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    if current_user.role == UserRole.GV and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ có thể đăng thông báo cho khóa học do mình phụ trách.",
        )

    announcement = Announcement(
        course_id=course.id,
        author_id=current_user.id,
        title=req.title.strip(),
        content=req.content.strip(),
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    # Gửi email thông báo tới toàn bộ sinh viên đã ghi danh
    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course.id).all()
    for en in enrollments:
        if en.student and en.student.email:
            email_service.send_announcement_email(
                to_email=en.student.email,
                course_title=course.title,
                title=announcement.title,
                content=announcement.content,
            )

    log_audit(
        db,
        action="CREATE_ANNOUNCEMENT",
        entity_type="ANNOUNCEMENT",
        user_id=current_user.id,
        entity_id=announcement.id,
        details=f"Đăng thông báo '{announcement.title}' trong khóa học {course.code}",
    )

    return AnnouncementResponse(
        id=announcement.id,
        course_id=announcement.course_id,
        author_id=announcement.author_id,
        author_name=current_user.full_name,
        title=announcement.title,
        content=announcement.content,
        created_at=announcement.created_at,
    )


@router.get(
    "/api/courses/{course_id}/announcements",
    response_model=list[AnnouncementResponse],
)
def list_announcements(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnnouncementResponse]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    check_course_access(course, current_user, db)

    announcements = (
        db.query(Announcement)
        .filter(Announcement.course_id == course_id)
        .order_by(Announcement.created_at.desc())
        .all()
    )
    return [
        AnnouncementResponse(
            id=a.id,
            course_id=a.course_id,
            author_id=a.author_id,
            author_name=a.author.full_name if a.author else None,
            title=a.title,
            content=a.content,
            created_at=a.created_at,
        )
        for a in announcements
    ]
