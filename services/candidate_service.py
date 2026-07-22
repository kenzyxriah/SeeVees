from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid, json

from common.logger import logger
from models.assignment import TestAssignment, AssignmentStatusEnum
from models.submission import Submission
from models.telemetry import Telemetry
from models.test import Test
from services.grading_service import grade_submission
from common import shared


async def check_telemetry(db: AsyncSession, token: str) -> Optional[Telemetry]:
    """
    Check if a telemetry record exists for a token and verify its ban status.

    Args:
        db (AsyncSession): Active database session.
        token (str): Unique candidate assignment access token.

    Returns:
        Optional[Telemetry]: Telemetry model instance if it exists and is not banned.

    Raises:
        HTTPException 400: If the token has been banned (e.g. after submission).
    """
    telemetry_stmt = select(Telemetry).where(Telemetry.token == token)
    telemetry_res = await db.execute(telemetry_stmt)
    telemetry_record = telemetry_res.scalar_one_or_none()
    if telemetry_record and telemetry_record.is_banned:
        raise HTTPException(status_code=400, detail="This token has been banned from assessment system.")
    return telemetry_record


async def ban_telemetry_token(db: AsyncSession, token: str, candidate_email: str) -> None:
    """
    Lock the telemetry record, clear current draft progress, and set ban status to True.
    This effectively prevents further draft saving and quiz re-entries.

    Args:
        db (AsyncSession): Active database session.
        token (str): Unique candidate assignment access token.
        candidate_email (str): The candidate's email address.
    """
    telemetry_stmt = select(Telemetry).where(Telemetry.token == token).with_for_update()
    telemetry_res = await db.execute(telemetry_stmt)
    telemetry_record = telemetry_res.scalar_one_or_none()

    if telemetry_record and not telemetry_record.is_banned:
        telemetry_record.answers = None
        telemetry_record.is_banned = True



