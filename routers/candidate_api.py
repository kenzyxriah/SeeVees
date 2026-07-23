import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from common.api_response import generate_response, generate_error_response
from common.logger import logger
from core.database import get_db
from core.auth import verify_api_key
from core.limiter import limiter
from services.candidate_service import (
    get_assessment_instructions,
    get_assigned_test_by_token,
    save_assessment_draft,
    submit_test_answers,
    get_candidate_submission_result,
)
from services.email_service import send_submission_result_email


router = APIRouter(prefix="/api/v1/assessment", tags=["Assessment"])


class SubmitAnswersRequest(BaseModel):
    token: str = Field(..., min_length=1)
    answers: dict[str, str] = Field(..., min_length=1)

    class Config:
        extra = "forbid"


class SaveDraftRequest(BaseModel):
    token: str = Field(..., min_length=1)
    answers: dict[str, str] = Field(..., min_length=1)

    class Config:
        extra = "forbid"


class AssessmentRequest(BaseModel):
    token: str = Field(..., min_length=1)

    class Config:
        extra = "forbid"


@router.post("/instructions")
async def fetch_instructions(
    request: AssessmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve assessment details/metadata before the test starts.
    """
    try:
        data = await get_assessment_instructions(db=db, token=request.token)
        return generate_response(entity=data, message="Instructions retrieved successfully")
    except HTTPException as e:
        logger.exception(f"Failed to retrieve instructions for {request.token}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception("An unexpected error occurred retrieving instructions.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve instructions due to a server error"
        )


@router.post("/take")
async def take_assessment(
    request: AssessmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve an assigned test by unique access token.
    """
    try:
        test_data = await get_assigned_test_by_token(db=db, token=request.token)
        return generate_response(entity=test_data, message="Assessment retrieved successfully")
    except HTTPException as e:
        logger.exception(f"Failed to retrieve assessment for {request.token}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception("An unexpected error occurred retrieving assessment.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve assessment due to a server error"
        )


@router.post("/save-draft")
@limiter.limit("1/10 seconds")
async def save_draft(
    request: Request,
    payload: SaveDraftRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Save progress draft for questions.
    """
    try:
        await save_assessment_draft(token=payload.token, answers=payload.answers)
        return generate_response(entity=None, message="Draft saved successfully")
    except HTTPException as e:
        logger.exception(f"Failed to save draft for {payload.token}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception("An unexpected error occurred saving draft.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not save draft due to a server error"
        )


@router.post("/submit")
async def submit_assessment(
    request: SubmitAnswersRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit answers for an assigned test. The token identifies the assignment.
    On success, sends candidate a result link email in the background.
    """
    try:
        submission, test_title = await submit_test_answers(
            db=db,
            token=request.token,
            answers=request.answers,
        )

        background_tasks.add_task(
            send_submission_result_email,
            candidate_email=submission.candidate_email,
            test_title=test_title,
            submission_id=str(submission.id),
        )

        return generate_response(
            entity={
                "submission_id": str(submission.id),
                "score": submission.score,
                "is_passed": submission.is_passed,
                "submitted_at": submission.submitted_at,
            },
            message="Assessment submitted successfully"
        )
    except HTTPException as e:
        logger.exception(f"Failed to submit assessment for {request.token}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception("An unexpected error occurred submitting assessment.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not submit assessment due to a server error"
        )


@router.get("/result/{submission_id}")
async def get_assessment_result(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve submission result by submission ID.
    """
    try:
        submission = await get_candidate_submission_result(db=db, submission_id=submission_id)
        return generate_response(entity=submission, message="Submission result retrieved successfully")
    except HTTPException as e:
        logger.exception(f"Failed to retrieve submission result for {submission_id}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred retrieving result {submission_id}.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve result due to a server error"
        )
