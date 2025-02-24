class UserError(Exception):
    """Exception raised when a user has most likely made a mistake"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"Error: {self.message}"
