"""Errors raised by the simulated banks and switch."""


class SimError(Exception):
    def __init__(self, code: str, op: str, detail: str = ""):
        self.code = code
        self.op = op
        self.detail = detail
        super().__init__(detail or f"{code} during {op}")


class SimTimeout(SimError):
    def __init__(self, op: str):
        super().__init__("timeout", op)


class SimConnectionError(SimError):
    def __init__(self, op: str):
        super().__init__("connection_error", op)


class SimNotFound(SimError):
    def __init__(self, op: str, identifier: str):
        self.identifier = identifier
        super().__init__("not_found", op, f"{op} found no record for {identifier}")
