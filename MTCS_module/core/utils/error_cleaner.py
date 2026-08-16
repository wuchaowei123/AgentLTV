"""
Error Message Cleaner Utility
=============================

Utility functions to clean up and format error messages for better user experience.
"""

import re
from typing import Optional


def clean_asyncio_error(error_message: Optional[str]) -> str:
    """
    Clean up asyncio-related error messages for better readability.
    
    Args:
        error_message: Raw error message that may contain asyncio warnings
        
    Returns:
        Cleaned error message
    """
    if not error_message:
        return "Unknown error"
    
    # Check for asyncio subprocess transport errors
    if ("BaseSubprocessTransport" in error_message and 
        "Event loop is closed" in error_message):
        return "Asyncio subprocess cleanup error (non-critical)"
    
    # Check for other asyncio-related errors
    asyncio_patterns = [
        r"Exception ignored in:.*BaseSubprocessTransport.*",
        r"RuntimeError: Event loop is closed",
        r"coroutine.*was never awaited",
        r"asyncio.*transport.*closed"
    ]
    
    for pattern in asyncio_patterns:
        if re.search(pattern, error_message, re.IGNORECASE | re.DOTALL):
            return "Asyncio cleanup error (non-critical)"
    
    # Truncate very long error messages
    if len(error_message) > 200:
        # Try to find the most relevant part of the error
        lines = error_message.split('\n')
        relevant_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('  File '):
                relevant_lines.append(line)
                if len(relevant_lines) >= 3:
                    break
        
        if relevant_lines:
            return ' | '.join(relevant_lines)
        else:
            return error_message[:200] + "..."
    
    return error_message


def is_critical_error(error_message: Optional[str]) -> bool:
    """
    Determine if an error message represents a critical error that needs attention.
    
    Args:
        error_message: Error message to analyze
        
    Returns:
        True if the error is critical, False if it's a non-critical warning
    """
    if not error_message:
        return True  # Unknown errors are considered critical
    
    # Non-critical patterns
    non_critical_patterns = [
        r"BaseSubprocessTransport",
        r"Event loop is closed",
        r"coroutine.*was never awaited",
        r"asyncio.*transport.*closed"
    ]
    
    for pattern in non_critical_patterns:
        if re.search(pattern, error_message, re.IGNORECASE | re.DOTALL):
            return False
    
    return True


def format_error_for_display(error_message: Optional[str], max_length: int = 100) -> str:
    """
    Format error message for display in terminal output.
    
    Args:
        error_message: Raw error message
        max_length: Maximum length for display
        
    Returns:
        Formatted error message
    """
    cleaned = clean_asyncio_error(error_message)
    
    if len(cleaned) <= max_length:
        return cleaned
    
    return cleaned[:max_length-3] + "..."