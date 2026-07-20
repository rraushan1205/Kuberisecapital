import os
import unittest
from contextlib import redirect_stdout
from io import StringIO

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "ChangeMe123!")

from fastapi import HTTPException, Response
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.admin import login_admin
from app.core.config import get_settings
from app.core.security import verify_password
from app.db.base import Base
from app.models.domain import User, UserRole
from app.schemas.admin import AdminLoginInput
from app.services.admin_bootstrap import ensure_initial_super_admin


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
        self.assertNotEqual(seeded_user.password_hash, "ChangeMe123!")
        self.assertTrue(verify_password("ChangeMe123!", seeded_user.password_hash))
        self.assertIn("Initial Super Admin", output.getvalue())
        self.assertIn("Email: admin@example.com", output.getvalue())
        self.assertIn("Password: ChangeMe123!", output.getvalue())
        self.assertIsNone(ensure_initial_super_admin(self.session))
        self.assertEqual(self.session.scalar(select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)), 1)

    def test_login_accepts_the_seeded_admin_and_sets_a_session_cookie(self) -> None:
        ensure_initial_super_admin(self.session)
        response = Response()

        result = login_admin(
            AdminLoginInput(email="ADMIN@example.com", password="ChangeMe123!"),
            response,
            self.session,
        )

        self.assertEqual(result.email, "admin@example.com")
        self.assertEqual(result.role, UserRole.SUPER_ADMIN)
        self.assertIn("stratum_admin_session=", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    def test_login_rejects_an_invalid_password(self) -> None:
        ensure_initial_super_admin(self.session)

        with self.assertRaises(HTTPException) as captured:
            login_admin(
                AdminLoginInput(email="admin@example.com", password="incorrect-password"),
                Response(),
                self.session,
            )

        self.assertEqual(captured.exception.status_code, 401)
        self.assertEqual(captured.exception.detail, "Invalid credentials.")
