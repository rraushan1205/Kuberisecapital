"""
Broker registry for managing broker provider implementations.

This module provides a centralized registry where broker implementations
can register themselves for discovery. It follows the registry pattern to
decouple broker registration from broker usage.

Design rationale:
    - Centralized broker discovery
    - Type-safe broker registration
    - Runtime validation of broker implementations
    - Easy to add new brokers without modifying existing code
    - Supports both manual registration and auto-discovery

The registry is a singleton that maintains a mapping of provider names
to broker classes. Route handlers and services use the registry indirectly
through the BrokerManager.
"""

from typing import Type

from app.services.brokers.base import BrokerProvider
from app.services.brokers.exceptions import BrokerNotFoundError


class BrokerRegistry:
    """
    Registry for broker provider implementations.
    
    This class maintains a mapping of provider names to broker classes.
    It ensures that only valid BrokerProvider implementations can be registered.
    
    Usage:
        # Register a broker
        registry = BrokerRegistry()
        registry.register(ZerodhaBroker)
        
        # Get a broker class
        broker_class = registry.get("zerodha")
        
        # List all registered brokers
        providers = registry.list_providers()
    """

    def __init__(self) -> None:
        """Initialize an empty broker registry."""
        self._brokers: dict[str, Type[BrokerProvider]] = {}

    def register(self, broker_class: Type[BrokerProvider]) -> None:
        """
        Register a broker provider implementation.
        
        The broker's provider_name property is used as the registry key.
        If a broker with the same name is already registered, it will be
        replaced (useful for testing with mock implementations).
        
        Args:
            broker_class: A class that inherits from BrokerProvider
        
        Raises:
            TypeError: If broker_class is not a subclass of BrokerProvider
            AttributeError: If broker_class doesn't implement required properties
        
        Example:
            class ZerodhaBroker(BrokerProvider):
                @property
                def provider_name(self) -> str:
                    return "zerodha"
                # ... implement other methods
            
            registry = BrokerRegistry()
            registry.register(ZerodhaBroker)
        """
        # Validate that broker_class is a subclass of BrokerProvider
        if not issubclass(broker_class, BrokerProvider):
            raise TypeError(
                f"{broker_class.__name__} must inherit from BrokerProvider"
            )

        # Create a temporary instance to get the provider_name
        # This validates that the broker implements required properties
        try:
            # Note: We instantiate here only to get the provider_name
            # The actual broker instances are created by BrokerManager
            temp_instance = broker_class()
            provider_name = temp_instance.provider_name
        except TypeError as error:
            raise TypeError(
                f"{broker_class.__name__} cannot be instantiated. "
                f"Ensure all abstract methods are implemented."
            ) from error
        except AttributeError as error:
            raise AttributeError(
                f"{broker_class.__name__} must implement the 'provider_name' property"
            ) from error

        # Validate provider_name format
        if not provider_name or not isinstance(provider_name, str):
            raise ValueError(
                f"provider_name must be a non-empty string, got: {provider_name}"
            )

        if not provider_name.islower():
            raise ValueError(
                f"provider_name must be lowercase, got: {provider_name}"
            )

        if " " in provider_name or "/" in provider_name:
            raise ValueError(
                f"provider_name must be URL-safe (no spaces or slashes), got: {provider_name}"
            )

        # Register the broker class
        self._brokers[provider_name] = broker_class

    def unregister(self, provider_name: str) -> None:
        """
        Unregister a broker provider.
        
        Useful for testing or hot-swapping broker implementations.
        
        Args:
            provider_name: The provider name to unregister
        
        Raises:
            BrokerNotFoundError: If provider is not registered
        """
        if provider_name not in self._brokers:
            raise BrokerNotFoundError(
                f"Broker provider '{provider_name}' is not registered",
                provider=provider_name,
            )
        del self._brokers[provider_name]

    def get(self, provider_name: str) -> Type[BrokerProvider]:
        """
        Get a registered broker class by provider name.
        
        Args:
            provider_name: The provider name (e.g., "zerodha", "fyers")
        
        Returns:
            Type[BrokerProvider]: The broker class (not an instance)
        
        Raises:
            BrokerNotFoundError: If provider is not registered
        
        Example:
            broker_class = registry.get("zerodha")
            broker_instance = broker_class()
        """
        if provider_name not in self._brokers:
            raise BrokerNotFoundError(
                f"Broker provider '{provider_name}' is not registered",
                provider=provider_name,
            )
        return self._brokers[provider_name]

    def is_registered(self, provider_name: str) -> bool:
        """
        Check if a broker provider is registered.
        
        Args:
            provider_name: The provider name to check
        
        Returns:
            bool: True if registered, False otherwise
        
        Example:
            if registry.is_registered("zerodha"):
                broker = registry.get("zerodha")
        """
        return provider_name in self._brokers

    def list_providers(self) -> list[str]:
        """
        List all registered broker provider names.
        
        Returns:
            list[str]: List of provider names
        
        Example:
            providers = registry.list_providers()
            # Returns: ["zerodha", "fyers", "groww"]
        """
        return list(self._brokers.keys())

    def list_brokers(self) -> list[dict[str, str]]:
        """
        List all registered brokers with their display names.
        
        Returns:
            list[dict]: List of dicts with 'provider' and 'display_name'
        
        Example:
            brokers = registry.list_brokers()
            # Returns: [
            #     {"provider": "zerodha", "display_name": "Zerodha Kite"},
            #     {"provider": "fyers", "display_name": "Fyers"},
            # ]
        """
        result = []
        for provider_name, broker_class in self._brokers.items():
            # Create temporary instance to get display_name
            temp_instance = broker_class()
            result.append({
                "provider": provider_name,
                "display_name": temp_instance.display_name,
                "supports_websocket": temp_instance.supports_websocket,
            })
        return result

    def clear(self) -> None:
        """
        Clear all registered brokers.
        
        Useful for testing to ensure a clean state.
        """
        self._brokers.clear()

    def __len__(self) -> int:
        """Return the number of registered brokers."""
        return len(self._brokers)

    def __contains__(self, provider_name: str) -> bool:
        """
        Check if a provider is registered using 'in' operator.
        
        Example:
            if "zerodha" in registry:
                print("Zerodha is registered")
        """
        return provider_name in self._brokers

    def __repr__(self) -> str:
        """Return string representation of the registry."""
        providers = ", ".join(self._brokers.keys())
        return f"BrokerRegistry({len(self._brokers)} brokers: {providers})"


# Global registry instance
# This is the singleton registry used throughout the application
_global_registry: BrokerRegistry | None = None


def get_global_registry() -> BrokerRegistry:
    """
    Get the global broker registry instance.
    
    This function returns a singleton BrokerRegistry that is shared
    across the entire application. All broker registrations should
    use this global instance.
    
    Returns:
        BrokerRegistry: The global registry instance
    
    Example:
        from app.services.brokers.registry import get_global_registry
        
        registry = get_global_registry()
        registry.register(ZerodhaBroker)
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = BrokerRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """
    Reset the global registry to a fresh state.
    
    This function is primarily useful for testing to ensure a clean
    registry state between test runs.
    
    Warning:
        This will remove all registered brokers. Use with caution
        in production code.
    """
    global _global_registry
    _global_registry = None
