from enum import Enum, Flag, auto


class PermissionType(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class EventMessageType(str, Enum):
    GROUP_MESSAGE = "group"
    PRIVATE_MESSAGE = "private"


class PlatformAdapterType(Flag):
    TELEGRAM = auto()
    QQOFFICIAL = auto()
    QQOFFICIAL_WEBHOOK = auto()
    ONEBOT = auto()
    DISCORD = auto()


def _noop_decorator(*_args, **_kwargs):
    def decorator(func):
        return func

    return decorator


class filter:  # noqa: N801
    EventMessageType = EventMessageType
    PlatformAdapterType = PlatformAdapterType
    command = staticmethod(_noop_decorator)
    permission_type = staticmethod(_noop_decorator)
    event_message_type = staticmethod(_noop_decorator)
    platform_adapter_type = staticmethod(_noop_decorator)
    on_platform_loaded = staticmethod(_noop_decorator)
