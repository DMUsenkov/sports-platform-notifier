# Обновление bot/main.py

import asyncio
import logging
import sys
import datetime
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config.config import TELEGRAM_BOT_TOKEN
from utils.logger import setup_logger
from database.connection import init_db
from bot.handlers.user import register_user_handlers
from bot.handlers.notification import register_notification_handlers, process_pending_notifications
from bot.handlers.match import register_match_handlers  # Новый импорт
from bot.handlers.championship import register_championship_handlers  # Новый импорт
from database.repositories.notification_repository import NotificationRepository
from bot.handlers.callback_handlers import register_callback_handlers

# Настройка логирования
logger = setup_logger("bot")

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрация обработчиков
# Обновление в bot/main.py

# Добавим импорт

register_user_handlers(dp)
register_notification_handlers(dp)
register_match_handlers(dp)
register_championship_handlers(dp)
register_callback_handlers(dp)  # Добавляем новую регистрацию

# Флаг для контроля фоновых задач
background_tasks_running = False


# Асинхронная функция для периодической проверки уведомлений
async def check_notifications_periodically():
    while background_tasks_running:
        try:
            # Проверка и отправка уведомлений
            await process_pending_notifications(bot)

            # Создание напоминаний о матчах (раз в день в 12:00)
            now = datetime.datetime.now()
            if now.hour == 12 and now.minute == 0:
                count = NotificationRepository.create_match_reminder_notifications()
                logger.info(f"Создано {count} напоминаний о матчах")

            # Удаление старых уведомлений (раз в день в 3:00)
            if now.hour == 3 and now.minute == 0:
                count = NotificationRepository.delete_old_sent_notifications(days=30)
                logger.info(f"Удалено {count} старых уведомлений")

        except Exception as e:
            logger.error(f"Ошибка при выполнении фоновых задач: {e}")

        # Ждем 10 секунд перед следующей проверкой
        await asyncio.sleep(10)


async def on_startup(dispatcher):
    """
    Функция, выполняемая при запуске бота

    Args:
        dispatcher: Диспетчер Aiogram
    """
    global background_tasks_running

    try:
        # Инициализация базы данных
        init_db()
        logger.info("База данных инициализирована")

        # Запускаем фоновую задачу проверки уведомлений
        background_tasks_running = True
        asyncio.create_task(check_notifications_periodically())
        logger.info("Фоновая задача проверки уведомлений запущена")

        # Оповещение об успешном запуске бота
        logger.info("Бот успешно запущен")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)


async def on_shutdown(dispatcher):
    """
    Функция, выполняемая при остановке бота

    Args:
        dispatcher: Диспетчер Aiogram
    """
    global background_tasks_running

    try:
        # Останавливаем фоновые задачи
        background_tasks_running = False
        logger.info("Фоновые задачи остановлены")

        # Закрытие соединения с хранилищем состояний
        await dispatcher.storage.close()
        await dispatcher.storage.wait_closed()
        logger.info("Хранилище состояний закрыто")

        # Оповещение об успешной остановке бота
        logger.info("Бот успешно остановлен")
    except Exception as e:
        logger.error(f"Ошибка при остановке бота: {e}")


if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True
    )