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

    # Обработчик запроса "Мои матчи"
    @dp.message_handler(lambda message: message.text == "Мои матчи")
    async def my_matches(message: types.Message):
        """
        Обработчик запроса информации о предстоящих матчах

        Args:
            message: Сообщение от пользователя
        """
        user_data = UserRepository.get_by_telegram_id(str(message.from_user.id))
        if not user_data:
            await message.answer(
                "Ваш аккаунт не привязан к боту. Отправьте /start для привязки."
            )
            return

        # Отправка сообщения о загрузке
        loading_message = await message.answer("Загрузка ваших предстоящих матчей...")

        try:
            # Получаем предстоящие матчи через API
            matches = await api_client.get_user_matches(user_data['id'], status="upcoming")

            # Проверяем, есть ли ошибка в ответе
            if matches and isinstance(matches, dict) and "error" in matches:
                await loading_message.delete()
                await message.answer(
                    f"Произошла ошибка при получении матчей: {matches['error']}"
                )
                return

            # Если матчей нет или список пуст
            if not matches or len(matches) == 0:
                await loading_message.delete()
                await message.answer(
                    "У вас нет предстоящих матчей."
                )
                return

            # Формируем сообщение с информацией о матчах
            response = "🏆 <b>Ваши предстоящие матчи:</b>\n\n"

            for match in matches:
                response += f"<b>{match['tournament_name']}</b>\n"
                response += f"🆚 Соперник: <b>{match['opponent_name']}</b>\n"
                response += f"📅 Дата: <b>{match['date']}</b> в <b>{match['time']}</b>\n"
                response += f"📍 Место: <b>{match['location_name']}</b>\n"
                response += f"🏢 Адрес: <b>{match['address']}</b>\n"
                response += "\n"

            # Удаляем сообщение загрузки
            await loading_message.delete()

            # Отправляем сообщение с информацией о матчах
            await message.answer(
                response,
                parse_mode="HTML"
            )

            # Если матчей больше одного, добавляем кнопки для управления
            if len(matches) > 0:
                first_match = matches[0]
                await message.answer(
                    "Действия для матча:",
                    reply_markup=get_match_actions_keyboard(first_match['id'], user_data['id'])
                )

        except Exception as e:
            logger.error(f"Ошибка при получении предстоящих матчей пользователя {user_data['id']}: {e}")

            # Удаляем сообщение загрузки
            await loading_message.delete()

            await message.answer(
                "Произошла ошибка при получении информации о матчах. Пожалуйста, попробуйте позже."
            )

    # Обработчик запроса "Мои чемпионаты"
    @dp.message_handler(lambda message: message.text == "Мои чемпионаты")
    async def my_championships(message: types.Message):
        """
        Обработчик запроса информации о чемпионатах пользователя

        Args:
            message: Сообщение от пользователя
        """
        user_data = UserRepository.get_by_telegram_id(str(message.from_user.id))
        if not user_data:
            await message.answer(
                "Ваш аккаунт не привязан к боту. Отправьте /start для привязки."
            )
            return

        # Здесь должна быть логика получения информации о чемпионатах через API
        await message.answer(
            "Функция просмотра чемпионатов находится в разработке. "
            "Скоро она будет доступна!"
        )

    # Обработчик запроса "Мои команды"
    @dp.message_handler(lambda message: message.text == "Мои команды")
    async def my_teams(message: types.Message):
        """
        Обработчик запроса информации о командах пользователя

        Args:
            message: Сообщение от пользователя
        """
        user_data = UserRepository.get_by_telegram_id(str(message.from_user.id))
        if not user_data:
            await message.answer(
                "Ваш аккаунт не привязан к боту. Отправьте /start для привязки."
            )
            return

        # Здесь должна быть логика получения информации о командах через API
        await message.answer(
            "Функция просмотра команд находится в разработке. "
            "Скоро она будет доступна!"
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

    # Функция для обработки номера телефона
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
            user_data = UserRepository.get_by_phone(phone_number)

            if user_data:
                # Обновляем Telegram ID пользователя
                success = UserRepository.update_telegram_id(phone_number, str(message.from_user.id))
                if success:
                    # Отправляем сообщение об успешной привязке
                    await message.answer(
                        PHONE_LINKED_MESSAGE.format(
                            first_name=user_data['first_name'],
                            last_name=user_data['last_name']
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
                    created_user = UserRepository.create(
                        phone_number=phone_number,
                        first_name=user_data.get("first_name", "Пользователь"),
                        last_name=user_data.get("last_name", ""),
                        telegram_id=str(message.from_user.id)
                    )

                    if created_user:
                        # Отправляем сообщение об успешной привязке
                        await message.answer(
                            PHONE_LINKED_MESSAGE.format(
                                first_name=created_user['first_name'],
                                last_name=created_user['last_name']
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