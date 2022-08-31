UNKNOWN_EXCEPTION = "Great job! You found a bug in the SIMBA Python SDK!\nPlease report the above stacktrace to https://github.com/SIMBAChain/libsimba/issues"

SIMBA_INVALID_URL_EXCEPTION = (
    "Please ensure that you have properly configured the LIBSIMBA_BASE_API_URL"
)

SIMBA_REQUEST_EXCEPTION = "Please check the inputs or query params and that you have properly configured the SDK according to the documentation."


class LibSimbaException(Exception):
    def __init__(self, error: str = None, message: str = ""):
        error = error or message
        super().__init__(error)


class SimbaInvalidURLException(LibSimbaException):
    def __init__(self):
        super().__init__(SIMBA_INVALID_URL_EXCEPTION)


class SimbaRequestException(LibSimbaException):
    def __init__(self):
        super().__init__(SIMBA_REQUEST_EXCEPTION)
