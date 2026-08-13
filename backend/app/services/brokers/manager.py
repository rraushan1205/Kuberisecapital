"""
Broker manager for creating and managing broker instances.

This module provides the BrokerManager class, which acts as a factory
for creating broker instances. It follows the factory pattern and serves
as the primary interface for route handlers to interact with brokers.

Design rationale:
    - Factory pattern: Centralizes broker instantiation logic
    - Follows existing Kuberise Capital pattern (similar to trading_engine.py service)
    - Stateless: Creates fresh broker instances on demand
    - Thread-safe: No shared mutable state
    - Easy to test: Can inject mock registries

Route handlers should use get_broker_manager() to obtain the manager
and then call get_broker(provider_name) to get a broker instance.
"""

from __future__ import annotations

from functools import lru_cache

from app.services.brokers.base import BrokerProvider
from app.services.brokers.exceptions import BrokerNotFoundError
from app.services.brokers.registry import BrokerRegistry, get_global_registry


class BrokerManager:
    """
    Factory for creating broker provider instances.
    
    The BrokerManager is responsible for:
        - Creating broker instances from the registry
        - Validating broker provider names
        - Providing a consistent interface for broker access
    
    This class follows the existing Kuberise Capital service pattern:
        - Stateless (no instance variables storing state)
        - Simple function-based interface
        - Direct instantiation (no complex DI framework)
    
    Usage:
        from app.services.brokers import get_broker_manager
        
        # In a route handler
        @router.get("/brokers/{provider}/positions")
        async def get_positions(provider: str, user: CurrentUser, db: DbSession):
            manager = get_broker_manager()
            broker = manager.get_broker(provider)
            
            # Fetch access token from database
            connection = get_broker_connection(db, user.id, provider)
            access_token = decrypt_token(connection.access_token_encrypted)
            
            # Use the broker
            positions = await broker.get_positions(user.id, access_token)
            return positions
    """

    def __init__(self, registry: BrokerRegistry | None = None) -> None:
        """
        Initialize the broker manager.
        
        Args:
            registry: Optional BrokerRegistry instance. If None, uses the global registry.
                     This parameter is primarily for testing with mock registries.
        """
        self._registry = registry or get_global_registry()

    def get_broker(self, provider_name: str) -> BrokerProvider:
        """
        Get a broker instance by provider name.
        
        This method creates a fresh broker instance each time it's called.
        Broker instances are stateless, so creating new instances is cheap
        and ensures thread safety.
        
        Args:
            provider_name: The broker provider name (e.g., "zerodha", "fyers")
        
        Returns:
            BrokerProvider: A fresh broker instance
        
        Raises:
            BrokerNotFoundError: If the provider is not registered
        
        Example:
            manager = BrokerManager()
            broker = manager.get_broker("zerodha")
            url = await broker.get_auth_url(user_id, redirect_uri)
        """
        # Normalize provider name (lowercase, strip whitespace)
        provider_name = provider_name.lower().strip()

        # Get the broker class from registry
        # This raises BrokerNotFoundError if not registered
        broker_class = self._registry.get(provider_name)

        # Create and return a fresh instance
        return broker_class()

    def is_provider_supported(self, provider_name: str) -> bool:
        """
        Check if a broker provider is supported.
        
        Args:
            provider_name: The broker provider name to check
        
        Returns:
            bool: True if the provider is registered and available
        
        Example:
            manager = BrokerManager()
            if manager.is_provider_supported("zerodha"):
                broker = manager.get_broker("zerodha")
            else:
                raise HTTPException(404, "Broker not supported")
        """
        provider_name = provider_name.lower().strip()
        return self._registry.is_registered(provider_name)

    def list_supported_providers(self) -> list[str]:
        """
        List all supported broker provider names.
        
        Returns:
            list[str]: List of provider names
        
        Example:
            manager = BrokerManager()
            providers = manager.list_supported_providers()
            # Returns: ["fyers", "aliceblue"]
        """
        return self._registry.list_providers()

    def list_available_brokers(self) -> list[dict[str, str]]:
        """
        List all available brokers with their metadata.
        
        This method is useful for API endpoints that need to return
        information about all supported brokers (e.g., for a UI dropdown).
        
        Returns:
            list[dict]: List of broker metadata dictionaries containing:
                - provider: Provider name (e.g., "zerodha")
                - display_name: Human-readable name (e.g., "Zerodha Kite")
                - supports_websocket: Boolean indicating WebSocket support
        
        Example:
            manager = BrokerManager()
            brokers = manager.list_available_brokers()
            # Returns: [
            #     {
            #         "provider": "zerodha",
            #         "display_name": "Zerodha Kite",
            #         "supports_websocket": True
            #     },
            #     {
            #         "provider": "fyers",
            #         "display_name": "Fyers",
            #         "supports_websocket": True
            #     }
            # ]
        """
        return self._registry.list_brokers()

    def get_broker_display_name(self, provider_name: str) -> str:
        """
        Get the display name for a broker provider.
        
        Args:
            provider_name: The broker provider name
        
        Returns:
            str: The human-readable display name
        
        Raises:
            BrokerNotFoundError: If the provider is not registered
        
        Example:
            manager = BrokerManager()
            name = manager.get_broker_display_name("zerodha")
            # Returns: "Zerodha Kite"
        """
        broker = self.get_broker(provider_name)
        return broker.display_name

    def validate_provider_name(self, provider_name: str) -> tuple[bool, str | None]:
        """
        Validate a provider name and return validation result.
        
        This method is useful for request validation in route handlers.
        
        Args:
            provider_name: The provider name to validate
        
        Returns:
            tuple: (is_valid, error_message)
                - is_valid: True if valid, False otherwise
                - error_message: None if valid, error description if invalid
        
        Example:
            manager = BrokerManager()
            is_valid, error = manager.validate_provider_name("zerodha")
            if not is_valid:
                raise HTTPException(400, error)
        """
        if not provider_name:
            return False, "Provider name cannot be empty"

        if not isinstance(provider_name, str):
            return False, "Provider name must be a string"

        provider_name = provider_name.lower().strip()

        if not provider_name:
            return False, "Provider name cannot be empty or whitespace"

        if not self._registry.is_registered(provider_name):
            available = ", ".join(self._registry.list_providers())
            return False, f"Unsupported broker provider: {provider_name}. Available: {available}"

        return True, None

    def __repr__(self) -> str:
        """Return string representation of the manager."""
        providers = ", ".join(self._registry.list_providers())
        count = len(self._registry)
        return f"BrokerManager({count} registered: {providers})"


