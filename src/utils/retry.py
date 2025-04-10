import asyncio
import logging
import random
from functools import wraps
from typing import Callable, TypeVar, Optional, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T')

def async_retry(
    max_retries: int = 3,
    initial_backoff: float = 2.0,
    max_backoff: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for async functions to retry operations with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_factor: Multiplier for backoff time after each retry
        jitter: Whether to add randomness to backoff time
        retryable_exceptions: Tuple of exceptions that should trigger a retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            retries = 0
            backoff = initial_backoff
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded. Last error: {str(e)}")
                        raise
                    
                    # Calculate backoff time with exponential increase
                    backoff = min(backoff * backoff_factor, max_backoff)
                    
                    # Add jitter if enabled (random value between 80-120% of backoff)
                    if jitter:
                        backoff = backoff * (0.8 + 0.4 * random.random())
                    
                    logger.info(f"Retry {retries}/{max_retries} after error: {str(e)}. "
                               f"Waiting {backoff:.2f}s before next attempt.")
                    
                    # Wait before retrying
                    await asyncio.sleep(backoff)
        
        return wrapper
    return decorator
