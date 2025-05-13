import logging
import re
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from utils.logger import get_logger
from database.repositories.user_repository import UserRepository
from api.client import ApiClient
from bot.messages.templates import (
    WELCOME_MESSAGE,
    PHONE_LINKED_MESSAGE,
    PHONE_NOT_FOUND_MESSAGE,
    PHONE_LINK_ERROR_MESSAGE,
    INVALID_PHONE_FORMAT_MESSAGE
)
from bot.keyboards.keyboards import (
    get_phone_keyboard,
    get_start_keyboard,
    get_help_keyboard,
    get_match_actions_keyboard
)

logger = get_logger("user_handler")


# Определяем состояния для конечного автомата
class UserStates(StatesGroup):
    waiting_for_phone = State()  # Ожидание номера телефона


# Регулярное выражение для проверки номера телефона
PHONE_REGEX = r'^(\+7|7|8)[0-9]{10}$'

# Инициализация API клиента
api_client = None


def register_user_handlers(dp: Dispatcher):
    """
    Регистрация обработчиков команд пользователя

    Args:
        dp: Диспетчер Aiogram
    """
    global api_client
    api_client = ApiClient()

    # Обработчик команды /start
    @dp.message_handler(commands=['start'])
    async def cmd_start(message: types.Message):
        """
        Обработчик команды /start

        Args:
            message: Сообщение от пользователя
        """
        user_id = message.from_user.id

        # Проверяем, есть ли пользователь с таким Telegram ID
        user_data = UserRepository.get_by_telegram_id(str(user_id))

        if user_data:
            # Если пользователь уже зарегистрирован, отправляем приветствие
            await message.answer(
                f"Привет, {user_data['first_name']}! Ваш аккаунт уже привязан к боту.",
                reply_markup=get_start_keyboard()
            )
        else:
            # Если пользователь не зарегистрирован, запрашиваем номер телефона
            await message.answer(
                WELCOME_MESSAGE,
                reply_markup=get_phone_keyboard()
            )
            # Устанавливаем состояние ожидания номера телефона
            await UserStates.waiting_for_phone.set()

    # Обработчик отправки контакта (номера телефона)
    @dp.message_handler(content_types=types.ContentType.CONTACT, state=UserStates.waiting_for_phone)
    async def process_contact(message: types.Message, state: FSMContext):
        """
        Обработчик отправки контакта пользователем

        Args:
            message: Сообщение с контактом от пользователя
            state: Состояние конечного автомата
        """
        # Получаем номер телефона из контакта
        phone_number = message.contact.phone_number

        # Форматируем номер телефона
        if phone_number.startswith('+'):
            phone_number = phone_number[1:]  # Убираем плюс

        # Проверяем, зарегистрирован ли пользователь с таким номером телефона
        await process_phone_number(message, phone_number, state)

    # Обработчик отправки текстового сообщения с номером телефона
    @dp.message_handler(state=UserStates.waiting_for_phone)
    async def process_phone_text(message: types.Message, state: FSMContext):
        """
        Обработчик отправки текстового сообщения с номером телефона

        Args:
            message: Сообщение от пользователя
            state: Состояние конечного автомата
        """
        # Получаем номер телефона из текстового сообщения
        phone_number = message.text.strip()

        # Проверяем формат номера телефона
        if not re.match(PHONE_REGEX, phone_number):
            await message.answer(INVALID_PHONE_FORMAT_MESSAGE)
            return

        # Форматируем номер телефона
        if phone_number.startswith('+'):
            phone_number = phone_number[1:]  # Убираем плюс
        elif phone_number.startswith('8'):
            phone_number = '7' + phone_number[1:]  # Заменяем 8 на 7

        # Проверяем, зарегистрирован ли пользователь с таким номером телефона
        await process_phone_number(message, phone_number, state)

    # Обработчик команды /help
    @dp.message_handler(commands=['help'])
    @dp.message_handler(lambda message: message.text == "Помощь")
    async def cmd_help(message: types.Message):
        """
        Обработчик команды /help

        Args:
            message: Сообщение от пользователя
        """
        await message.answer(
            "Выберите раздел помощи:",
            reply_markup=get_help_keyboard()
        )

    @dp.message_handler(lambda message: message.text == "Мои матчи")
    async def my_matches(message: types.Message):
        """
        Обработчик запроса информации о предстоящих матчах

        Args:
            message: Сообщение от пользователя
        """
        user = UserRepository.get_by_telegram_id(str(message.from_user.id))
        if not user:
            await message.answer(
                "Ваш аккаунт не привязан к боту. Отправьте /start для привязки."
            )
            return

        try:
            # Получаем ID пользователя
            user_id = user.id if hasattr(user, 'id') else user.get('id')

            if not user_id:
                await message.answer(
                    "Не удалось определить ID пользователя. Пожалуйста, попробуйте заново привязать аккаунт, отправив /start."
                )
                return

            # Получаем список матчей пользователя через API
            matches = await api_client.get_user_matches(user_id, status="upcoming")

            if not matches:
                await message.answer("У вас нет предстоящих матчей.")
                return

            # Формируем сообщение с информацией о матчах
            response = "📅 Ваши предстоящие матчи:\n\n"

            for match in matches:
                response += f"🏆 *{match['tournament_name']}*\n"
                response += f"🆚 Соперник: {match['opponent_name']}\n"
                response += f"📍 Место: {match['location_name']}\n"
                response += f"📆 Дата: {match['date']} в {match['time']}\n\n"

            # Отправляем сообщение с форматированием Markdown
            await message.answer(response, parse_mode="Markdown")

        except Exception as e:
            # Безопасное логирование
            user_id_str = str(user.id if hasattr(user, 'id') else user.get('id', 'unknown'))
            logger.error(f"Ошибка при получении матчей пользователя {user_id_str}: {e}")

            await message.answer(
                "Произошла ошибка при получении информации о матчах. Пожалуйста, попробуйте позже."
            )

    @dp.message_handler(commands=['invitations'])
    @dp.message_handler(lambda message: message.text == "Приглашения")
    async def my_invitations(message: types.Message):
        """
        Обработчик запроса информации о приглашениях пользователя

        Args:
            message: Сообщение от пользователя
        """
        user = UserRepository.get_by_telegram_id(str(message.from_user.id))
        if not user:
            await message.answer(
                "Ваш аккаунт не привязан к боту. Отправьте /start для привязки."
            )
            return

        try:
            # Получаем ID пользователя
            user_id = user.id if hasattr(user, 'id') else user.get('id')

            if not user_id:
                await message.answer(
                    "Не удалось определить ID пользователя. Пожалуйста, попробуйте заново привязать аккаунт, отправив /start."
                )
                return

            # Получаем список приглашений пользователя через API
            invitations = await api_client.get_user_invitations(user_id)

            if not invitations:
                await message.answer("У вас нет активных приглашений.")
                return

            has_sent_invitations = False

            # Отправляем отдельные сообщения для каждого приглашения с кнопками
            for invitation in invitations:
                if invitation['type'] == 'team':
                    # Создаем клавиатуру для этого приглашения
                    markup = get_invitation_keyboard(invitation['invitation_id'], "team")

                    # Отправляем отдельное сообщение для каждого приглашения в команду
                    await message.answer(
                        TEAM_INVITATION_MESSAGE.format(
                            team_name=invitation.get('team_name', ''),
                            sport_type=invitation.get('sport', ''),
                            captain_name=invitation.get('inviter_name', '')
                        ),
                        reply_markup=markup
                    )
                    has_sent_invitations = True

                elif invitation['type'] == 'committee':
                    # Создаем клавиатуру для этого приглашения
                    markup = get_invitation_keyboard(invitation['invitation_id'], "committee")

                    # Отправляем отдельное сообщение для каждого приглашения в оргкомитет
                    await message.answer(
                        COMMITTEE_INVITATION_MESSAGE.format(
                            committee_name=invitation.get('committee_name', ''),
                            inviter_name=invitation.get('inviter_name', '')
                        ),
                        reply_markup=markup
                    )
                    has_sent_invitations = True

            if not has_sent_invitations:
                await message.answer("У вас нет активных приглашений.")

        except Exception as e:
            # Безопасное логирование
            user_id_str = str(user.id if hasattr(user, 'id') else user.get('id', 'unknown'))
            logger.error(f"Ошибка при получении приглашений пользователя {user_id_str}: {e}")

            await message.answer(
                "Произошла ошибка при получении информации о приглашениях. Пожалуйста, попробуйте позже."
            )

    @dp.message_handler(lambda message: message.text == "Мои чемпионаты")
    async def my_championships(message: types.Message):
        """
        Обработчик запроса информации о чемпионатах пользователя

        Args:
            message: Сообщение от пользователя
        """
        user = UserRepository.get_by_telegram_id(str(message.from_user.id))
        if not user:
            await message.answer(
                "Ваш аккаунт не привязан к боту. Отправьте /start для привязки."
            )
            return

        try:
            # Получаем ID пользователя
            user_id = user.id if hasattr(user, 'id') else user.get('id')

            if not user_id:
                await message.answer(
                    "Не удалось определить ID пользователя. Пожалуйста, попробуйте заново привязать аккаунт, отправив /start."
                )
                return

            # Получаем список чемпионатов пользователя через API
            championships = await api_client.get_user_championships(user_id)

            if not championships:
                await message.answer("Вы не участвуете ни в одном чемпионате.")
                return

            # Формируем сообщение с информацией о чемпионатах
            response = "🏆 Ваши чемпионаты:\n\n"

            for championship in championships:
                response += f"*{championship['name']}*\n"
                response += f"⚽ Вид спорта: {championship['sport']}\n"
                response += f"🌆 Город: {championship['city']}\n"

                if championship['status'] == "active":
                    status = "Активный"
                elif championship['status'] == "past":
                    status = "Завершен"
                else:
                    status = "Неизвестно"

                response += f"📊 Статус: {status}\n"

                if 'position' in championship and championship['position']:
                    response += f"🏅 Позиция: {championship['position']}\n"

                response += "\n"

            # Отправляем сообщение с форматированием Markdown
            await message.answer(response, parse_mode="Markdown")

        except Exception as e:
            # Безопасное логирование
            user_id_str = str(user.id if hasattr(user, 'id') else user.get('id', 'unknown'))
            logger.error(f"Ошибка при получении чемпионатов пользователя {user_id_str}: {e}")

            await message.answer(
                "Произошла ошибка при получении информации о чемпионатах. Пожалуйста, попробуйте позже."
            )

    @dp.message_handler(lambda message: message.text == "Мои команды")
    async def my_teams(message: types.Message):
        """
        Обработчик запроса информации о командах пользователя

        Args:
            message: Сообщение от пользователя
        """
        user = UserRepository.get_by_telegram_id(str(message.from_user.id))
        if not user:
            await message.answer(
                "Ваш аккаунт не привязан к боту. Отправьте /start для привязки."
            )
            return

        try:
            # Получаем ID пользователя
            user_id = user.id if hasattr(user, 'id') else user.get('id')

            if not user_id:
                await message.answer(
                    "Не удалось определить ID пользователя. Пожалуйста, попробуйте заново привязать аккаунт, отправив /start."
                )
                return

            # Получаем список команд пользователя через API
            teams = await api_client.get_user_teams(user_id)

            if not teams:
                await message.answer("Вы не состоите ни в одной команде.")
                return

            # Формируем сообщение с информацией о командах
            response = "👥 Ваши команды:\n\n"

            for team in teams:
                response += f"*{team['name']}*\n"
                response += f"⚽ Вид спорта: {team['sport']}\n"

                if team.get('is_captain', False):
                    response += "👑 Вы капитан этой команды\n"

                response += "\n"

            # Добавляем инструкцию по просмотру деталей команды
            response += "Чтобы просмотреть подробную информацию о команде, отправьте /team_<id>, например /team_123"

            # Отправляем сообщение с форматированием Markdown
            await message.answer(response, parse_mode="Markdown")

        except Exception as e:
            # Безопасное логирование
            user_id_str = str(user.id if hasattr(user, 'id') else user.get('id', 'unknown'))
            logger.error(f"Ошибка при получении команд пользователя {user_id_str}: {e}")

            await message.answer(
                "Произошла ошибка при получении информации о командах. Пожалуйста, попробуйте позже."
            )

    # Обработчики колбэков для меню помощи
    @dp.callback_query_handler(lambda c: c.data == 'help_about')
    async def help_about(callback_query: types.CallbackQuery):
        """
        Обработчик запроса информации о боте

        Args:
            callback_query: Запрос от кнопки
        """
        await callback_query.answer()
        await callback_query.message.answer(
            "О боте:\n\n"
            "Этот бот предназначен для отправки уведомлений пользователям онлайн-платформы "
            "для поиска и управления любительскими спортивными соревнованиями.\n\n"
            "Через этот бот вы будете получать актуальную информацию о чемпионатах, "
            "матчах и командах, в которых вы участвуете."
        )

    @dp.callback_query_handler(lambda c: c.data == 'help_notification_types')
    async def help_notification_types(callback_query: types.CallbackQuery):
        """
        Обработчик запроса информации о типах уведомлений

        Args:
            callback_query: Запрос от кнопки
        """
        await callback_query.answer()
        await callback_query.message.answer(
            "Типы уведомлений:\n\n"
            "• Заявки на участие в чемпионатах\n"
            "• Отмена или отклонение заявок\n"
            "• Отмена или завершение чемпионатов\n"
            "• Назначение новых матчей\n"
            "• Перенос матчей\n"
            "• Результаты прохождения в плей-офф\n"
            "• Напоминания о матчах\n"
            "• Новые интересные чемпионаты\n"
            "• Сообщения от оргкомитетов\n"
            "• Приглашения в команды\n"
            "• Приглашения в оргкомитеты"
        )

    @dp.callback_query_handler(lambda c: c.data == 'help_change_phone')
    async def help_change_phone(callback_query: types.CallbackQuery):
        """
        Обработчик запроса информации о смене номера телефона

        Args:
            callback_query: Запрос от кнопки
        """
        await callback_query.answer()
        await callback_query.message.answer(
            "Как привязать другой номер телефона:\n\n"
            "1. Отправьте команду /changephone\n"
            "2. Введите новый номер телефона или отправьте контакт\n"
            "3. Ваш аккаунт будет привязан к новому номеру телефона\n\n"
            "Обратите внимание, что номер телефона должен быть зарегистрирован в системе."
        )

    @dp.callback_query_handler(lambda c: c.data == 'help_support')
    async def help_support(callback_query: types.CallbackQuery):
        """
        Обработчик запроса информации о поддержке

        Args:
            callback_query: Запрос от кнопки
        """
        await callback_query.answer()
        await callback_query.message.answer(
            "Связаться с поддержкой:\n\n"
            "По всем вопросам, связанным с работой бота или платформы, "
            "пожалуйста, обращайтесь по адресу электронной почты:\n"
            "support@sports-platform.ru\n\n"
            "Или позвоните нам по телефону:\n"
            "+7 (800) 123-45-67"
        )

    # Обработчик команды изменения номера телефона
    @dp.message_handler(commands=['changephone'])
    async def cmd_change_phone(message: types.Message):
        """
        Обработчик команды /changephone

        Args:
            message: Сообщение от пользователя
        """
        await message.answer(
            "Пожалуйста, отправьте новый номер телефона или поделитесь контактом.",
            reply_markup=get_phone_keyboard()
        )
        # Устанавливаем состояние ожидания номера телефона
        await UserStates.waiting_for_phone.set()

    async def process_phone_number(message: types.Message, phone_number: str, state: FSMContext):
        """
        Обработка номера телефона

        Args:
            message: Сообщение от пользователя
            phone_number: Номер телефона
            state: Состояние конечного автомата
        """
        try:
            # Сначала проверяем в локальной базе данных
            user = UserRepository.get_by_phone(phone_number)

            if user:
                # Получаем имя и фамилию пользователя безопасно
                first_name = user.first_name if hasattr(user, 'first_name') else user.get('first_name', 'Пользователь')
                last_name = user.last_name if hasattr(user, 'last_name') else user.get('last_name', '')

                # Обновляем Telegram ID пользователя
                success = UserRepository.update_telegram_id(phone_number, str(message.from_user.id))
                if success:
                    # Отправляем сообщение об успешной привязке
                    await message.answer(
                        PHONE_LINKED_MESSAGE.format(
                            first_name=first_name,
                            last_name=last_name
                        ),
                        reply_markup=get_start_keyboard()
                    )
                    # Сбрасываем состояние
                    await state.finish()
                else:
                    # Произошла ошибка при обновлении Telegram ID
                    await message.answer(
                        PHONE_LINK_ERROR_MESSAGE,
                        reply_markup=get_phone_keyboard()
                    )
                return

            # Если пользователь не найден в локальной базе, проверяем через API
            if api_client:
                user_data = await api_client.get_user_data(phone_number)
                if "error" not in user_data and user_data:
                    # Создаем пользователя в локальной базе данных
                    user = UserRepository.create(
                        phone_number=phone_number,
                        first_name=user_data.get("first_name", "Пользователь"),
                        last_name=user_data.get("last_name", ""),
                        telegram_id=str(message.from_user.id)
                    )

                    # Проверяем результат создания пользователя
                    if user:
                        # Получаем имя и фамилию пользователя безопасно
                        first_name = user.first_name if hasattr(user, 'first_name') else user.get('first_name',
                                                                                                  'Пользователь')
                        last_name = user.last_name if hasattr(user, 'last_name') else user.get('last_name', '')

                        # Отправляем сообщение об успешной привязке
                        await message.answer(
                            PHONE_LINKED_MESSAGE.format(
                                first_name=first_name,
                                last_name=last_name
                            ),
                            reply_markup=get_start_keyboard()
                        )
                        # Сбрасываем состояние
                        await state.finish()
                    else:
                        # Произошла ошибка при создании пользователя
                        await message.answer(
                            PHONE_LINK_ERROR_MESSAGE,
                            reply_markup=get_phone_keyboard()
                        )
                    return

            # Пользователь не найден ни в локальной базе, ни через API
            await message.answer(
                PHONE_NOT_FOUND_MESSAGE.format(phone=phone_number),
                reply_markup=get_phone_keyboard()
            )

        except Exception as e:
            logger.error(f"Ошибка при обработке номера телефона {phone_number}: {e}")
            await message.answer(
                PHONE_LINK_ERROR_MESSAGE,
                reply_markup=get_phone_keyboard()
            )

    @dp.message_handler(lambda message: message.text.startswith('/team_'))
    async def team_details(message: types.Message):
        """
        Обработчик запроса информации о конкретной команде

        Args:
            message: Сообщение от пользователя
        """
        user = UserRepository.get_by_telegram_id(str(message.from_user.id))
        if not user:
            await message.answer(
                "Ваш аккаунт не привязан к боту. Отправьте /start для привязки."
            )
            return

        try:
            # Извлекаем ID команды из команды
            team_id = int(message.text.split('_')[1])

            # Получаем детальную информацию о команде через API
            team = await api_client.get_team_details(team_id)

            if not team:
                await message.answer("Команда не найдена или у вас нет доступа к ней.")
                return

            # Формируем сообщение с информацией о команде
            response = f"👥 *{team['name']}*\n\n"
            response += f"⚽ Вид спорта: {team['sport']}\n"
            response += f"👨‍👩‍👧‍👦 Участников: {team['count_member']}\n"
            response += f"🏆 Побед: {team.get('wins', 0)}\n"
            response += f"❌ Поражений: {team.get('loss', 0)}\n\n"

            # Список участников команды
            response += "👥 *Состав команды:*\n"
            for member in team.get('members', []):
                name = f"{member['first_name']} {member['last_name']}"
                if member.get('is_captain', False):
                    name += " 👑"
                response += f"- {name}\n"

            # Отправляем сообщение с форматированием Markdown
            await message.answer(response, parse_mode="Markdown")

        except ValueError:
            await message.answer("Неверный формат команды. Используйте /team_<id>, например /team_123")
        except Exception as e:
            # Безопасное логирование
            user_id_str = str(user.id if hasattr(user, 'id') else user.get('id', 'unknown'))
            logger.error(f"Ошибка при получении информации о команде для пользователя {user_id_str}: {e}")

            await message.answer(
                "Произошла ошибка при получении информации о команде. Пожалуйста, попробуйте позже."
            )