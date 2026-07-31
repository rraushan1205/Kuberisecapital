"""
Structured logging configuration for security events.

Implements JSON-formatted logging with security event tracking.
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict

import structlog
from structlog import wrap_logger


def add_timestamp(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add timestamp to log event."""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_severity(_, __, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add severity level to log event."""
    event_dict["severity"] = event_dict.get("level", "info").upper()
    return event_dict


def configure_logging(environment: str = "production") -> None:
    """
    Configure structured logging for the application.

    Args:
        environment: Environment name (development, staging, production)
    """
    # Determine log level based on environment
    log_level = logging.DEBUG if environment == "development" else logging.INFO

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_timestamp,
            add_severity,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if environment == "production" else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (defaults to calling module)

    Returns:
        Configured structured logger

    Example:
        logger = get_logger(__name__)
        logger.info("user_login_success", user_id="123", email="user@example.com")
    """
    return structlog.get_logger(name)


# Security event logger helpers
def log_auth_event(
    event_type: str,
    success: bool,
    user_id: str = None,
    email: str = None,
    reason: str = None,
    ip_address: str = None,
    **extra
) -> None:
    """
    Log authentication event.

    Args:
        event_type: Type of event (login, register, logout, etc.)
        success: Whether the event was successful
        user_id: User ID if available
        email: User email
        reason: Failure reason if unsuccessful
        ip_address: Client IP address
        **extra: Additional context
    """
    logger = get_logger("auth")

    event_data = {
        "event_type": event_type,
        "success": success,
        "user_id": user_id,
        "email": email,
        "reason": reason,
        "ip_address": ip_address,
        **extra,
    }

    if success:
        logger.info(f"{event_type}_success", **event_data)
    else:
        logger.warning(f"{event_type}_failed", **event_data)


def log_admin_action(
    action: str,
    admin_id: str,
    target_id: str = None,
    target_type: str = None,
    details: dict = None,
    **extra
) -> None:
    """
    Log admin action for audit trail.

    Args:
        action: Action performed (approve_user, start_strategy, etc.)
        admin_id: ID of admin performing action
        target_id: ID of affected resource
        target_type: Type of resource (user, strategy, etc.)
        details: Additional details about the action
        **extra: Additional context
    """
    logger = get_logger("admin")

    logger.info(
        "admin_action",
        action=action,
        admin_id=admin_id,
        target_id=target_id,
        target_type=target_type,
        details=details,
        **extra,
    )


def log_security_event(
    event_type: str,
    severity: str,
    description: str,
    user_id: str = None,
    ip_address: str = None,
    **extra
) -> None:
    """
    Log security event (suspicious activity, rate limit violations, etc.).

    Args:
        event_type: Type of security event
        severity: Severity level (low, medium, high, critical)
        description: Human-readable description
        user_id: User ID if applicable
        ip_address: Client IP address
        **extra: Additional context
    """
    logger = get_logger("security")

    event_data = {
        "event_type": event_type,
        "severity": severity,
        "description": description,
        "user_id": user_id,
        "ip_address": ip_address,
        **extra,
    }

    if severity in ["high", "critical"]:
        logger.error("security_event", **event_data)
    elif severity == "medium":
        logger.warning("security_event", **event_data)
    else:
        logger.info("security_event", **event_data)
