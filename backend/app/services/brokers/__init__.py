"""
Broker integration module for Stratum platform.

This module provides the foundation for integrating multiple broker providers
into the platform. It follows the strategy pattern to allow seamless addition
of new brokers without modifying existing code.

Architecture:
    - base.py: Abstract broker interface defining required capabilities
    - exceptions.py: Broker-specific exception hierarchy
    - types.py: Shared types and enums used across brokers
    - constants.py: Common constants for broker operations
    - registry.py: Broker registration and discovery system
    - manager.py: Broker factory for resolving broker implementations

Usage:
    from app.services.brokers import get_broker_manager
    
    manager = get_broker_manager()
    broker = manager.get_broker("zerodha")
    positions = await broker.get_positions(user_id)
"""

from app.services.brokers.manager import BrokerManager, get_broker_manager

__all__ = ["BrokerManager", "get_broker_manager"]
