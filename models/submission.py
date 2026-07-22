from models.common import *

class Submission(Base):
    __tablename__ = "submissions"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Optional[uuid.UUID] = Column(UUID(as_uuid=True), ForeignKey("test_assignments.id"), unique=True, nullable=True)
    candidate_email: str = Column(String(255), nullable=False)
    score: int = Column(Integer, nullable=False)
    is_passed: bool = Column(Boolean, nullable=False, default=False)
    answers: dict[str, Any] = Column(JSONB, nullable=False)
    submission_breakdown: dict[str, Any] = Column(JSONB, nullable=False)
    submitted_at: dt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("score >= 0", name="check_score_positive"),
    )

    assignment = relationship("TestAssignment", back_populates="submission")

    def __init__(
        self,
        *,
        assignment_id: Optional[uuid.UUID],
        candidate_email: str,
        score: int,
        answers: dict[str, Any],
        submission_breakdown: dict[str, Any],
        is_passed: bool = False,
        id: Optional[uuid.UUID] = None,
        submitted_at: Optional[dt] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            assignment_id=assignment_id,
            candidate_email=candidate_email,
            score=score,
            answers=answers,
            submission_breakdown=submission_breakdown,
            is_passed=is_passed,
            id=id,
            submitted_at=submitted_at,
            **kwargs,
        )
