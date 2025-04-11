class PipaskException(Exception):
    pass


class HandoverToPipException(PipaskException):
    pass


class PipAskResolutionException(PipaskException):
    """Exception raised when pipask cannot resolve the dependencies with a given method"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class PipAskCodeExecutionDeniedException(PipAskResolutionException):
    """Exception raised when we are not allowed execute 3rd party code in a package"""

    def __init__(self, message: str):
        super().__init__(message)
