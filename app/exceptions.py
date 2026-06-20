class BusinessValidationError(Exception):
    def __init__(self, code: str, message: str, missing_params: list = None, detail: dict = None):
        self.code = code
        self.message = message
        self.missing_params = missing_params
        self.detail = detail
