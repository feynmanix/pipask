class PipaskException(Exception):
    pass


class PipAskResolutionException(PipaskException):
    """Exception raised when pipask cannot resolve the dependencies with a given method"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