async def get_assessment_instructions(db: AsyncSession, token: str) -> dict[str, Any]:
    """
    Retrieve assessment details (title, duration, candidate information) before the test starts.
    Does not transition assignment status or initialize countdown session.

    Args:
        db (AsyncSession): Active database session.
        token (str): Unique candidate assignment access token.

    Returns:
        dict[str, Any]: Assessment metadata payload:
            - token (str): Unique access token.
            - title (str): Test title.
            - duration_minutes (int): Allowed test duration.
            - candidate_email (str): Registered candidate email address.
            - expires_at (datetime): Overall token expiration deadline.
            - status (AssignmentStatusEnum): Current status.

    Raises:
        HTTPException 404: If token is invalid.
        HTTPException 400: If assessment is expired or already submitted.
    """
    stmt = (
        select(TestAssignment)
        .where(TestAssignment.unique_token == token)
        .options(selectinload(TestAssignment.test))
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Invalid assessment token")

    if assignment.expires_at < datetime.now(timezone.utc):
        assignment.status = AssignmentStatusEnum.EXPIRED
        await db.flush()
        raise HTTPException(status_code=400, detail="Assessment link has expired")

    if assignment.status == AssignmentStatusEnum.SUBMITTED:
        raise HTTPException(status_code=400, detail="This assessment has already been submitted")

    test = assignment.test
    return {
        "token": token,
        "title": test.title,
        "duration_minutes": test.duration_minutes,
        "candidate_email": assignment.candidate_email,
        "expires_at": assignment.expires_at,
        "status": assignment.status,
    }


async def get_assigned_test_by_token(db: AsyncSession, token: str) -> dict[str, Any]:
    """
    Retrieve questions and setup/calculate countdown session for a test by token.
    Transitions status to STARTED if it is currently PENDING.

    Args:
        db (AsyncSession): Active database session.
        token (str): Unique candidate assignment access token.

    Returns:
        dict[str, Any]: Assessment payload including questions, remaining time, and draft answers:
            - token (str): Unique access token.
            - assignment_id (str): Assignment ID.
            - test_id (int): Test ID.
            - title (str): Test title.
            - duration_minutes (int): Allowed test duration.
            - remaining_seconds (int): Computed remaining time.
            - draft_answers (dict): Eagerly loaded draft answers from Telemetry.
            - questions (list[dict]): Questions sanitized without correct answers.
            - expires_at (datetime): Overall token expiration deadline.

    Raises:
        HTTPException 404: If token is invalid.
        HTTPException 400: If token is banned, expired, or already submitted.
    """
    stmt = (
        select(TestAssignment)
        .where(TestAssignment.unique_token == token)
        .options(selectinload(TestAssignment.test).selectinload(Test.questions))
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(status_code=404, detail="Invalid assessment token")

    if assignment.expires_at < datetime.now(timezone.utc):
        assignment.status = AssignmentStatusEnum.EXPIRED
        await db.flush()
        raise HTTPException(status_code=400, detail="Assessment link has expired")

    if assignment.status == AssignmentStatusEnum.SUBMITTED:
        raise HTTPException(status_code=400, detail="This assessment has already been submitted")

    if assignment.status == AssignmentStatusEnum.PENDING:
        assignment.status = AssignmentStatusEnum.STARTED
        await db.flush()

    test = assignment.test
    duration_secs = test.duration_minutes * 60
    redis_key = f"active_session:{token}"
    remaining_seconds = duration_secs

    try:
        cached_session = await shared.redis_client.get(redis_key)
        if cached_session:
            session_data = json.loads(cached_session)
            start_time = datetime.fromisoformat(session_data["start_time"])
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            remaining_seconds = max(0, int(duration_secs - elapsed))
        else:
            session_payload = {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "candidate_email": assignment.candidate_email
            }
            ttl = duration_secs + 30
            await shared.redis_client.set(redis_key, json.dumps(session_payload), ex=int(ttl))
    except Exception:
        logger.exception(f"Failed to manage Redis timer session for token {token}")

    telemetry_record = await check_telemetry(db, token)
    draft_answers = telemetry_record.answers if telemetry_record and telemetry_record.answers else {}

    safe_questions = []
    for q in test.questions:
        safe_questions.append({
            "id": str(q.id),
            "type": q.type,
            "content": q.content,
            "options": q.options,
            "test_cases": q.test_cases,
            "points": q.points,
        })

    return {
        "token": token,
        "assignment_id": str(assignment.id),
        "test_id": test.id,
        "title": test.title,
        "duration_minutes": test.duration_minutes,
        "remaining_seconds": remaining_seconds,
        "draft_answers": draft_answers,
        "questions": safe_questions,
        "expires_at": assignment.expires_at,
    }


async def save_assessment_draft(
    db: AsyncSession,
    token: str,
    answers: dict[str, Any],
) -> None:
    """
    Save candidate's active quiz progress to the Telemetry database table.
    Bypasses overall assignment validation to accept fast progress saving.

    Args:
        db (AsyncSession): Active database session.
        token (str): Unique candidate assignment access token.
        answers (dict[str, Any]): Dictionary containing current draft answers.
    """
    telemetry_record = await check_telemetry(db, token)

    if not telemetry_record:
        stmt = select(TestAssignment).where(TestAssignment.unique_token == token)
        result = await db.execute(stmt)
        assignment = result.scalar_one_or_none()
        email = assignment.candidate_email 

        telemetry_record = Telemetry(
            token=token,
            candidate_email=email,
            is_banned=False
        )
        db.add(telemetry_record)
    else:
        telemetry_record.answers = answers

    await db.flush()


async def submit_test_answers(
    db: AsyncSession,
    token: str,
    answers: dict[str, Any],
) -> tuple[Submission, str]:
    """
    Grade and record test submission. Updates assignment status and bans telemetry token.

    Args:
        db (AsyncSession): Active database session.
        token (str): Unique candidate assignment access token.
        answers (dict[str, Any]): Candidate answers mapping question_id string to response.

    Returns:
        Submission: Created Submission database model instance.

    Raises:
        HTTPException 404: If token is invalid.
        HTTPException 400: If assessment is expired or already submitted.
    """
    async with db.begin():
        stmt = (
            select(TestAssignment)
            .where(TestAssignment.unique_token == token)
            .options(selectinload(TestAssignment.test).selectinload(Test.questions))
            .with_for_update()
        )
        result = await db.execute(stmt)
        assignment = result.scalar_one_or_none()

        if not assignment:
            raise HTTPException(status_code=404, detail="Invalid assessment token")

        if assignment.status == AssignmentStatusEnum.SUBMITTED:
            logger.warning(
                f"Invalid. Multiple submission attempt for Token: {token}, Candidate Email: {assignment.candidate_email}"
            )
            raise HTTPException(
                status_code=400,
                detail="Assessment has already been submitted. Multiple submissions are prohibited."
            )

        if assignment.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Assessment link has expired")

        total_score, is_passed, breakdown = await grade_submission(
            questions=assignment.test.questions,
            candidate_answers=answers,
            pass_score=assignment.test.pass_score,
        )

        submission = Submission(
            assignment_id=assignment.id,
            candidate_email=assignment.candidate_email,
            score=total_score,
            is_passed=is_passed,
            answers=answers,
            submission_breakdown=breakdown,
        )

        await ban_telemetry_token(db, token, assignment.candidate_email)

        db.add(submission)
        await db.flush()
        assignment.status = AssignmentStatusEnum.SUBMITTED

    await db.refresh(submission)

    logger.info(
        f"Test submitted successfully. Candidate: {assignment.candidate_email}, Score: {total_score}, Passed: {is_passed}"
    )

    return submission, assignment.test.title


async def get_candidate_submission_result(
    db: AsyncSession,
    submission_id: uuid.UUID,
) -> Submission:
    """
    Retrieve submission result and score breakdown by submission ID.

    Args:
        db (AsyncSession): Active database session.
        submission_id (uuid.UUID): Submission UUID.

    Returns:
        Submission: The requested Submission model.

    Raises:
        HTTPException 404: If submission is not found.
    """
    stmt = (
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.assignment).selectinload(TestAssignment.test))
    )
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    logger.info(
        f"Submission result retrieved successfully. Candidate: {submission.candidate_email}, "
        f"Score: {submission.score}, Passed: {submission.is_passed}"
    )
    return submission
