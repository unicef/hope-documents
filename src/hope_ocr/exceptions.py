class DocumentError(BaseException):
    pass


class InvalidImageError(DocumentError):
    pass


class ExtractionError(DocumentError):
    pass
