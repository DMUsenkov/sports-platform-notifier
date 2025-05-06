import logging
import sys
from logging.handlers import RotatingFileHandler
import os

from config.config import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT


def setup_logger(name="sports_platform_notifier"):
    """
    Настройка логирования для приложения

    Args:
        name: Имя логгера

    Returns:
        Настроенный объект логгера
    """
    # Создаем логгер
    logger = logging.getLogger(name)

    # Устанавливаем уровень логирования
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    # Если у логгера уже есть обработчики, значит он уже настроен
    if logger.handlers:
        return logger

    # Создаем форматтер для логов
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)

    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Создаем каталог для хранения логов
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Создаем обработчик для записи в файл
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, f"{name}.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name=None):
    """
    Получение логгера для компонента приложения

    Args:
        name: Имя компонента (опционально)

    Returns:
        Объект логгера
    """
    if name:
        return logging.getLogger(f"sports_platform_notifier.{name}")
    return logging.getLogger("sports_platform_notifier")