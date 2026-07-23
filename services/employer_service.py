import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from common.logger import logger
from common import shared
from core.config import BASE_URL
from services.utils import paginate_query
from models.test import Test
from models.question import Question
from models.assignment import TestAssignment, AssignmentStatusEnum
from models.submission import Submission
from services.retrieve_service import get_test_by_id



async def create_test(
    db: AsyncSession,
    employer_id: uuid.UUID,
    title: str,
    duration_minutes: int,
    questions_data: list[dict[str, Any]],
    pass_score: Optional[int] = None,
) -> Test:
    """
    Create a new technical test for an employer.

    Args:
        db (AsyncSession): Database session.
        employer_id (uuid.UUID): Employer User ID.
        title (str): Test title.
        duration_minutes (int): Allowed test time in minutes.
        questions_data (list[dict]): Initial questions to add to the test.
        pass_score (Optional[int]): Minimum passing score, or None if optional.

    Returns:
        Test: Created Test instance.

    """
    test = Test(
        created_by_id=employer_id,
        title=title,
        pass_score=pass_score,
        duration_minutes=duration_minutes,
    )

    db.add(test)
    await db.flush()

    for q in questions_data:
        question = Question(
            test_id=test.id,
            type=q["type"],
            content=q["content"],
            options=q.get("options"),
            test_cases=q.get("test_cases"),
            correct_answer=q["correct_answer"],
            points=q["points"],
        )
        db.add(question)

    await db.flush()
    await db.refresh(test)
    logger.info(f"Test created successfully: ID {test.id}, Title: '{test.title}' by Employer {employer_id}")
    return test


async def delete_test(db: AsyncSession, test_id: int, employer_id: uuid.UUID) -> bool:
    """
    Delete a test owned by an employer.

    Args:
        db (AsyncSession): Database session.
        test_id (int): Test ID to delete.
        employer_id (uuid.UUID): Employer User ID.

    Returns:
        bool: True on success.
    """
    async with db.begin():
        test = await get_test_by_id(db, test_id, employer_id)

        if test.deleted:
            logger.info(f"Test ID {test_id} was already deleted by Employer {employer_id}")
            return True

        test.deleted = True

        stmt = select(TestAssignment).where(TestAssignment.test_id == test.id)
        result = await db.execute(stmt)
        assignments = result.scalars().all()

        for assignment in assignments:
            if shared.redis_client:
                try:
                    await shared.redis_client.delete(f"active_assignment:{test.id}:{assignment.candidate_email}")
                except Exception:
                    logger.exception(f"Failed to clear redis assignment cache for assignment {assignment.id}")

            await db.delete(assignment)

    logger.info(f"Test ID {test_id} deactivated by Employer {employer_id}")
    return True


async def update_test_questions(
    db: AsyncSession,
    test_id: int,
    employer_id: uuid.UUID,
    questions_data: list[dict[str, Any]],
) -> list[Question]:
    """
    Update/overwrite all questions for a test, delegating checks to the database constraints.

    Args:
        db (AsyncSession): Database session.
        test_id (int): Target test ID.
        employer_id (uuid.UUID): Employer User ID.
        questions_data (list[dict]): Question payload dicts.

    Returns:
        list[Question]: The updated Question instances.
    """
    test = await get_test_by_id(db, test_id, employer_id)

    new_questions = []
    for q in questions_data:
        question = Question(
            test_id=test.id,
            type=q["type"],
            content=q["content"],
            options=q.get("options"),
            test_cases=q.get("test_cases"),
            correct_answer=q["correct_answer"],
            points=q["points"],
        )
        new_questions.append(question)

    test.questions = new_questions
    db.add(test)
    await db.flush()

    logger.info(f"Updated questions for Test ID {test_id}. New count: {len(new_questions)}")
    return new_questions



async def assign_test_to_candidate(
    db: AsyncSession,
    test_id: int,
    employer_id: uuid.UUID,
    candidate_email: str,
    expires_in_hours: float = 48,
) -> tuple[TestAssignment, str]:
    """
    Assign a test to a candidate email.

    Args:
        db (AsyncSession): Database session.
        test_id (int): Test ID.
        employer_id (uuid.UUID): Employer User ID.
        candidate_email (str): Candidate email address.
        expires_in_hours (int, optional): Expiration hours. Defaults to 48.

    Returns:
        tuple[TestAssignment, str]: Created TestAssignment instance and Test Title.
    """
    redis_key = f"active_assignment:{test_id}:{candidate_email}"
    if shared.redis_client:
        active = await shared.redis_client.get(redis_key)
        if active:
            raise HTTPException(status_code=400,detail="Test is already assigned to this candidate")

    test = await get_test_by_id(db, test_id, employer_id)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

    assignment = TestAssignment(
        test_id=test.id,
        candidate_email=candidate_email,
        unique_token=token,
        status=AssignmentStatusEnum.PENDING,
        expires_at=expires_at,
    )

    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)

    ttl = max(1, int(expires_in_hours * 3600))
    await shared.redis_client.setex(redis_key, ttl, token)

    logger.info(f"Candidate {candidate_email} has been assigned the technical test: {test.title}")
    return assignment, test.title



async def get_test_submissions(
    db: AsyncSession,
    test_id: int,
    employer_id: uuid.UUID,
    start: int = 0,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Retrieve a paginated list of submissions for a test owned by an employer.

    Args:
        db (AsyncSession): Database session.
        test_id (int): Test ID.
        employer_id (uuid.UUID): Employer User ID.
        start (int, optional): Starting offset index. Defaults to 0.
        limit (int, optional): Maximum items to return. Defaults to 10.

    Returns:
        dict[str, Any]: Dictionary containing total_count and items summary.
    """
    test = await get_test_by_id(db, test_id, employer_id)

    stmt = (
        select(Submission)
        .join(TestAssignment)
        .where(TestAssignment.test_id == test.id)
        .options(selectinload(Submission.assignment))
        .order_by(Submission.submitted_at.desc())
    )

    paginated_res = await paginate_query(db, stmt, start=start, limit=limit)
    raw_submissions: list[Submission] = paginated_res["items"]

    summary_items = []
    for sub in raw_submissions:
        summary_items.append({
            "submission_id": str(sub.id),
            "candidate_email": sub.candidate_email,
            "score": sub.score,
            "is_passed": sub.is_passed,
            "submitted_at": sub.submitted_at,
        })

    logger.info(f"Retrieved submissions for Test ID {test_id} offset {start}, limit {limit} (Total: {paginated_res['total_count']})")
    return {
        "total_count": paginated_res["total_count"],
        "items": summary_items
    }
