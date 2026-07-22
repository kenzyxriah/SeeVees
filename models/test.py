from models.common import *
from models.user import RoleEnum


class Test(Base):
    __tablename__ = "tests"

    id: int = Column(Integer, Identity(start=1), primary_key=True)
    created_by_id: uuid.UUID = Column(UUID(as_uuid=True), nullable=False)
    creator_role: RoleEnum = Column(SQLEnum(RoleEnum), nullable=False, default=RoleEnum.EMPLOYER)
    title: str = Column(String(255), nullable=False)
    pass_score: Optional[int] = Column(Integer, nullable=True)
    duration_minutes: int = Column(Integer, nullable=False)
    deleted: bool = Column(Boolean, nullable=False, default=False)
    created_at: dt= Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("pass_score IS NULL OR pass_score >= 0", name="check_pass_score_positive"),
        CheckConstraint("duration_minutes > 0", name="check_duration_positive"),
        CheckConstraint("creator_role = 'EMPLOYER'", name="check_test_creator_role"),
        ForeignKeyConstraint(
            ["created_by_id", "creator_role"],
            ["users.id", "users.role"],
            ondelete="CASCADE"
        ),
    )

    creator = relationship("User", back_populates="created_tests")
    questions = relationship("Question", back_populates="test", cascade="all, delete-orphan")
    assignments = relationship("TestAssignment", back_populates="test", cascade="all, delete-orphan")

    def __init__(
        self,
        *,
        created_by_id: uuid.UUID,
        title: str,
        duration_minutes: int,
        pass_score: Optional[int] = None,
        creator_role: RoleEnum = RoleEnum.EMPLOYER,
        deleted: bool = False,
        id: Optional[int] = None,
        created_at: Optional[dt] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            created_by_id=created_by_id,
            title=title,
            duration_minutes=duration_minutes,
            pass_score=pass_score,
            creator_role=creator_role,
            deleted=deleted,
            id=id,
            created_at=created_at,
            **kwargs,
        )

