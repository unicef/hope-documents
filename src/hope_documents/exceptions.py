class DocumentError(BaseException):
    pass


class InvalidImageError(DocumentError):
    pass


class ExtractionError(DocumentError):
    pass


class FlowTimeoutError(Exception):
    pass


class FlowLockoutError(Exception):
    pass


class ValidationFailedError(Exception):
    pass
