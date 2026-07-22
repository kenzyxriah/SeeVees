from models.common import *

class Telemetry(Base):
    __tablename__ = "telemetry"

    token: str = Column(String(255), primary_key=True)
    candidate_email: str = Column(String(255), nullable=False)
    answers: Optional[dict[str, Any]] = Column(JSONB, nullable=True)
    is_banned: bool = Column(Boolean, nullable=False, default=False)
    created_at: dt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: dt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(
        self,
        *,
        token: str,
        candidate_email: str,
        answers: Optional[dict[str, Any]] = None,
        is_banned: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            token=token,
            candidate_email=candidate_email,
            answers=answers,
            is_banned=is_banned,
            **kwargs,
        )
