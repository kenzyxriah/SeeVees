import uuid
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from common.logger import logger
from services.utils import paginate_query
from models.test import Test
from models.submission import Submission
from models.assignment import TestAssignment


async def get_test_by_id(
    db: AsyncSession,
    test_id: int,
    user_id: Optional[uuid.UUID] = None,
) -> Test:
    """
    Retrieve full details for a single test including its questions.

    Args:
        db (AsyncSession): Database session.
        test_id (int): Primary key test ID.
        user_id (Optional[uuid.UUID]): Optional user ID (Employer or Candidate) to validate access.

    Returns:
        Test: Full Test model instance with questions loaded.

    Raises:
        KeyError: If test is not found.
        PermissionError: If user_id is provided and user is neither the creator nor an assigned candidate.
    """
    stmt = (
        select(Test)
        .where(Test.id == test_id)
        .where(Test.deleted.is_(False))
        .options(
            selectinload(Test.questions),
            selectinload(Test.assignments),
        )
    )
    result = await db.execute(stmt)
    test = result.scalar_one_or_none()

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    if user_id is not None:
        if test.created_by_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You are not the creator of this test"
            )

    logger.info(f"Test ID {test_id} retrieved successfully")
    return test


async def get_all_tests(
    db: AsyncSession,
    employer_id: Optional[uuid.UUID] = None,
    start: int = 0,
    limit: int = 30,
) -> dict[str, Any]:
    """
    Retrieve a paginated lightweight list of technical tests across the platform or filtered by employer.

    Args:
        db (AsyncSession): Database session.
        employer_id (Optional[uuid.UUID]): Optional employer ID to filter tests created by them.
        start (int, optional): Starting offset index. Defaults to 0.
        limit (int, optional): Maximum items to return. Defaults to 30.

    Returns:
        dict[str, Any]: Dictionary containing total_count and items summary.
    """
    stmt = select(Test).options(selectinload(Test.questions)).order_by(Test.created_at.desc())
    stmt = stmt.where(Test.deleted.is_(False))

    if employer_id is not None:
        stmt = stmt.where(Test.created_by_id == employer_id)

    paginated_res = await paginate_query(db, stmt, start=start, limit=limit)
    raw_tests: list[Test] = paginated_res["items"]

    summary_items = []
    for test in raw_tests:
        summary_items.append({
            "id": test.id,
            "title": test.title,
            "pass_score": test.pass_score,
            "duration_minutes": test.duration_minutes,
            "created_by_id": str(test.created_by_id),
            "question_count": len(test.questions),
            "created_at": test.created_at,
        })

    logger.info(f"Retrieved tests offset {start}, limit {limit} (Total: {paginated_res['total_count']})")

    return {
        "total_count": paginated_res["total_count"],
        "items": summary_items,
    }


async def get_all_submissions(
    db: AsyncSession,
    employer_id: Optional[uuid.UUID] = None,
    start: int = 0,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Retrieve a paginated list of candidate submissions across the platform or filtered by employer.

    Args:
        db (AsyncSession): Database session.
        employer_id (Optional[uuid.UUID]): Optional employer ID to filter submissions for their tests.
        start (int, optional): Starting offset index. Defaults to 0.
        limit (int, optional): Maximum items to return. Defaults to 10.

    Returns:
        dict[str, Any]: Dictionary containing total_count and items summary.
    """
    stmt = (
        select(Submission)
        .join(Submission.assignment)
        .join(TestAssignment.test)
        .options(
            selectinload(Submission.assignment).selectinload(TestAssignment.test),
        )
        .order_by(Submission.submitted_at.desc())
    )

    if employer_id is not None:
        stmt = stmt.where(Test.created_by_id == employer_id)

    paginated_res = await paginate_query(db, stmt, start=start, limit=limit)
    raw_submissions: list[Submission] = paginated_res["items"]

    summary_items = []
    for sub in raw_submissions:
        assignment = sub.assignment
        summary_items.append({
            "submission_id": str(sub.id),
            "assignment_id": str(sub.assignment_id) if sub.assignment_id else None,
            "test_id": assignment.test_id if assignment is not None else None,
            "candidate_email": sub.candidate_email,
            "score": sub.score,
            "is_passed": sub.is_passed,
            "submitted_at": sub.submitted_at,
        })

    logger.info(f"Retrieved submissions offset {start}, limit {limit} (Total: {paginated_res['total_count']})")

    return {
        "total_count": paginated_res["total_count"],
        "items": summary_items,
    }


async def get_submission_by_id(
    db: AsyncSession,
    submission_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
) -> Submission:
    """
    Retrieve full details and answers for a single submission.

    Args:
        db (AsyncSession): Database session.
        submission_id (uuid.UUID): Primary key submission ID.
        user_id (Optional[uuid.UUID]): Optional user ID (Employer or Candidate) for ownership validation.

    Returns:
        Submission: Full Submission model instance including assignment and test details.

    Raises:
        KeyError: If submission is not found.
        PermissionError: If user_id is provided and matches neither candidate nor test creator.
    """
    stmt = (
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.assignment).selectinload(TestAssignment.test),
        )
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if user_id is not None:
        is_employer = submission.assignment and submission.assignment.test and submission.assignment.test.created_by_id == user_id
        if not is_employer:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You are not authorized to view this submission"
            )

    logger.info(f"Submission {submission_id} retrieved successfully")
    return submission

