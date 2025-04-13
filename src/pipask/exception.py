class PipaskException(Exception):
    pass


class HandoverToPipException(PipaskException):
    pass


class PipAskCodeExecutionDeniedException(PipaskException):
    """Exception raised when we are not allowed execute 3rd party code in a package"""

    def __init__(self, message: str):
        super().__init__(message)
