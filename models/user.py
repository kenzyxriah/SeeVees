from models.common import *

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    EMPLOYER = "EMPLOYER"


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("id", "role", name="uq_user_id_role"),
    )

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: str = Column(String(255), unique=True, index=True, nullable=False)
    password_hash: str = Column(String(255), nullable=False)
    username: Optional[str] = Column(String(100), unique=True, index=True, nullable=True)
    first_name: str = Column(String(100), nullable=False)
    last_name: str = Column(String(100), nullable=False)
    role: RoleEnum = Column(SQLEnum(RoleEnum), nullable=False)
    created_at: dt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    created_tests = relationship("Test", back_populates="creator", cascade="all, delete-orphan")

    def __init__(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        role: RoleEnum,
        username: Optional[str] = None,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[dt] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            email=email,
            password_hash=password_hash,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            id=id,
            created_at=created_at,
            **kwargs,
        )

