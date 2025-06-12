from app.app_exceptions.app_exception import AppException


class ResourceNotFoundException(AppException):
    def __init__(self, message="Resource not found"):
        self.message = message
        self.status_code = 404
        super().__init__(self.message, status_code=self.status_code)
