class AdapterError(Exception):

    def __init__(self, code, message, http_status, field=None):
        super().__init__(message)

        self.code = code
        self.message = message
        self.http_status = http_status
        self.field = field

    def to_dict(self):
        return {
            "error_code": self.code,
            "message": self.message,
            "field": self.field
        }