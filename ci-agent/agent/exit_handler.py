"""
Exit Handler Module

Manages exit codes and provides a clean way to exit the application
with appropriate status codes based on the outcome.
"""

import sys
import logging
from enum import IntEnum

logger = logging.getLogger(__name__)


class ExitCode(IntEnum):
    """
    Standard exit codes for the CI/CD Fixer application.
    
    These codes help CI systems and scripts understand the outcome
    of the optimization process.
    """
    # Success - no issues found or all issues fixed
    SUCCESS = 0
    
    # Issues found but not fixed (suggestion mode)
    ISSUES_FOUND = 1
    
    # Fatal error - couldn't complete analysis
    FATAL_ERROR = 2
    
    # Configuration error
    CONFIG_ERROR = 3
    
    # File not found or inaccessible
    FILE_ERROR = 4
    
    # External service error (LLM, API, etc.)
    SERVICE_ERROR = 5
    
    # Timeout error
    TIMEOUT_ERROR = 6
    
    # User cancelled operation
    USER_CANCELLED = 7


def handle_exit(code: ExitCode, message: str = None) -> None:
    """
    Handle application exit with the appropriate code.
    
    Args:
        code: The exit code to use
        message: Optional message to log before exiting
    """
    if message:
        if code == ExitCode.SUCCESS:
            logger.info(f"✅ {message}")
        elif code in (ExitCode.ISSUES_FOUND, ExitCode.USER_CANCELLED):
            logger.warning(f"⚠️  {message}")
        else:
            logger.error(f"❌ {message}")
    
    # Log exit code in debug mode
    logger.debug(f"Exiting with code {code} ({code.name})")
    
    # Exit with the specified code
    sys.exit(int(code))


def get_exit_code_description(code: ExitCode) -> str:
    """
    Get a human-readable description of an exit code.
    
    Args:
        code: The exit code
        
    Returns:
        Description of what the exit code means
    """
    descriptions = {
        ExitCode.SUCCESS: "Operation completed successfully",
        ExitCode.ISSUES_FOUND: "Issues were found in CI/CD configuration",
        ExitCode.FATAL_ERROR: "A fatal error occurred during execution",
        ExitCode.CONFIG_ERROR: "Configuration file is invalid or missing",
        ExitCode.FILE_ERROR: "File not found or inaccessible",
        ExitCode.SERVICE_ERROR: "External service error (LLM, API, etc.)",
        ExitCode.TIMEOUT_ERROR: "Operation timed out",
        ExitCode.USER_CANCELLED: "Operation cancelled by user",
    }
    
    return descriptions.get(code, f"Unknown exit code: {code}") 