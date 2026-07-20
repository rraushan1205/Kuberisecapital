from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select

from app.api.dependencies import DbSession, SuperAdmin
from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.models.domain import (
    AccountStatus,
    Announcement,
    BrokerConnection,
    BrokerStatus,
    ExecutionAction,
    ExecutionLog,
    Strategy,
    StrategyStatus,
    SubscriptionStatus,
    User,
    UserRole,
)
from app.schemas.admin import (
    AdminLoginInput,
    AdminSessionOutput,
    AnnouncementInput,
    AnnouncementOutput,
    ConnectedUserOutput,
    ExecutionLogOutput,
    StrategyOutput,
    UserOutput,
)
from app.services.trading_engine import dispatch_engine_command

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/auth/login", response_model=AdminSessionOutput)
def login_admin(payload: AdminLoginInput, response: Response, db: DbSession) -> AdminSessionOutput:
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access is required.")

    user.last_login_at = datetime.now(UTC)
    db.commit()
    token = create_access_token(str(user.id), user.role.value)
    response.set_cookie(
        key="stratum_admin_session",
        value=token,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        max_age=get_settings().jwt_expires_minutes * 60,
        path="/",
    )
    return AdminSessionOutput(user_id=user.id, email=user.email, role=user.role)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_admin(_: SuperAdmin, response: Response) -> Response:
    response.delete_cookie("stratum_admin_session", path="/")
    return response


@router.get("/auth/session", response_model=AdminSessionOutput)
def get_admin_session(admin: SuperAdmin) -> AdminSessionOutput:
    return AdminSessionOutput(user_id=admin.id, email=admin.email, role=admin.role)


@router.get("/users", response_model=list[UserOutput])
def list_users(_: SuperAdmin, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.get("/pending-registrations", response_model=list[UserOutput])
def list_pending_registrations(_: SuperAdmin, db: DbSession) -> list[User]:
    statement = select(User).where(User.account_status == AccountStatus.PENDING).order_by(User.created_at.asc())
    return list(db.scalars(statement))


@router.post("/subscriptions/{user_id}/approve", response_model=UserOutput)
def approve_subscription(user_id: UUID, _: SuperAdmin, db: DbSession) -> User:
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.USER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account was not found.")
    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email verification is required before approval.")

    user.account_status = AccountStatus.APPROVED
    user.subscription_status = SubscriptionStatus.ACTIVE
    db.commit()
    db.refresh(user)
    return user


@router.get("/connected-users", response_model=list[ConnectedUserOutput])
def list_connected_users(_: SuperAdmin, db: DbSession) -> list[ConnectedUserOutput]:
    statement = (
        select(BrokerConnection, User)
        .join(User, BrokerConnection.user_id == User.id)
        .where(BrokerConnection.status == BrokerStatus.CONNECTED)
        .order_by(BrokerConnection.connected_at.desc())
    )
    return [
        ConnectedUserOutput(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            provider=connection.provider,
            status=connection.status,
            connected_at=connection.connected_at,
        )
        for connection, user in db.execute(statement).all()
    ]


@router.get("/strategies", response_model=list[StrategyOutput])
def list_strategies(_: SuperAdmin, db: DbSession) -> list[Strategy]:
    return list(db.scalars(select(Strategy).order_by(Strategy.created_at.desc())))


@router.post("/strategies", response_model=StrategyOutput, status_code=status.HTTP_201_CREATED)
async def upload_strategy(
    _: SuperAdmin,
    db: DbSession,
    name: str = Form(min_length=1, max_length=160),
    script: UploadFile = File(),
) -> Strategy:
    if not script.filename or Path(script.filename).suffix.lower() != ".py":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only Python strategy files are accepted.")
    existing_count = db.scalar(select(func.count()).select_from(Strategy)) or 0
    if existing_count >= 3:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The platform supports a maximum of three strategies.")
    existing_name = db.scalar(select(Strategy).where(Strategy.name == name.strip()))
    if existing_name is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A strategy with this name already exists.")

    contents = await script.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The strategy file is empty.")
    if len(contents) > 1_048_576:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Strategy files are limited to 1 MB.")

    storage_path = get_settings().strategy_storage_path
    storage_path.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid4()}.py"
    destination = storage_path / storage_key
    destination.write_bytes(contents)

    strategy = Strategy(
        name=name.strip(),
        script_filename=Path(script.filename).name,
        script_storage_key=storage_key,
        uploaded_by_id=_.id,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


async def update_strategy_execution(strategy_id: UUID, command: str, action: ExecutionAction, admin: User, db: DbSession) -> Strategy:
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy was not found.")
    await dispatch_engine_command(command, {"strategy_id": str(strategy.id)})
    strategy.status = StrategyStatus.RUNNING if action == ExecutionAction.STRATEGY_STARTED else StrategyStatus.STOPPED
    db.add(ExecutionLog(action=action, message=f"Strategy {strategy.name} {command} command accepted by the trading engine.", strategy_id=strategy.id, initiated_by_id=admin.id))
    db.commit()
    db.refresh(strategy)
    return strategy


@router.post("/strategies/{strategy_id}/start", response_model=StrategyOutput)
async def start_strategy(strategy_id: UUID, admin: SuperAdmin, db: DbSession) -> Strategy:
    return await update_strategy_execution(strategy_id, "start", ExecutionAction.STRATEGY_STARTED, admin, db)


@router.post("/strategies/{strategy_id}/stop", response_model=StrategyOutput)
async def stop_strategy(strategy_id: UUID, admin: SuperAdmin, db: DbSession) -> Strategy:
    return await update_strategy_execution(strategy_id, "stop", ExecutionAction.STRATEGY_STOPPED, admin, db)


@router.post("/force-square-off", status_code=status.HTTP_204_NO_CONTENT)
async def force_square_off(admin: SuperAdmin, db: DbSession) -> Response:
    await dispatch_engine_command("force-square-off", {})
    db.add(ExecutionLog(action=ExecutionAction.FORCE_SQUARE_OFF, message="Force square off command accepted by the trading engine.", initiated_by_id=admin.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/logs", response_model=list[ExecutionLogOutput])
def list_execution_logs(_: SuperAdmin, db: DbSession) -> list[ExecutionLog]:
    return list(db.scalars(select(ExecutionLog).order_by(ExecutionLog.created_at.desc()).limit(200)))


@router.get("/announcements", response_model=list[AnnouncementOutput])
def list_announcements(_: SuperAdmin, db: DbSession) -> list[Announcement]:
    return list(db.scalars(select(Announcement).order_by(Announcement.created_at.desc())))


@router.post("/announcements", response_model=AnnouncementOutput, status_code=status.HTTP_201_CREATED)
def create_announcement(payload: AnnouncementInput, admin: SuperAdmin, db: DbSession) -> Announcement:
    announcement = Announcement(title=payload.title.strip(), message=payload.message.strip(), created_by_id=admin.id)
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement
