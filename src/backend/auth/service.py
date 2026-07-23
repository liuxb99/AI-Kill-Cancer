"""
AuthService — production authentication and authorization service.

Uses bcrypt for password hashing and JWT (HS256) for stateless tokens.
Access tokens are short-lived (default 60 min). Refresh tokens are
long-lived (default 30 days) and can be revoked via a blacklist table.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.models import (
    ROLE_PERMISSIONS,
    AuthenticationError,
    DuplicateUserError,
    Permission,
    PermissionDeniedError,
)
from src.backend.config import settings
from src.backend.domain.user import (
    LoginRequest,
    TokenBlacklistModel,
    TokenResponse,
    UserCreate,
    UserModel,
    UserResponse,
)

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """Return bcrypt hash (auto-generated salt)."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
    ).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def _create_access_token(user_id: str, role: str) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """Create a long-lived JWT refresh token. Returns (token, expires_at_naive_utc)."""
    now = datetime.now(UTC)
    exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": exp,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    # Return naive UTC datetime for DB storage (SQLAlchemy DateTime compatibility)
    return token, exp.replace(tzinfo=None)


def _decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT token. Raises AuthenticationError on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {e}")

    if payload.get("type") != expected_type:
        raise AuthenticationError(f"Invalid token type (expected {expected_type})")

    return payload


# ── Service ──────────────────────────────────────────────────────────────

class AuthService:
    """Production authentication service backed by the database."""

    @staticmethod
    def _user_to_response(user: UserModel) -> UserResponse:
        """Convert a UserModel to a UserResponse, handling UUID->str conversion."""
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role.value if hasattr(user.role, "value") else user.role,
            is_active=user.is_active,
            display_name=user.display_name,
            created_at=user.created_at,
        )

    async def register_user(
        self,
        db: AsyncSession,
        user_create: UserCreate,
    ) -> UserResponse:
        """Register a new user. Returns user info (no token)."""
        # Check duplicates
        existing_username = await self._find_by_username(db, user_create.username)
        if existing_username:
            raise DuplicateUserError(f"Username '{user_create.username}' already exists")

        if user_create.email:
            existing_email = await self._find_by_email(db, user_create.email)
            if existing_email:
                raise DuplicateUserError(f"Email '{user_create.email}' already exists")

        user = UserModel(
            id=uuid.uuid4(),
            username=user_create.username,
            email=user_create.email,
            password_hash=_hash_password(user_create.password),
            role=user_create.role,
            display_name=user_create.display_name,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Registered user %s (role=%s)", user.username, user.role)
        return self._user_to_response(user)

    async def login(
        self,
        db: AsyncSession,
        login_req: LoginRequest,
    ) -> TokenResponse:
        """Authenticate with username+password, return token pair."""
        user = await self._find_by_username(db, login_req.username)
        if not user:
            raise AuthenticationError("Invalid username or password")

        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        if not _verify_password(login_req.password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        access_token = _create_access_token(str(user.id), user.role.value)
        refresh_token, refresh_exp = _create_refresh_token(str(user.id))

        logger.info("User %s logged in", user.username)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=self._user_to_response(user),
        )

    async def authenticate(self, db: AsyncSession, token: str) -> UserModel:
        """Validate an access token and return the user."""
        payload = _decode_token(token, expected_type="access")
        user_id = payload.get("sub")

        # Check blacklist
        if await self._is_token_blacklisted(db, payload["jti"]):
            raise AuthenticationError("Token has been revoked")

        user = await self._find_by_id(db, uuid.UUID(user_id))
        if not user:
            raise AuthenticationError("User not found")
        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        return user

    async def refresh_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> TokenResponse:
        """Exchange a refresh token for a new token pair."""
        payload = _decode_token(refresh_token, expected_type="refresh")

        # Check blacklist
        if await self._is_token_blacklisted(db, payload["jti"]):
            raise AuthenticationError("Refresh token has been revoked")

        user_id = payload.get("sub")
        user = await self._find_by_id(db, uuid.UUID(user_id))
        if not user:
            raise AuthenticationError("User not found")
        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        # Blacklist the old refresh token (rotation)
        exp_ts = datetime.fromtimestamp(payload["exp"], tz=UTC).replace(tzinfo=None)
        blacklisted = TokenBlacklistModel(
            id=uuid.uuid4(),
            jti=payload["jti"],
            token_type="refresh",
            expires_at=exp_ts,
        )
        db.add(blacklisted)

        # Issue new pair
        new_access = _create_access_token(str(user.id), user.role.value)
        new_refresh, refresh_exp = _create_refresh_token(str(user.id))

        await db.commit()
        logger.info("Token refreshed for user %s", user.username)
        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=self._user_to_response(user),
        )

    async def logout(
        self,
        db: AsyncSession,
        access_token: str,
        refresh_token: str | None = None,
    ) -> None:
        """Revoke tokens by blacklisting their JTI."""
        # Blacklist access token
        try:
            access_payload = _decode_token(access_token, expected_type="access")
            exp_ts = datetime.fromtimestamp(access_payload["exp"], tz=UTC).replace(tzinfo=None)
            db.add(TokenBlacklistModel(
                id=uuid.uuid4(),
                jti=access_payload["jti"],
                token_type="access",
                expires_at=exp_ts,
            ))
        except AuthenticationError:
            pass  # Already invalid — nothing to blacklist

        # Blacklist refresh token if provided
        if refresh_token:
            try:
                refresh_payload = _decode_token(refresh_token, expected_type="refresh")
                exp_ts = datetime.fromtimestamp(refresh_payload["exp"], tz=UTC).replace(tzinfo=None)
                db.add(TokenBlacklistModel(
                    id=uuid.uuid4(),
                    jti=refresh_payload["jti"],
                    token_type="refresh",
                    expires_at=exp_ts,
                ))
            except AuthenticationError:
                pass

        await db.commit()
        logger.info("Tokens revoked")

    # ── Permission helpers ───────────────────────────────────────────────

    def authorize(self, user: UserModel, permission: Permission) -> bool:
        """Check if a user's role grants the given permission."""
        user_permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in user_permissions

    def require_permission(self, user: UserModel, permission: Permission) -> None:
        """Raise PermissionDeniedError if the user lacks the permission."""
        if not self.authorize(user, permission):
            raise PermissionDeniedError(
                f"User {user.username} lacks permission: {permission.value}"
            )

    # ── Token blacklist helpers ──────────────────────────────────────────

    async def _is_token_blacklisted(self, db: AsyncSession, jti: str) -> bool:
        stmt = select(TokenBlacklistModel).where(TokenBlacklistModel.jti == jti)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ── User lookup helpers ──────────────────────────────────────────────

    async def get_user(self, db: AsyncSession, user_id: uuid.UUID) -> UserModel | None:
        return await self._find_by_id(db, user_id)

    async def get_user_by_username(self, db: AsyncSession, username: str) -> UserModel | None:
        return await self._find_by_username(db, username)

    async def _find_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_by_username(self, db: AsyncSession, username: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_by_email(self, db: AsyncSession, email: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# ── Singleton provider ──────────────────────────────────────────────────

_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Return the singleton AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
