import asyncio
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from uuid import UUID

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "a-strong-test-secret-key-0123456789abcdef")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "TestAdminPass123!")

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.admin import login_admin, refresh_admin_session
from app.core.config import get_settings
from app.core.security import decode_access_token, verify_password
from app.db.base import Base
from app.models.domain import RefreshToken, User, UserRole
from app.schemas.admin import AdminLoginInput, AdminRefreshInput
from app.services.admin_bootstrap import ensure_initial_super_admin
from app.services.refresh_sessions import session_is_active


def _request() -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


class AdminAuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_startup_seeds_a_hashed_super_admin_once(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            created = ensure_initial_super_admin(self.session)

        seeded_user = self.session.scalar(select(User).where(User.role == UserRole.SUPER_ADMIN))
        self.assertIsNotNone(created)
        self.assertIsNotNone(seeded_user)
        self.assertEqual(seeded_user.email, "admin@example.com")
        self.assertNotEqual(seeded_user.password_hash, "TestAdminPass123!")
        self.assertTrue(verify_password("TestAdminPass123!", seeded_user.password_hash))
        self.assertIn("Initial Super Admin", output.getvalue())
        self.assertIn("Email: admin@example.com", output.getvalue())
        self.assertIn("Password: TestAdminPass123!", output.getvalue())
        self.assertIsNone(ensure_initial_super_admin(self.session))
        self.assertEqual(self.session.scalar(select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)), 1)

    def test_login_accepts_the_seeded_admin_and_issues_tokens(self) -> None:
        ensure_initial_super_admin(self.session)

        result = asyncio.run(login_admin(
            AdminLoginInput(email="ADMIN@example.com", password="TestAdminPass123!"),
            _request(),
            self.session,
        ))

        self.assertEqual(result.email, "admin@example.com")
        self.assertEqual(result.role, UserRole.SUPER_ADMIN)
        self.assertTrue(result.access_token)
        self.assertTrue(result.refresh_token)
        self.assertEqual(decode_access_token(result.access_token)["role"], "SUPER_ADMIN")
        self.assertEqual(self.session.scalar(select(func.count()).select_from(RefreshToken)), 1)

    def test_login_rejects_an_invalid_password(self) -> None:
        ensure_initial_super_admin(self.session)

        with self.assertRaises(HTTPException) as captured:
            asyncio.run(login_admin(
                AdminLoginInput(email="admin@example.com", password="incorrect-password"),
                _request(),
                self.session,
            ))

        self.assertEqual(captured.exception.status_code, 401)
        self.assertEqual(captured.exception.detail, "Invalid credentials.")

    def test_refresh_rotates_the_session_and_revokes_the_previous_access_token(self) -> None:
        ensure_initial_super_admin(self.session)
        login_result = asyncio.run(login_admin(
            AdminLoginInput(email="admin@example.com", password="TestAdminPass123!"),
            _request(),
            self.session,
        ))
        raw_refresh_token = login_result.refresh_token
        original_access_token = login_result.access_token
        original_session_id = UUID(str(decode_access_token(original_access_token)["sid"]))

        refresh_result = refresh_admin_session(
            AdminRefreshInput(refresh_token=raw_refresh_token),
            self.session,
        )
        rotated_refresh_token = refresh_result.refresh_token
        rotated_access_token = refresh_result.access_token
        rotated_session_id = UUID(str(decode_access_token(rotated_access_token)["sid"]))

        self.assertNotEqual(raw_refresh_token, rotated_refresh_token)
        self.assertNotEqual(original_session_id, rotated_session_id)
        self.assertFalse(session_is_active(self.session, original_session_id))
        self.assertTrue(session_is_active(self.session, rotated_session_id))

    def test_reusing_a_rotated_refresh_token_revokes_its_entire_family(self) -> None:
        ensure_initial_super_admin(self.session)
        login_result = asyncio.run(login_admin(
            AdminLoginInput(email="admin@example.com", password="TestAdminPass123!"),
            _request(),
            self.session,
        ))
        old_refresh_token = login_result.refresh_token
        refresh_admin_session(AdminRefreshInput(refresh_token=old_refresh_token), self.session)

        with self.assertRaises(HTTPException) as captured:
            refresh_admin_session(AdminRefreshInput(refresh_token=old_refresh_token), self.session)

        self.assertEqual(captured.exception.status_code, 401)
        self.assertIn("reuse was detected", captured.exception.detail)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.revoked.is_(False))), 0)
