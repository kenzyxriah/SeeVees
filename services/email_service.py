from datetime import datetime
from common.logger import logger
from core.config import BASE_URL


def send_mock_email(candidate_email: str, test_title: str, access_link: str, expires_at: datetime):
    """
    Simulate sending an assessment invitation email.
    """
    logger.info(
        f"\n======================================================\n"
        f"[SIMULATED EMAIL SENT TO: {candidate_email}]\n"
        f"Subject: You have been assigned a technical test: {test_title}\n"
        f"Access Link: {access_link}\n"
        f"Expires At: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"======================================================\n"
    )


def send_submission_result_email(candidate_email: str, test_title: str, submission_id: str):
    """
    Simulate sending a submission result email containing a permanent link
    the candidate can use anytime to view their score and breakdown.

    Args:
        candidate_email (str): Candidate's email address.
        test_title (str): Title of the completed test.
        submission_id (str): UUID of the submission for the result link.
    """
    result_link = f"{BASE_URL}/assessment/result/{submission_id}"
    logger.info(
        f"\n======================================================\n"
        f"[SIMULATED EMAIL SENT TO: {candidate_email}]\n"
        f"Subject: Your results for: {test_title}\n"
        f"View your result anytime: {result_link}\n"
        f"======================================================\n"
    )
