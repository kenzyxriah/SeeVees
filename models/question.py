from models.common import *

class QuestionTypeEnum(str, enum.Enum):
    MCQ = "MCQ"
    CODING = "CODING"


class Question(Base):
    __tablename__ = "questions"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id: int = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    type: QuestionTypeEnum = Column(SQLEnum(QuestionTypeEnum), nullable=False)
    content: str = Column(Text, nullable=False)
    options: Optional[dict[str, Any]] = Column(JSONB, nullable=True)
    test_cases: Optional[dict[str, Any]] = Column(JSONB, nullable=True)
    correct_answer: str = Column(Text, nullable=False)
    points: int = Column(Integer, nullable=False)
    created_at: dt= Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("points > 0", name="check_points_positive"),
        CheckConstraint("length(trim(content)) > 10", name="check_content_okay"),
        CheckConstraint("length(trim(correct_answer)) > 0", name="check_correct_answer_not_empty"),
    )

    test = relationship("Test", back_populates="questions")

    def __init__(
        self,
        *,
        test_id: int,
        type: QuestionTypeEnum,
        content: str,
        correct_answer: str,
        points: int,
        options: Optional[dict[str, Any]] = None,
        test_cases: Optional[dict[str, Any]] = None,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[dt] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            test_id=test_id,
            type=type,
            content=content,
            correct_answer=correct_answer,
            points=points,
            options=options,
            test_cases=test_cases,
            id=id,
            created_at=created_at,
            **kwargs,
        )

