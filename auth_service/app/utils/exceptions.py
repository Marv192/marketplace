class TokenExpiredError(Exception):
    default_message = 'Token expired'
    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)

class InvalidTokenError(Exception):
    default_message = 'Invalid token'
    def __init__(self, message: str| None = None):
        super().__init__(message or self.default_message)

class PermissionDeniedError(Exception):
    default_message = 'Permission denied'
    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)