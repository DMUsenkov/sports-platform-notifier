# Новый файл bot/handlers/callback_handlers.py
import logging
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.logger import get_logger
from database.repositories.user_repository import UserRepository
from api.client import ApiClient

logger = get_logger("callback_handlers")
api_client = None  # Будет инициализирован при регистрации обработчиков


def register_callback_handlers(dp: Dispatcher):
    """
    Регистрация обработчиков для всех колбэков

    Args:
        dp: Диспетчер Aiogram
    """
    global api_client
    from api.client import ApiClient
    api_client = ApiClient()

    # Общий обработчик для всех типов колбэков
    @dp.callback_query_handler(lambda c: True)
    async def process_callback_query(callback_query: types.CallbackQuery):
        """
        Общий обработчик всех callback queries

        Args:
            callback_query: Callback query от пользователя
        """
        callback_data = callback_query.data
        logger.info(f"Получен callback query с данными: {callback_data}")

        # Проверяем, что callback_data существует
        if not callback_data:
            logger.warning("Получен пустой callback_data")
            await callback_query.answer("Ошибка: пустой callback_data")
            return

        # Разбираем callback_data
        try:
            parts = callback_data.split('_')
            if len(parts) < 3:
                logger.warning(f"Некорректный формат callback_data: {callback_data}")
                await callback_query.answer("Ошибка: некорректный формат")
                return

            action = parts[0]  # accept или decline
            invitation_type = parts[1]  # team или committee
            invitation_id = int(parts[2])  # ID приглашения

            logger.info(f"Разобран callback_data: action={action}, type={invitation_type}, id={invitation_id}")

            # Получаем пользователя
            user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
            if not user:
                logger.warning(f"Пользователь не найден для Telegram ID {callback_query.from_user.id}")
                await callback_query.answer("Ошибка: пользователь не найден")
                await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
                return

            # Сообщаем пользователю о начале обработки
            await callback_query.answer("Обрабатываем ваше решение...")

            # Получаем ID пользователя
            user_id = user.id if hasattr(user, 'id') else user['id'] if isinstance(user,
                                                                                   dict) and 'id' in user else None
            if user_id is None:
                logger.error("Не удалось определить ID пользователя")
                raise ValueError("Не удалось определить ID пользователя")

            # Вызываем соответствующий метод API
            result = None
            success_message = ""

            if action == "accept" and invitation_type == "team":
                logger.info(f"Вызываем API для принятия приглашения в команду {invitation_id}")
                result = await api_client.accept_team_invitation(invitation_id)
                success_message = "✅ Вы приняли приглашение в команду!"

            elif action == "decline" and invitation_type == "team":
                logger.info(f"Вызываем API для отклонения приглашения в команду {invitation_id}")
                result = await api_client.decline_team_invitation(invitation_id)
                success_message = "❌ Вы отклонили приглашение в команду."

            elif action == "accept" and invitation_type == "committee":
                logger.info(f"Вызываем API для принятия приглашения в оргкомитет {invitation_id}")
                result = await api_client.accept_committee_invitation(invitation_id)
                success_message = "✅ Вы приняли приглашение в оргкомитет!"

            elif action == "decline" and invitation_type == "committee":
                logger.info(f"Вызываем API для отклонения приглашения в оргкомитет {invitation_id}")
                result = await api_client.decline_committee_invitation(invitation_id)
                success_message = "❌ Вы отклонили приглашение в оргкомитет."

            else:
                logger.warning(f"Неизвестная комбинация action/type: {action}/{invitation_type}")
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❓ Неизвестная операция.",
                    reply_markup=None
                )
                return

            # Логируем результат API
            logger.info(f"Результат API: {result}")

            # Обрабатываем результат вызова API
            if result and "error" not in result:
                # Успешно
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n{success_message}",
                    reply_markup=None
                )
            else:
                # Ошибка
                error_msg = result.get("error", "неизвестная ошибка") if result else "неизвестная ошибка"
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось выполнить операцию: {error_msg}",
                    reply_markup=None
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке callback_query: {e}", exc_info=True)
            try:
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.",
                    reply_markup=None
                )
            except Exception as e2:
                logger.error(f"Невозможно отправить сообщение об ошибке: {e2}")