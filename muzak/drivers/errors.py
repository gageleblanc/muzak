class MQLError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class MQLSyntaxError(MQLError):
    pass

class CommandNotFound(MQLError):
    pass