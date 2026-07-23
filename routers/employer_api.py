import uuid
from fastapi import APIRouter, Depends, Query, status, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, field_validator
from typing import Literal

from common.api_response import generate_response, generate_error_response
from common.logger import logger
from core.database import get_db
from core.auth import require_role, User
from services.retrieve_service import get_test_by_id, get_submission_by_id, get_all_tests
from services.employer_service import (
    assign_test_to_candidate,
    create_test,
    delete_test,
    get_test_submissions,
    update_test_questions,
)
from services.email_service import send_mock_email
from core.config import BASE_URL


class QuestionPayload(BaseModel):
    type: Literal["MCQ", "CODING"]
    content: str = Field(..., min_length=10)
    correct_answer: str = Field(..., min_length=1)
    points: int = Field(..., ge=1)
    options: dict | None = None
    test_cases: dict | None = None

    class Config:
        extra = "forbid"


class CreateTestRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    duration_minutes: int = Field(..., ge=1, le=300)
    pass_score: int | None = Field(None, ge=0)
    questions: list[QuestionPayload] = Field(..., min_length=1)

    class Config:
        extra = "forbid"


class UpdateQuestionsRequest(BaseModel):
    questions: list[QuestionPayload] = Field(..., min_length=1)

    class Config:
        extra = "forbid"

class AssignTestRequest(BaseModel):
    test_id: int
    candidate_email: str
    expires_in_hours: float = Field(48, gt=0, le=168)

    @field_validator("candidate_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email_clean = v.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise ValueError("Invalid candidate email address")
        return email_clean

    class Config:
        extra = "forbid"

router = APIRouter(prefix="/api/v1/employer", tags=["Employer"])


@router.post("/tests/create")
async def create_candidate_test(
    request: CreateTestRequest,
    current_user: User = Depends(require_role(["EMPLOYER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new technical test by employer.
    """
    try:
        test = await create_test(
            db=db,
            employer_id=current_user.user_id,
            title=request.title,
            duration_minutes=request.duration_minutes,
            pass_score=request.pass_score,
            questions_data=[q.model_dump() for q in request.questions]
        )
        return generate_response(
            entity={
                "id": test.id,
                "title": test.title,
                "duration_minutes": test.duration_minutes,
                "pass_score": test.pass_score,
            },
            message="Test created successfully"
        )
    except Exception as e:
        logger.exception("An unexpected error occurred creating test.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not create test due to a server error"
        )



@router.post("/tests/assign")
async def assign_test(
    request: AssignTestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["EMPLOYER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign a test to a candidate email and schedule email sending in the background.
    """
    try:
        assignment, test_title = await assign_test_to_candidate(
            db=db,
            test_id=request.test_id,
            employer_id=current_user.user_id,
            candidate_email=request.candidate_email,
            expires_in_hours=request.expires_in_hours
        )

        access_link = f"{BASE_URL}/assessment/take?token={assignment.unique_token}"
        background_tasks.add_task(
            send_mock_email,
            candidate_email=assignment.candidate_email,
            test_title=test_title,
            access_link=access_link,
            expires_at=assignment.expires_at
        )

        return generate_response(
            entity={
                "id": str(assignment.id),
                "test_id": assignment.test_id,
                "candidate_email": assignment.candidate_email,
                "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None,
                "status": assignment.status,
                "token": assignment.unique_token
            },
            message="Test assigned successfully"
        )
    except HTTPException as e:
        logger.exception(f"Cannot assign test {request.test_id} to candidate {request.candidate_email}.")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred assigning test {request.test_id}.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not assign test due to a server error"
        )


@router.get("/tests")
async def fetch_employer_tests(
    start: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_role(["EMPLOYER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a paginated lightweight list of tests created by the authenticated employer.
    """
    try:
        data = await get_all_tests(
            db=db,
            employer_id=current_user.user_id,
            start=start,
            limit=limit
        )
        return generate_response(entity=data, message="Employer tests retrieved successfully")
    except Exception as e:
        logger.exception("An unexpected error occurred while fetching employer tests.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve tests due to a server error"
        )


@router.get("/tests/{test_id}")
async def fetch_test_for_employer(
    test_id: int,
    current_user: User = Depends(require_role(["EMPLOYER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve full details for a single test created by the employer.
    """
    try:
        test = await get_test_by_id(db=db, test_id=test_id, user_id=current_user.user_id)
        return generate_response(entity=test, message="Test retrieved successfully")
    except HTTPException as e:
        logger.exception(f"Cannot retrieve test {test_id} for employer {current_user.user_id}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred retrieving test {test_id}")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve test due to a server error"
        )


@router.get("/tests/{test_id}/submissions")
async def fetch_test_submissions_for_employer(
    test_id: int,
    start: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_role(["EMPLOYER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve paginated submission records for a specific test owned by the employer.
    """
    try:
        submissions = await get_test_submissions(
            db=db,
            test_id=test_id,
            employer_id=current_user.user_id,
            start=start,
            limit=limit,
        )
        return generate_response(entity=submissions, message="Test submissions retrieved successfully")
    except HTTPException as e:
        logger.exception(f"Cannot retrieve submissions for test {test_id} for employer {current_user.user_id}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred retrieving submissions for test {test_id}.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve test submissions due to a server error"
        )


@router.get("/submissions/{submission_id}")
async def fetch_submission_for_employer(
    submission_id: uuid.UUID,
    current_user: User = Depends(require_role(["EMPLOYER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve candidate submission details for a test created by the employer.
    """
    try:
        submission = await get_submission_by_id(
            db=db,
            submission_id=submission_id,
            user_id=current_user.user_id
        )
        return generate_response(entity=submission, message="Submission retrieved successfully")
    except HTTPException as e:
        logger.exception(f"Cannot retrieve submission {submission_id} for employer {current_user.user_id}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred retrieving submission {submission_id}.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve submission due to a server error"
        )



@router.patch("/tests/{test_id}/questions")
async def update_employer_test_questions(
    test_id: int,
    request: UpdateQuestionsRequest,
    current_user: User = Depends(require_role(["EMPLOYER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Overwrite all questions for an existing test
    """
    try:
        questions = await update_test_questions(
            db=db,
            test_id=test_id,
            employer_id=current_user.user_id,
            questions_data=[q.model_dump() for q in request.questions],
        )
        return generate_response(
            entity={"test_id": test_id, "count": len(questions)},
            message="Test questions updated successfully"
        )
    except HTTPException as e:
        logger.exception(f"Cannot update questions for test {test_id} for employer {current_user.user_id}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred updating questions for test {test_id}.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not update questions due to a server error"
        )


@router.delete("/tests/{test_id}")
async def delete_employer_test(
    test_id: int,
    current_user: User = Depends(require_role(["EMPLOYER"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a test.
    """
    try:
        await delete_test(db=db, test_id=test_id, employer_id=current_user.user_id)
        return generate_response(entity=None, message=f"Test {test_id} deleted successfully")

    except HTTPException as e:
        logger.exception(f"Cannot delete test {test_id} for employer {current_user.user_id}")
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred deleting test {test_id}.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not delete test due to a server error"
        )