@lru_cache(maxsize=1)
def get_broker_manager() -> BrokerManager:
    """
    Get the global broker manager instance.
    
    This function returns a cached BrokerManager instance that uses the
    global broker registry. It follows the same pattern as get_settings()
    in app.core.config.
    
    The @lru_cache decorator ensures only one instance is created and
    reused across the application, providing a lightweight singleton pattern.
    
    Returns:
        BrokerManager: The global broker manager instance
    
    Example:
        from app.services.brokers import get_broker_manager
        
        # In a route handler
        @router.get("/brokers/{provider}/profile")
        async def get_broker_profile(provider: str, user: CurrentUser):
            manager = get_broker_manager()
            broker = manager.get_broker(provider)
            # ... use broker
    
    Note:
        This follows the existing Kuberise Capital pattern from:
            - app.core.config.get_settings()
            - app.db.session.get_db()
    """
    return BrokerManager()


def get_broker(provider_name: str) -> BrokerProvider:
    """
    Convenience function to get a broker instance directly.
    
    This is a shorthand for:
        manager = get_broker_manager()
        broker = manager.get_broker(provider_name)
    
    Args:
        provider_name: The broker provider name
    
    Returns:
        BrokerProvider: A fresh broker instance
    
    Raises:
        BrokerNotFoundError: If the provider is not registered
    
    Example:
        from app.services.brokers.manager import get_broker
        
        broker = get_broker("zerodha")
        url = await broker.get_auth_url(user_id, redirect_uri)
    
    Note:
        For most use cases, prefer get_broker_manager() which provides
        additional utility methods like validation and listing providers.
    """
    manager = get_broker_manager()
    return manager.get_broker(provider_name)
