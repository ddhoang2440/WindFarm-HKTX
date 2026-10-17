from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.models.User import User, UserRole, UserStatus
from src.config.settings import get_settings
from src.core.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    ConflictException,
)
from src.core.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting (in-memory, MVP only)
_failed_attempts: dict[str, list[datetime]] = defaultdict(list)
LOCK_DURATION = timedelta(minutes=15)
MAX_ATTEMPTS = 5


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


async def register_user(
    email: str, password: str, full_name: str = ""
) -> User:
    existing = await User.find_one(User.email == email)
    if existing:
        logger.warning(f"Registration failed - email exists: {email}")
        raise ConflictException("Email already registered")

    user = User(
        email=email,
        password_hash=_hash_password(password),
        full_name=full_name,
        role=UserRole.ENGINEER,      # tường minh
        status=UserStatus.PENDING,   # tường minh
    )
    await user.insert()
    logger.info(
        f"User registered: {email} ({full_name}) - status=PENDING"
    )
    return user


async def login_user(email: str, password: str) -> str:
    now = datetime.utcnow()

    # 1. Rate limiting
    attempts = [
        t for t in _failed_attempts[email] if now - t < LOCK_DURATION
    ]
    if len(attempts) >= MAX_ATTEMPTS:
        logger.warning(f"Account locked: {email}")
        raise ForbiddenException(
            "Account locked due to too many failed attempts. "
            "Try again in 15 minutes."
        )

    # 2. Verify credentials
    user = await User.find_one(User.email == email)
    if not user or not _verify_password(password, user.password_hash):
        _failed_attempts[email].append(now)
        logger.warning(f"Login failed - invalid credentials: {email}")
        raise UnauthorizedException("Invalid credentials")

    # 3. Check status
    if user.status == UserStatus.PENDING:
        logger.warning(f"Login blocked - pending approval: {email}")
        raise ForbiddenException(
            "Your account is pending approval. "
            "Please wait for Administrator."
        )

    if user.status in (UserStatus.REJECTED, UserStatus.INACTIVE):
        logger.warning(f"Login blocked - account {user.status}: {email}")
        raise ForbiddenException(
            "Your account has been deactivated. "
            "Please contact Administrator."
        )

    if user.status != UserStatus.ACTIVE:
        logger.warning(f"Login blocked - unexpected status: {email}")
        raise ForbiddenException("Account is not active")

    # 4. Success → reset attempts, update last_login
    _failed_attempts.pop(email, None)
    user.last_login_at = now
    user.updated_at = now
    await user.save()

    logger.info(f"Login successful: {email} (role={user.role.value})")

    # 5. Generate token
    return _create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
    })


async def get_current_user(token: str) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("Invalid token payload")
    except JWTError:
        raise UnauthorizedException("Invalid or expired token")

    user = await User.get(user_id)
    if not user:
        raise UnauthorizedException("User not found")

    # ✅ Check status ngay cả khi đã có token
    if user.status != UserStatus.ACTIVE:
        raise ForbiddenException(
            f"Account is {user.status.value}. "
            f"Please contact Administrator."
        )

    return user