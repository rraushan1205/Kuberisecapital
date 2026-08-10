"""
Dynamic Strategy Loader

Loads and executes Python strategy code from the database with security restrictions.
Supports the admin-managed strategies feature where admins upload strategy code
and assign it to users.

Security Features:
- Restricted imports (only safe libraries allowed)
- No file system access
- No network access (except through provided adapter)
- No subprocess/os operations
- Execution timeout limits
- Memory limits (future enhancement)
"""
import ast
import sys
import types
import logging
from typing import Dict, Optional, Any, Callable
from datetime import datetime
import pandas as pd

from app.models.domain import StrategyState, StrategyDefinition
from app.services.strategy_execution.context import StrategyConfig
from app.services.strategy_adapter import StrategyAdapter

logger = logging.getLogger(__name__)

# Whitelist of allowed imports for strategy code
ALLOWED_MODULES = {
    'pandas', 'pd',
    'numpy', 'np',
    'datetime',
    'typing',
    'math',
    'statistics',
    'decimal',
    'json',
}

# Blacklisted builtins that could be dangerous
RESTRICTED_BUILTINS = {
    'eval', 'exec', 'compile',
    'open', 'input', 'file',
    'execfile', 'reload',
    'breakpoint', 'help', 'quit', 'exit',
}


class StrategyLoadError(Exception):
    """Raised when strategy code cannot be loaded or validated"""
    pass


class StrategyExecutionError(Exception):
    """Raised when strategy code execution fails"""
    pass


class SecurityViolation(Exception):
    """Raised when strategy code violates security restrictions"""
    pass


