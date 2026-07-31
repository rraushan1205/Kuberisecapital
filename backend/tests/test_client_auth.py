import asyncio
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "a-strong-test-secret-key-0123456789abcdef")
os.environ.setdefault("ADMIN_PASSWORD", "TestAdminPass123!")
os.environ.setdefault("REGISTRATION_INVITATION_CODES", '["VALID123"]')

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.auth import register_user
from app.api.client_auth import login_client, refresh_client_session
from app.core.config import get_settings
from app.core.security import decode_access_token, hash_password
from app.db.base import Base
from app.models.domain import AccountStatus, RefreshToken, User, UserRole
from app.schemas.auth import UserRegistrationInput
from app.schemas.client import ClientLoginInput, ClientRefreshInput


def _request() -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


class ClientAuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def make_user(self, status: AccountStatus) -> User:
        user = User(
            email=f"{status.value.lower()}@example.com",
            password_hash=hash_password("StrongPass123!"),
            role=UserRole.USER,
            account_status=status,
        )
        self.session.add(user)
        self.session.commit()
        return user

    def test_pending_and_rejected_users_never_receive_session_tokens(self) -> None:
        for account_status in (AccountStatus.PENDING, AccountStatus.REJECTED):
            user = self.make_user(account_status)
            with self.assertRaises(HTTPException) as captured:
                asyncio.run(login_client(
                    ClientLoginInput(email=user.email, password="StrongPass123!"),
                    _request(),
                    self.session,
                ))
            self.assertEqual(captured.exception.status_code, 403)

        self.assertEqual(self.session.scalar(select(func.count()).select_from(RefreshToken)), 0)

    def test_login_issues_access_and_refresh_tokens_for_approved_user(self) -> None:
        user = self.make_user(AccountStatus.APPROVED)

        result = asyncio.run(login_client(
            ClientLoginInput(email=user.email, password="StrongPass123!"),
            _request(),
            self.session,
        ))

        self.assertEqual(result.email, user.email)
        self.assertEqual(result.account_status, "approved")
        self.assertTrue(result.access_token)
        self.assertTrue(result.refresh_token)
        self.assertEqual(decode_access_token(result.access_token)["role"], "USER")
        self.assertEqual(self.session.scalar(select(func.count()).select_from(RefreshToken)), 1)

    def test_refresh_revokes_locked_user_session_family(self) -> None:
        user = self.make_user(AccountStatus.APPROVED)
        login_result = asyncio.run(login_client(
            ClientLoginInput(email=user.email, password="StrongPass123!"),
            _request(),
            self.session,
        ))
        refresh_token = login_result.refresh_token
        user.account_status = AccountStatus.REJECTED
        self.session.commit()

        with self.assertRaises(HTTPException) as captured:
            refresh_client_session(ClientRefreshInput(refresh_token=refresh_token), self.session)

        self.assertEqual(captured.exception.status_code, 403)
        self.assertEqual(
            self.session.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.revoked.is_(False))),
            0,
        )

    def test_registration_password_requires_length_and_complexity(self) -> None:
        with self.assertRaises(ValueError):
            UserRegistrationInput(email="qa@example.com", password="short", full_name="QA", invitation_code="VALID123")
        with self.assertRaises(ValueError):
            UserRegistrationInput(email="qa@example.com", password="alllowercase12", full_name="QA", invitation_code="VALID123")

        payload = UserRegistrationInput(email="qa@example.com", password="StrongPass123!", full_name="QA", invitation_code="VALID123")
        self.assertEqual(payload.password, "StrongPass123!")

    def test_registration_requires_a_server_validated_invitation_code(self) -> None:
        with self.assertRaises(HTTPException) as captured:
            asyncio.run(register_user(
                UserRegistrationInput(
                    email="invited@example.com",
                    password="StrongPass123!",
                    full_name="Invited User",
                    invitation_code="INVALID",
                ),
                _request(),
                self.session,
            ))
        self.assertEqual(captured.exception.status_code, 403)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(User)), 0)

        registration = asyncio.run(register_user(
            UserRegistrationInput(
                email="invited@example.com",
                password="StrongPass123!",
                full_name="Invited User",
                invitation_code="valid123",
            ),
            _request(),
            self.session,
        ))
        self.assertEqual(registration.email, "invited@example.com")
