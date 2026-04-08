"""
Custom exception classes for the application.
Provides structured error handling with proper HTTP status codes.
"""
from typing import Any, Dict, Optional


class BroskiBotException(Exception):
    """Base exception for all BROski Bot errors."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize exception.
        
        Args:
            message: Error message
            code: Error code for client identification
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}


# Database Exceptions
class DatabaseException(BroskiBotException):
    """Base exception for database errors."""
    pass


class RecordNotFoundException(DatabaseException):
    """Raised when a database record is not found."""
    
    def __init__(self, model: str, identifier: Any) -> None:
        super().__init__(
            message=f"{model} not found",
            code="RECORD_NOT_FOUND",
            details={"model": model, "identifier": str(identifier)},
        )


class DuplicateRecordException(DatabaseException):
    """Raised when attempting to create a duplicate record."""
    
    def __init__(self, model: str, field: str, value: Any) -> None:
        super().__init__(
            message=f"{model} with {field}={value} already exists",
            code="DUPLICATE_RECORD",
            details={"model": model, "field": field, "value": str(value)},
        )


# Business Logic Exceptions
class BusinessLogicException(BroskiBotException):
    """Base exception for business logic errors."""
    pass


class InsufficientBalanceException(BusinessLogicException):
    """Raised when user has insufficient balance for transaction."""
    
    def __init__(self, required: int, available: int) -> None:
        super().__init__(
            message=f"Insufficient balance: need {required}, have {available}",
            code="INSUFFICIENT_BALANCE",
            details={"required": required, "available": available},
        )


class DailyLimitExceededException(BusinessLogicException):
    """Raised when user exceeds daily action limit."""
    
    def __init__(self, action: str, limit: int) -> None:
        super().__init__(
            message=f"Daily limit exceeded for {action} (limit: {limit})",
            code="DAILY_LIMIT_EXCEEDED",
            details={"action": action, "limit": limit},
        )


class SessionActiveException(BusinessLogicException):
    """Raised when trying to start a session while one is active."""
    
    def __init__(self, session_type: str) -> None:
        super().__init__(
            message=f"{session_type} session already active",
            code="SESSION_ACTIVE",
            details={"session_type": session_type},
        )


class SessionNotFoundException(BusinessLogicException):
    """Raised when trying to end a non-existent session."""
    
    def __init__(self, session_type: str) -> None:
        super().__init__(
            message=f"No active {session_type} session found",
            code="SESSION_NOT_FOUND",
            details={"session_type": session_type},
        )


class InvalidAmountException(BusinessLogicException):
    """Raised when an amount is invalid (negative, zero, etc)."""
    
    def __init__(self, amount: int, reason: str) -> None:
        super().__init__(
            message=f"Invalid amount {amount}: {reason}",
            code="INVALID_AMOUNT",
            details={"amount": amount, "reason": reason},
        )


# Validation Exceptions
class ValidationException(BroskiBotException):
    """Base exception for validation errors."""
    pass


class InvalidInputException(ValidationException):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, value: Any, reason: str) -> None:
        super().__init__(
            message=f"Invalid {field}: {reason}",
            code="INVALID_INPUT",
            details={"field": field, "value": str(value), "reason": reason},
        )


# Rate Limiting Exceptions
class RateLimitException(BroskiBotException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            message=f"Rate limit exceeded. Try again in {retry_after}s",
            code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


# Permission Exceptions
class PermissionDeniedException(BroskiBotException):
    """Raised when user lacks required permissions."""
    
    def __init__(self, action: str, required_permission: str) -> None:
        super().__init__(
            message=f"Permission denied for {action}",
            code="PERMISSION_DENIED",
            details={"action": action, "required_permission": required_permission},
        )


# Integration Exceptions
class ExternalServiceException(BroskiBotException):
    """Base exception for external service errors."""
    pass


class APIException(ExternalServiceException):
    """Raised when external API call fails."""
    
    def __init__(self, service: str, status_code: int, message: str) -> None:
        super().__init__(
            message=f"{service} API error: {message}",
            code="API_ERROR",
            details={
                "service": service,
                "status_code": status_code,
                "message": message,
            },
        )


class CacheException(ExternalServiceException):
    """Raised when cache operations fail."""
    
    def __init__(self, operation: str, key: str) -> None:
        super().__init__(
            message=f"Cache {operation} failed for key: {key}",
            code="CACHE_ERROR",
            details={"operation": operation, "key": key},
        )
