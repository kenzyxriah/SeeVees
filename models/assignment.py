from models.common import *

class AssignmentStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"


class TestAssignment(Base):
    __tablename__ = "test_assignments"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id: int = Column(Integer, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    candidate_email: str = Column(String(255), index=True, nullable=False)
    unique_token: str = Column(String(255), unique=True, index=True, nullable=False)
    status: AssignmentStatusEnum = Column(SQLEnum(AssignmentStatusEnum), nullable=False, default=AssignmentStatusEnum.PENDING)
    expires_at: dt = Column(DateTime(timezone=True), nullable=False)
    created_at: dt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    test = relationship("Test", back_populates="assignments")
    submission = relationship("Submission", back_populates="assignment", uselist=False)

    def __init__(
        self,
        *,
        test_id: int,
        candidate_email: str,
        unique_token: str,
        expires_at: dt,
        status: AssignmentStatusEnum = AssignmentStatusEnum.PENDING,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[dt] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            test_id=test_id,
            candidate_email=candidate_email,
            unique_token=unique_token,
            expires_at=expires_at,
            status=status,
            id=id,
            created_at=created_at,
            **kwargs,
        )