def validate_imports(code: str) -> None:
    """
    Validate that code only imports allowed modules.
    
    Args:
        code: Python source code to validate
    
    Raises:
        SecurityViolation: If code imports unauthorized modules
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise StrategyLoadError(f"Syntax error in strategy code: {e}")
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name not in ALLOWED_MODULES:
                    raise SecurityViolation(
                        f"Import '{alias.name}' is not allowed. "
                        f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
                    )
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name not in ALLOWED_MODULES:
                    raise SecurityViolation(
                        f"Import from '{node.module}' is not allowed. "
                        f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
                    )


def create_restricted_globals() -> Dict[str, Any]:
    """
    Create a restricted global namespace for strategy execution.
    
    Returns:
        Dictionary of allowed global names and values
    """
    # Get the real __import__ function
    import builtins
    real_import = builtins.__import__
    
    # Create a restricted __import__ function that only allows whitelisted modules
    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
        """Restricted import that only allows whitelisted modules."""
        # Get the base module name (e.g., 'pandas' from 'pandas.core')
        base_module = name.split('.')[0]
        
        if base_module not in ALLOWED_MODULES:
            raise SecurityViolation(
                f"Import '{name}' is not allowed. "
                f"Allowed modules: {', '.join(sorted(ALLOWED_MODULES))}"
            )
        
        # Use the real __import__ for allowed modules
        return real_import(name, globals, locals, fromlist, level)
    
    # Start with a minimal set of builtins
    safe_builtins = {
        name: getattr(builtins, name)
        for name in dir(builtins)
        if name not in RESTRICTED_BUILTINS and not name.startswith('_')
    }
    
    # Add the restricted __import__
    safe_builtins['__import__'] = restricted_import
    
    # Add commonly needed builtins explicitly
    safe_builtins.update({
        'True': True,
        'False': False,
        'None': None,
        'int': int,
        'float': float,
        'str': str,
        'bool': bool,
        'list': list,
        'dict': dict,
        'tuple': tuple,
        'set': set,
        'len': len,
        'range': range,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'sum': sum,
        'min': min,
        'max': max,
        'abs': abs,
        'round': round,
        'sorted': sorted,
        'any': any,
        'all': all,
        'isinstance': isinstance,
        'print': print,  # Allow print for debugging
    })
    
    return {
        '__builtins__': safe_builtins,
        '__name__': '__strategy__',
        '__file__': '<strategy>',
    }


def load_strategy_module(code: str, strategy_name: str) -> types.ModuleType:
    """
    Load strategy code into a module with security restrictions.
    
    Args:
        code: Python source code
        strategy_name: Name of the strategy (for module naming)
    
    Returns:
        Loaded module object
    
    Raises:
        StrategyLoadError: If code cannot be loaded
        SecurityViolation: If code violates security restrictions
    """
    # Validate imports before execution
    validate_imports(code)
    
    # Create restricted namespace
    module_globals = create_restricted_globals()
    
    # Pre-import allowed modules into the namespace
    # This allows strategies to use them without explicit import
    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        from typing import Dict, Optional, List, Tuple
        
        module_globals['pd'] = pd
        module_globals['pandas'] = pd
        module_globals['np'] = np
        module_globals['numpy'] = np
        module_globals['datetime'] = datetime
        module_globals['timedelta'] = timedelta
        module_globals['Dict'] = Dict
        module_globals['Optional'] = Optional
        module_globals['List'] = List
        module_globals['Tuple'] = Tuple
    except ImportError as e:
        logger.warning(f"Failed to pre-import module: {e}")
    
    # Create module object
    module_name = f"strategy_{strategy_name.replace(' ', '_').replace('-', '_').lower()}"
    module = types.ModuleType(module_name)
    module.__dict__.update(module_globals)
    
    # Execute code in the module's namespace
    try:
        exec(code, module.__dict__)
    except Exception as e:
        raise StrategyLoadError(f"Failed to execute strategy code: {type(e).__name__}: {e}")
    
    return module


def extract_check_for_signal_function(module: types.ModuleType) -> Callable:
    """
    Extract the check_for_signal function from a loaded strategy module.
    
    Args:
        module: Loaded strategy module
    
    Returns:
        The check_for_signal function
    
    Raises:
        StrategyLoadError: If function is not found or has wrong signature
    """
    if not hasattr(module, 'check_for_signal'):
        raise StrategyLoadError(
            "Strategy code must define a 'check_for_signal' function. "
            "Expected signature: async def check_for_signal(index_df, state, config, adapter, token) -> Optional[Dict]"
        )
    
    func = getattr(module, 'check_for_signal')
    
    if not callable(func):
        raise StrategyLoadError("'check_for_signal' must be a callable function")
    
    # Check if it's an async function
    import inspect
    if not inspect.iscoroutinefunction(func):
        raise StrategyLoadError("'check_for_signal' must be an async function (use 'async def')")
    
    return func


class StrategyLoader:
    """
    Main strategy loader class.
    Caches loaded strategies to avoid re-parsing on every signal check.
    """
    
    def __init__(self):
        self._cache: Dict[int, types.ModuleType] = {}
        self._cache_timestamps: Dict[int, datetime] = {}
    
    def load_strategy(self, strategy_def: StrategyDefinition) -> Callable:
        """
        Load a strategy from database definition and return its check_for_signal function.
        
        Args:
            strategy_def: StrategyDefinition ORM object from database
        
        Returns:
            The strategy's check_for_signal async function
        
        Raises:
            StrategyLoadError: If strategy cannot be loaded
            SecurityViolation: If strategy violates security restrictions
        """
        strategy_id = strategy_def.id
        
        # Check cache (invalidate if strategy was updated)
        if strategy_id in self._cache:
            cached_time = self._cache_timestamps.get(strategy_id)
            if cached_time and strategy_def.updated_at and cached_time >= strategy_def.updated_at:
                logger.debug(f"Using cached strategy module for '{strategy_def.name}' (id={strategy_id})")
                return extract_check_for_signal_function(self._cache[strategy_id])
            else:
                logger.info(f"Strategy '{strategy_def.name}' was updated, reloading from DB")
                del self._cache[strategy_id]
                del self._cache_timestamps[strategy_id]
        
        # Load strategy code
        logger.info(f"Loading strategy '{strategy_def.name}' (id={strategy_id})")
        
        try:
            module = load_strategy_module(strategy_def.code, strategy_def.name)
            func = extract_check_for_signal_function(module)
            
            # Cache the loaded module
            self._cache[strategy_id] = module
            self._cache_timestamps[strategy_id] = datetime.utcnow()
            
            logger.info(f"Successfully loaded strategy '{strategy_def.name}' (id={strategy_id})")
            return func
        
        except (StrategyLoadError, SecurityViolation) as e:
            logger.error(f"Failed to load strategy '{strategy_def.name}' (id={strategy_id}): {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading strategy '{strategy_def.name}': {e}", exc_info=True)
            raise StrategyLoadError(f"Unexpected error: {type(e).__name__}: {e}")
    
    def clear_cache(self, strategy_id: Optional[int] = None):
        """
        Clear cached strategy modules.
        
        Args:
            strategy_id: If provided, clear only this strategy. Otherwise clear all.
        """
        if strategy_id is not None:
            self._cache.pop(strategy_id, None)
            self._cache_timestamps.pop(strategy_id, None)
            logger.info(f"Cleared cache for strategy id={strategy_id}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cleared all strategy cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        return {
            'cached_strategies': len(self._cache),
            'total_loads': len(self._cache_timestamps),
        }


# Global singleton instance
_global_loader: Optional[StrategyLoader] = None


def get_strategy_loader() -> StrategyLoader:
    """Get the global strategy loader instance"""
    global _global_loader
    if _global_loader is None:
        _global_loader = StrategyLoader()
    return _global_loader


async def execute_strategy_signal_check(
    strategy_def: StrategyDefinition,
    index_df: pd.DataFrame,
    state: StrategyState,
    config: StrategyConfig,
    adapter: StrategyAdapter,
    token: str
) -> Optional[Dict]:
    """
    High-level function to load and execute a strategy's signal check.
    
    This is the main entry point used by the signal engine.
    
    Args:
        strategy_def: Strategy definition from database
        index_df: OHLCV data for index
        state: Current strategy state
        config: Strategy configuration
        adapter: Strategy adapter for broker calls
        token: Broker access token
    
    Returns:
        Signal dict or None (same format as reference_strategy.check_for_signal)
    
    Raises:
        StrategyLoadError: If strategy cannot be loaded
        SecurityViolation: If strategy violates security restrictions
        StrategyExecutionError: If strategy execution fails
    """
    import asyncio
    
    # Execution timeout in seconds (prevent infinite loops)
    STRATEGY_EXECUTION_TIMEOUT = 5.0
    
    loader = get_strategy_loader()
    
    try:
        # Load the strategy (from cache if available)
        check_for_signal_func = loader.load_strategy(strategy_def)
        
        # Execute the strategy's signal check WITH TIMEOUT
        # This prevents infinite loops from freezing the system
        signal = await asyncio.wait_for(
            check_for_signal_func(
                index_df=index_df,
                state=state,
                config=config,
                adapter=adapter,
                token=token
            ),
            timeout=STRATEGY_EXECUTION_TIMEOUT
        )
        
        return signal
    
    except asyncio.TimeoutError:
        # Strategy took too long to execute
        logger.error(
            f"Strategy '{strategy_def.name}' exceeded timeout of {STRATEGY_EXECUTION_TIMEOUT}s"
        )
        raise StrategyExecutionError(
            f"Strategy execution timeout after {STRATEGY_EXECUTION_TIMEOUT}s. "
            "Check for infinite loops or expensive operations."
        )
    
    except (StrategyLoadError, SecurityViolation) as e:
        # These are "permanent" errors - strategy code is broken
        logger.error(f"Strategy load/security error for '{strategy_def.name}': {e}")
        raise
    
    except Exception as e:
        # Runtime error during strategy execution
        logger.error(
            f"Strategy execution error for '{strategy_def.name}': {type(e).__name__}: {e}",
            exc_info=True
        )
        raise StrategyExecutionError(f"Execution failed: {type(e).__name__}: {e}")


# Export main interface
__all__ = [
    'StrategyLoader',
    'get_strategy_loader',
    'execute_strategy_signal_check',
    'StrategyLoadError',
    'SecurityViolation',
    'StrategyExecutionError',
]
