from typing import Any, Optional
from common.logger import logger
from models.question import Question, QuestionTypeEnum


async def grade_submission(
    questions: list[Question],
    candidate_answers: dict[str, Any],
    pass_score: Optional[int] = None,
) -> tuple[int, bool, dict[str, Any]]:
    """
    Auto-grade MCQ and Coding questions for a candidate test submission.

    Iterates through each test question, evaluates candidate answers against correct options or expected outputs,
    accumulates earned points, and determines whether the total score meets or exceeds the test passing threshold.

    Args:
        questions (list[Question]): List of Question models attached to the test.
        candidate_answers (dict[str, Any]): Dictionary mapping question_id string to the candidate's answer.
        pass_score (Optional[int]): Minimum passing score threshold required for the test, or None.

    Returns:
        tuple[int, bool, dict[str, Any]]: A 3-element tuple containing:
            - total_score (int): Total points earned across all questions.
            - is_passed (bool): True if total_score >= pass_score or if no pass_score is set.
            - breakdown (dict[str, Any]): Detailed question-by-question scoring summary.
    """
    total_score = 0
    max_possible_points = 0
    breakdown = {}

    for question in questions:
        q_id_str = str(question.id)
        max_possible_points += question.points
        answer = candidate_answers.get(q_id_str)

        is_correct = False
        points_earned = 0

        if answer is None:
            logger.info(f"Question {q_id_str} unanswered by candidate")

        elif str(answer).strip().lower() == str(question.correct_answer).strip().lower():
            is_correct = True
            points_earned = question.points

        total_score += points_earned
        breakdown[q_id_str] = {
            "type": question.type,
            "points_earned": points_earned,
            "points_possible": question.points,
            "is_correct": is_correct,
            "correct_answer": question.correct_answer
        }
     
    pass_check = pass_score is not None
    is_passed = (total_score >= pass_score) if pass_check else True
    logger.info(f"Grading complete. Total Score: {total_score}/{max_possible_points}")
    
    if pass_check:
        logger.info(f"Test passed: {is_passed}")
    else:
        logger.info("Test has no pass score set. Automatic success")
        
    return total_score, is_passed, breakdown
