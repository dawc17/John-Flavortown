class BotError(Exception):
    """Base error type for user-facing failures."""


class APIError(BotError):
    """Flavortown API error."""


class HackatimeError(BotError):
    """Hackatime API error."""


class StorageError(BotError):
    """Storage layer error."""
