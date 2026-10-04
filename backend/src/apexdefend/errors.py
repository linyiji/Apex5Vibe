class AppError(Exception):
    def __init__(self, code, message, status=422, retryable=False, details=None):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
        self.retryable, self.details = retryable, details or {}

    def body(self, request_id="worker"):
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details,
            },
            "request_id": request_id,
        }
