import logging
import json
from aiogram import Dispatcher, types
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, UserDeactivated, TelegramAPIError
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from config.config import MAX_RPS
from utils.logger import get_logger
from database.models import NotificationType
from database.repositories.notification_repository import NotificationRepository
from database.repositories.user_repository import UserRepository
from bot.messages.templates import (
    TEAM_APPLICATION_MESSAGE,
    APPLICATION_CANCEL_MESSAGE,
    CHAMPIONSHIP_CANCEL_MESSAGE,
    NEW_MATCH_MESSAGE,
    MATCH_RESCHEDULE_MESSAGE,
    PLAYOFF_RESULT_MESSAGE,
    MATCH_REMINDER_MESSAGE,
    NEW_CHAMPIONSHIP_MESSAGE,
    COMMITTEE_MESSAGE,
    TEAM_INVITATION_MESSAGE,
    COMMITTEE_INVITATION_MESSAGE
)
from bot.keyboards.keyboards import get_invitation_keyboard, get_start_keyboard

logger = get_logger("notification_handler")
api_client = None  # Будет инициализирован при регистрации обработчиков


# Восстановленная функция для отправки уведомлений
async def send_notification(bot, notification, user):
    """
    Отправка уведомления пользователю

    Args:
        bot: Объект бота Telegram
        notification: Объект уведомления
        user: Объект пользователя

    Returns:
        bool: True, если уведомление успешно отправлено, иначе False
    """
    if not user.telegram_id:
        logger.warning(f"Пользователь {user.id} не имеет привязанного Telegram ID")
        return False

    try:
        # Изменено с metadata на metadata_json
        metadata = json.loads(notification.metadata_json) if notification.metadata_json else {}

        # Формируем текст сообщения в зависимости от типа уведомления
        message_text = ""
        markup = None

        if notification.type == NotificationType.TEAM_APPLICATION:
            message_text = TEAM_APPLICATION_MESSAGE.format(
                team_name=metadata.get("team_name", ""),
                championship_name=metadata.get("championship_name", ""),
                application_deadline=metadata.get("application_deadline", "")
            )

        elif notification.type == NotificationType.APPLICATION_CANCEL:
            message_text = APPLICATION_CANCEL_MESSAGE.format(
                status=metadata.get("status", "отклонена"),
                team_name=metadata.get("team_name", ""),
                championship_name=metadata.get("championship_name", ""),
                reason=metadata.get("reason", "Причина не указана")
            )

        elif notification.type == NotificationType.CHAMPIONSHIP_CANCEL:
            message_text = CHAMPIONSHIP_CANCEL_MESSAGE.format(
                status=metadata.get("status", "отменен"),
                championship_name=metadata.get("championship_name", ""),
                additional_info=metadata.get("additional_info", "")
            )

        elif notification.type == NotificationType.NEW_MATCH:
            message_text = NEW_MATCH_MESSAGE.format(
                championship_name=metadata.get("championship_name", ""),
                opponent_name=metadata.get("opponent_name", ""),
                match_date=metadata.get("match_date", ""),
                match_time=metadata.get("match_time", ""),
                venue=metadata.get("venue", ""),
                address=metadata.get("address", "")
            )

        elif notification.type == NotificationType.MATCH_RESCHEDULE:
            message_text = MATCH_RESCHEDULE_MESSAGE.format(
                championship_name=metadata.get("championship_name", ""),
                opponent_name=metadata.get("opponent_name", ""),
                new_date=metadata.get("new_date", ""),
                new_time=metadata.get("new_time", ""),
                new_venue=metadata.get("new_venue", ""),
                new_address=metadata.get("new_address", ""),
                old_date=metadata.get("old_date", ""),
                old_time=metadata.get("old_time", "")
            )

        elif notification.type == NotificationType.PLAYOFF_RESULT:
            message_text = PLAYOFF_RESULT_MESSAGE.format(
                team_name=metadata.get("team_name", ""),
                result=metadata.get("result", "прошла"),
                championship_name=metadata.get("championship_name", ""),
                additional_info=metadata.get("additional_info", "")
            )

        elif notification.type == NotificationType.MATCH_REMINDER:
            message_text = MATCH_REMINDER_MESSAGE.format(
                championship_name=metadata.get("championship_name", ""),
                opponent_name=metadata.get("opponent_name", ""),
                match_date=metadata.get("match_date", ""),
                match_time=metadata.get("match_time", ""),
                venue=metadata.get("venue", ""),
                address=metadata.get("address", "")
            )

        elif notification.type == NotificationType.NEW_CHAMPIONSHIP:
            message_text = NEW_CHAMPIONSHIP_MESSAGE.format(
                championship_name=metadata.get("championship_name", ""),
                sport_type=metadata.get("sport_type", ""),
                deadline=metadata.get("deadline", ""),
                city=metadata.get("city", ""),
                description=metadata.get("description", "")
            )

        elif notification.type == NotificationType.COMMITTEE_MESSAGE:
            message_text = COMMITTEE_MESSAGE.format(
                championship_name=metadata.get("championship_name", ""),
                message=metadata.get("message", "")
            )

        elif notification.type == NotificationType.TEAM_INVITATION:
            message_text = TEAM_INVITATION_MESSAGE.format(
                team_name=metadata.get("team_name", ""),
                sport_type=metadata.get("sport_type", ""),
                captain_name=metadata.get("captain_name", "")
            )
            invitation_id = metadata.get("invitation_id")
            if invitation_id:
                markup = get_invitation_keyboard(invitation_id, "team")

        elif notification.type == NotificationType.COMMITTEE_INVITATION:
            message_text = COMMITTEE_INVITATION_MESSAGE.format(
                committee_name=metadata.get("committee_name", ""),
                inviter_name=metadata.get("inviter_name", "")
            )
            invitation_id = metadata.get("invitation_id")
            if invitation_id:
                markup = get_invitation_keyboard(invitation_id, "committee")

        else:
            # Если тип уведомления неизвестен, отправляем текст из уведомления
            message_text = notification.content

        # Отправляем сообщение пользователю
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message_text,
            reply_markup=markup,
            parse_mode="HTML"
        )

        # Помечаем уведомление как отправленное
        NotificationRepository.mark_as_sent(notification.id)

        return True

    except BotBlocked:
        logger.warning(f"Бот заблокирован пользователем {user.id}")
        return False
    except ChatNotFound:
        logger.warning(f"Чат с пользователем {user.id} не найден")
        return False
    except UserDeactivated:
        logger.warning(f"Пользователь {user.id} деактивировал свой аккаунт")
        return False
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API при отправке уведомления пользователю {user.id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Необработанная ошибка при отправке уведомления пользователю {user.id}: {e}")
        return False


# Восстановленная функция для обработки ожидающих уведомлений
async def process_pending_notifications(bot):
    """
    Обработка ожидающих отправки уведомлений

    Args:
        bot: Объект бота Telegram
    """
    try:
        # Получаем неотправленные уведомления
        # Ограничиваем количество уведомлений для обработки за один раз
        notifications = NotificationRepository.get_pending_notifications(limit=MAX_RPS)

        if not notifications:
            return

        logger.info(f"Найдено {len(notifications)} неотправленных уведомлений")

        # Отправляем уведомления
        for notification in notifications:
            user = notification.user
            if not user or not user.telegram_id:
                logger.warning(f"Уведомление {notification.id}: пользователь не найден или не имеет Telegram ID")
                NotificationRepository.mark_as_sent(notification.id)
                continue

            # Отправляем уведомление
            await send_notification(bot, notification, user)

    except Exception as e:
        logger.error(f"Ошибка при обработке неотправленных уведомлений: {e}")


def register_notification_handlers(dp: Dispatcher):
    """
    Регистрация обработчиков для колбэков от уведомлений

    Args:
        dp: Диспетчер Aiogram
    """
    global api_client
    from api.client import ApiClient
    api_client = ApiClient()

    # Добавим отдельные обработчики для каждого типа колбэка
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('accept_team_'))
    async def accept_team_invitation(callback_query: types.CallbackQuery):
        """
        Обработчик для принятия приглашения в команду

        Args:
            callback_query: Запрос от кнопки
        """
        logger.info(f"Получен callback для принятия приглашения в команду: {callback_query.data}")

        try:
            # Извлекаем ID приглашения
            invitation_id = int(callback_query.data.split('_')[2])

            # Сообщаем пользователю о начале обработки
            await callback_query.answer("Принимаем приглашение...")

            # Получаем пользователя
            user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
            if not user:
                await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
                return

            # Вызываем API
            logger.info(f"Вызываем API для принятия приглашения в команду {invitation_id}")
            result = await api_client.accept_team_invitation(invitation_id)
            logger.info(f"Результат API: {result}")

            # Обрабатываем результат
            if result and "error" not in result:
                team_name = result.get('team_name', '')
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n✅ Вы приняли приглашение! Вы теперь участник команды {team_name}.",
                    reply_markup=None,
                    parse_mode="HTML"
                )
            else:
                error_msg = result.get("error", "неизвестная ошибка") if result else "неизвестная ошибка"
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось принять приглашение: {error_msg}",
                    reply_markup=None,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка при принятии приглашения в команду: {e}")
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
                reply_markup=None,
                parse_mode="HTML"
            )

    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('decline_team_'))
    async def decline_team_invitation(callback_query: types.CallbackQuery):
        """
        Обработчик для отклонения приглашения в команду

        Args:
            callback_query: Запрос от кнопки
        """
        logger.info(f"Получен callback для отклонения приглашения в команду: {callback_query.data}")

        try:
            # Извлекаем ID приглашения
            invitation_id = int(callback_query.data.split('_')[2])

            # Сообщаем пользователю о начале обработки
            await callback_query.answer("Отклоняем приглашение...")

            # Получаем пользователя
            user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
            if not user:
                await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
                return

            # Вызываем API
            logger.info(f"Вызываем API для отклонения приглашения в команду {invitation_id}")
            result = await api_client.decline_team_invitation(invitation_id)
            logger.info(f"Результат API: {result}")

            # Обрабатываем результат
            if result and "error" not in result:
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Вы отклонили приглашение.",
                    reply_markup=None,
                    parse_mode="HTML"
                )
            else:
                error_msg = result.get("error", "неизвестная ошибка") if result else "неизвестная ошибка"
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось отклонить приглашение: {error_msg}",
                    reply_markup=None,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка при отклонении приглашения в команду: {e}")
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
                reply_markup=None,
                parse_mode="HTML"
            )

    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('accept_committee_'))
    async def accept_committee_invitation(callback_query: types.CallbackQuery):
        """
        Обработчик для принятия приглашения в оргкомитет

        Args:
            callback_query: Запрос от кнопки
        """
        logger.info(f"Получен callback для принятия приглашения в оргкомитет: {callback_query.data}")

        try:
            # Извлекаем ID приглашения
            invitation_id = int(callback_query.data.split('_')[2])

            # Сообщаем пользователю о начале обработки
            await callback_query.answer("Принимаем приглашение...")

            # Получаем пользователя
            user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
            if not user:
                await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
                return

            # Вызываем API
            logger.info(f"Вызываем API для принятия приглашения в оргкомитет {invitation_id}")
            result = await api_client.accept_committee_invitation(invitation_id)
            logger.info(f"Результат API: {result}")

            # Обрабатываем результат
            if result and "error" not in result:
                committee_name = result.get('committee_name', '')
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n✅ Вы приняли приглашение! Вы теперь член оргкомитета {committee_name}.",
                    reply_markup=None,
                    parse_mode="HTML"
                )
            else:
                error_msg = result.get("error", "неизвестная ошибка") if result else "неизвестная ошибка"
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось принять приглашение: {error_msg}",
                    reply_markup=None,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка при принятии приглашения в оргкомитет: {e}")
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
                reply_markup=None,
                parse_mode="HTML"
            )

    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('decline_committee_'))
    async def decline_committee_invitation(callback_query: types.CallbackQuery):
        """
        Обработчик для отклонения приглашения в оргкомитет

        Args:
            callback_query: Запрос от кнопки
        """
        logger.info(f"Получен callback для отклонения приглашения в оргкомитет: {callback_query.data}")

        try:
            # Извлекаем ID приглашения
            invitation_id = int(callback_query.data.split('_')[2])

            # Сообщаем пользователю о начале обработки
            await callback_query.answer("Отклоняем приглашение...")

            # Получаем пользователя
            user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
            if not user:
                await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
                return

            # Вызываем API
            logger.info(f"Вызываем API для отклонения приглашения в оргкомитет {invitation_id}")
            result = await api_client.decline_committee_invitation(invitation_id)
            logger.info(f"Результат API: {result}")

            # Обрабатываем результат
            if result and "error" not in result:
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Вы отклонили приглашение.",
                    reply_markup=None,
                    parse_mode="HTML"
                )
            else:
                error_msg = result.get("error", "неизвестная ошибка") if result else "неизвестная ошибка"
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось отклонить приглашение: {error_msg}",
                    reply_markup=None,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка при отклонении приглашения в оргкомитет: {e}")
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
                reply_markup=None,
                parse_mode="HTML"
            )

    # Обработчик для отклонения приглашения в команду
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('decline_team_'))
    async def decline_team_invitation(callback_query: types.CallbackQuery):
        """
        Обработчик для отклонения приглашения в команду

        Args:
            callback_query: Запрос от кнопки
        """
        await callback_query.answer("Обрабатываем ваше решение...")

        try:
            invitation_id = int(callback_query.data.split('_')[2])
            logger.info(f"Отклоняем приглашение в команду: {invitation_id}")

            # Получаем пользователя
            user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
            if not user:
                await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
                return

            # Вызываем API для отклонения приглашения
            result = await api_client.decline_team_invitation(invitation_id)

            # Обрабатываем результат
            if "error" not in result:
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Вы отклонили приглашение.",
                    reply_markup=None
                )
            else:
                error_msg = result.get("error", "неизвестная ошибка")
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось отклонить приглашение: {error_msg}",
                    reply_markup=None
                )
        except Exception as e:
            logger.error(f"Ошибка при отклонении приглашения в команду: {e}")
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
                reply_markup=None
            )

    # Обработчик для принятия приглашения в оргкомитет
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('accept_committee_'))
    async def accept_committee_invitation(callback_query: types.CallbackQuery):
        """
        Обработчик для принятия приглашения в оргкомитет

        Args:
            callback_query: Запрос от кнопки
        """
        await callback_query.answer("Обрабатываем ваше решение...")

        try:
            invitation_id = int(callback_query.data.split('_')[2])
            logger.info(f"Принимаем приглашение в оргкомитет: {invitation_id}")

            # Получаем пользователя
            user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
            if not user:
                await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
                return

            # Вызываем API для принятия приглашения
            result = await api_client.accept_committee_invitation(invitation_id)

            # Обрабатываем результат
            if "error" not in result:
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n✅ Вы приняли приглашение! Вы теперь член оргкомитета {result.get('committee_name', '')}.",
                    reply_markup=None
                )
            else:
                error_msg = result.get("error", "неизвестная ошибка")
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось принять приглашение: {error_msg}",
                    reply_markup=None
                )
        except Exception as e:
            logger.error(f"Ошибка при принятии приглашения в оргкомитет: {e}")
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
                reply_markup=None
            )

    # Обработчик для отклонения приглашения в оргкомитет
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith('decline_committee_'))
    async def decline_committee_invitation(callback_query: types.CallbackQuery):
        """
        Обработчик для отклонения приглашения в оргкомитет

        Args:
            callback_query: Запрос от кнопки
        """
        await callback_query.answer("Обрабатываем ваше решение...")

        try:
            invitation_id = int(callback_query.data.split('_')[2])
            logger.info(f"Отклоняем приглашение в оргкомитет: {invitation_id}")

            # Получаем пользователя
            user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
            if not user:
                await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
                return

            # Вызываем API для отклонения приглашения
            result = await api_client.decline_committee_invitation(invitation_id)

            # Обрабатываем результат
            if "error" not in result:
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Вы отклонили приглашение.",
                    reply_markup=None
                )
            else:
                error_msg = result.get("error", "неизвестная ошибка")
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось отклонить приглашение: {error_msg}",
                    reply_markup=None
                )
        except Exception as e:
            logger.error(f"Ошибка при отклонении приглашения в оргкомитет: {e}")
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
                reply_markup=None
            )

    # Обработчик колбэков для кнопок
    @dp.callback_query_handler(lambda c: c.data and c.data.startswith(('accept_', 'decline_')))
    async def process_invitation_callback(callback_query: types.CallbackQuery):
        """
        Общий обработчик для колбэков от кнопок приглашений

        Args:
            callback_query: Запрос от кнопки
        """
        logger.info(f"Получен callback_query: {callback_query.data}")

        # Анализируем callback_data
        parts = callback_query.data.split('_')
        if len(parts) < 3:
            logger.error(f"Некорректный формат callback_data: {callback_query.data}")
            await callback_query.answer("Ошибка обработки запроса")
            return

        action = parts[0]  # accept или decline
        invitation_type = parts[1]  # team или committee
        invitation_id = int(parts[2])  # ID приглашения

        logger.info(f"Обрабатываем {action} для {invitation_type} с ID {invitation_id}")

        # Получаем пользователя
        user = UserRepository.get_by_telegram_id(str(callback_query.from_user.id))
        if not user:
            await callback_query.answer("Ваш аккаунт не привязан к боту")
            await callback_query.message.answer("Ваш аккаунт не привязан к боту. Отправьте /start для привязки.")
            return

        # Сообщаем пользователю о начале обработки
        await callback_query.answer("Обрабатываем ваше решение...")

        try:
            result = None

            # Вызываем соответствующий метод API в зависимости от действия и типа приглашения
            if action == "accept" and invitation_type == "team":
                result = await api_client.accept_team_invitation(invitation_id)
                success_message = f"✅ Вы приняли приглашение в команду!"
            elif action == "decline" and invitation_type == "team":
                result = await api_client.decline_team_invitation(invitation_id)
                success_message = "❌ Вы отклонили приглашение в команду."
            elif action == "accept" and invitation_type == "committee":
                result = await api_client.accept_committee_invitation(invitation_id)
                success_message = f"✅ Вы приняли приглашение в оргкомитет!"
            elif action == "decline" and invitation_type == "committee":
                result = await api_client.decline_committee_invitation(invitation_id)
                success_message = "❌ Вы отклонили приглашение в оргкомитет."
            else:
                logger.error(f"Неподдерживаемая комбинация действия и типа: {action}_{invitation_type}")
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Неизвестная операция.",
                    reply_markup=None
                )
                return

            # Проверяем результат вызова API
            if result and "error" not in result:
                # Успешный результат
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n{success_message}",
                    reply_markup=None,
                    parse_mode="HTML"
                )
            else:
                # Ошибка от API
                error_msg = result.get("error", "неизвестная ошибка") if result else "неизвестная ошибка"
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n❌ Не удалось выполнить операцию: {error_msg}",
                    reply_markup=None,
                    parse_mode="HTML"
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке callback_query {callback_query.data}: {e}")
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.",
                reply_markup=None,
                parse_mode="HTML"
            )