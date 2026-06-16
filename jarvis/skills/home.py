import logging

logger = logging.getLogger(__name__)


def control_device(device: str, action: str, value: str = None) -> str:
    detail = f" to {value}" if value else ""
    message = f"Device '{device}' action '{action}'{detail} executed."
    logger.info(message)
    return message
