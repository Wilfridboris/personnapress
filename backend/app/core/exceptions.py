class PlatformError(Exception):
    def __init__(self, platform: str, status_code: int, message: str):
        self.platform = platform
        self.status_code = status_code
        self.message = message
        super().__init__(f"{platform} returned {status_code} — {message}")
