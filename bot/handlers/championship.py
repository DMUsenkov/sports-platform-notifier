from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from utils.logger import get_logger
from database.repositories.user_repository import UserRepository
from api.client import ApiClient
from bot.keyboards.keyboards import get_championship_menu_keyboard, get_start_keyboard

logger = get_logger("championship_handler")

# Инициализация API клиента
api_client = None


def register_championship_handlers(dp: Dispatcher):
    """
    Регистрация обработчиков для чемпионатов

    Args:
        dp: Диспетчер Aiogram
    """
    global api_client
    api_client = ApiClient()

    # Обработчик для просмотра рекомендуемых чемпионатов
    @dp.message_handler(lambda message: message.text == "Рекомендуемые чемпионаты")
    async def recommended_championships(message: types.Message):
        """
        Обработчик запроса информации о рекомендуемых чемпионатах

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
            # Отправляем информационное сообщение о начале поиска
            wait_message = await message.answer("Ищем чемпионаты, которые могут вас заинтересовать...")

            # Получаем ID пользователя в зависимости от типа объекта user
            user_id = user.id if hasattr(user, 'id') else user['id'] if isinstance(user,
                                                                                   dict) and 'id' in user else None

            if user_id is None:
                raise ValueError("Не удалось определить ID пользователя")

            # Получаем рекомендуемые чемпионаты через API
            championships = await api_client.get_recommended_championships(user_id)

            # Всесторонняя проверка на отсутствие рекомендаций
            if championships is None or not isinstance(championships, list) or len(championships) == 0:
                await message.answer(
                    "На данный момент у нас нет рекомендаций для вас. Пожалуйста, проверьте позже.",
                    reply_markup=get_start_keyboard()
                )
                return

            # Проверка, что в списке есть действительные записи
            valid_championships = [c for c in championships if isinstance(c, dict) and c.get('name')]
            if not valid_championships:
                await message.answer(
                    "На данный момент у нас нет рекомендаций для вас. Пожалуйста, проверьте позже.",
                    reply_markup=get_start_keyboard()
                )
                return

            # Отправляем информацию о каждом рекомендуемом чемпионате
            await message.answer(
                "🏆 Вот чемпионаты, которые могут вас заинтересовать:",
                reply_markup=get_start_keyboard()
            )

            # Функция для экранирования спец. символов Markdown
            def escape_markdown(text):
                if not text:
                    return ""
                # Экранируем специальные символы Markdown
                special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.',
                                 '!']
                for char in special_chars:
                    text = text.replace(char, '\\' + char)
                return text

            count_sent = 0
            for championship in valid_championships:
                try:
                    # Формируем сообщение с информацией о чемпионате
                    # Экранируем специальные символы в текстовых данных
                    name = escape_markdown(championship.get('name', 'Без названия'))
                    sport = escape_markdown(championship.get('sport', 'Не указан'))
                    city = escape_markdown(championship.get('city', 'Не указан'))
                    team_size = championship.get('team_members_count', '-')
                    deadline = escape_markdown(championship.get('application_deadline', 'Не указан'))

                    description = championship.get('description', '')
                    if len(description) > 200:
                        description = description[:197] + "..."
                    description = escape_markdown(description)

                    # Используем HTML вместо Markdown для более безопасного форматирования
                    response = f"🏆 <b>{name}</b>\n\n"
                    response += f"⚽ Вид спорта: {sport}\n"
                    response += f"🌆 Город: {city}\n"
                    response += f"👥 Размер команды: {team_size} участников\n"
                    response += f"📅 Дедлайн подачи заявок: {deadline}\n\n"

                    if description:
                        response += f"📝 <b>Описание:</b>\n{description}\n\n"

                    tournament_id = championship.get('tournament_id', championship.get('id'))
                    if tournament_id:
                        response += f"Для получения подробной информации отправьте /championship_{tournament_id}"

                    # Отправляем сообщение с форматированием HTML вместо Markdown
                    await message.answer(response, parse_mode="HTML")
                    count_sent += 1
                except Exception as e:
                    logger.error(f"Ошибка при обработке информации о чемпионате: {e}")

                    # Попробуем отправить без форматирования при ошибке
                    try:
                        name = championship.get('name', 'Без названия')
                        sport = championship.get('sport', 'Не указан')
                        city = championship.get('city', 'Не указан')
                        team_size = championship.get('team_members_count', '-')
                        deadline = championship.get('application_deadline', 'Не указан')

                        # Без форматирования
                        plain_response = f"🏆 {name}\n\n"
                        plain_response += f"⚽ Вид спорта: {sport}\n"
                        plain_response += f"🌆 Город: {city}\n"
                        plain_response += f"👥 Размер команды: {team_size} участников\n"
                        plain_response += f"📅 Дедлайн подачи заявок: {deadline}\n"

                        tournament_id = championship.get('tournament_id', championship.get('id'))
                        if tournament_id:
                            plain_response += f"\nДля получения подробной информации отправьте /championship_{tournament_id}"

                        await message.answer(plain_response)
                        count_sent += 1
                    except Exception as e2:
                        logger.error(f"Не удалось отправить даже простое сообщение: {e2}")

            # Если не удалось отправить ни одного чемпионата
            if count_sent == 0:
                await message.answer(
                    "К сожалению, не удалось загрузить информацию о рекомендуемых чемпионатах. Пожалуйста, попробуйте позже.",
                    reply_markup=get_start_keyboard()
                )

        except Exception as e:
            # Безопасное получение ID пользователя для логирования
            user_id_for_log = "неизвестно"
            try:
                if hasattr(user, 'id'):
                    user_id_for_log = user.id
                elif isinstance(user, dict) and 'id' in user:
                    user_id_for_log = user['id']
            except:
                pass

            logger.error(f"Ошибка при получении рекомендуемых чемпионатов для пользователя {user_id_for_log}: {e}")
            await message.answer(
                "Произошла ошибка при получении рекомендаций. Пожалуйста, попробуйте позже.",
                reply_markup=get_start_keyboard()
            )

    # Обработчик для просмотра детальной информации о чемпионате
    @dp.message_handler(lambda message: message.text.startswith('/championship_'))
    async def championship_details(message: types.Message):
        """
        Обработчик запроса информации о конкретном чемпионате

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
            # Сообщаем пользователю, что идет загрузка данных
            wait_message = await message.answer("Загружаем информацию о чемпионате...")

            # Извлекаем ID чемпионата из команды
            try:
                championship_id = int(message.text.split('_')[1])
            except (IndexError, ValueError) as e:
                await message.answer(
                    "Неверный формат команды. Используйте /championship_<id>, например /championship_123")
                return

            # Получаем ID пользователя в зависимости от типа объекта user
            user_id = user.id if hasattr(user, 'id') else user['id'] if isinstance(user,
                                                                                   dict) and 'id' in user else None

            if user_id is None:
                raise ValueError("Не удалось определить ID пользователя")

            # Получаем детальную информацию о чемпионате через API
            championship = await api_client.get_championship_details(championship_id)

            # Проверяем наличие данных
            if not championship or not isinstance(championship, dict):
                await message.answer("Чемпионат не найден или у вас нет доступа к нему.")
                return

            # Подготовка данных
            name = championship.get('name', 'Без названия')
            sport = championship.get('sport', 'Не указан')
            city = championship.get('city', 'Не указан')
            team_members_count = championship.get('team_members_count', '-')
            application_deadline = championship.get('application_deadline', 'Не указан')
            description = championship.get('description', '')
            org_name = championship.get('org_name', 'Не указан')
            is_stopped = championship.get('is_stopped', False)

            # Формируем ответ в формате HTML
            response = f"🏆 <b>{name}</b>\n\n"
            response += f"⚽ Вид спорта: {sport}\n"
            response += f"🌆 Город: {city}\n"
            response += f"👥 Размер команды: {team_members_count} участников\n"
            response += f"📅 Дедлайн подачи заявок: {application_deadline}\n\n"

            # Информация о стадиях чемпионата
            if 'stages' in championship and championship['stages']:
                response += f"📊 <b>Этапы чемпионата:</b>\n"
                for stage in championship['stages']:
                    status = "✅ Опубликован" if stage.get('is_published') else "⏳ Не опубликован"
                    response += f"- {stage.get('name', 'Этап')}: {status}\n"

            # Полное описание
            if description:
                if len(description) > 500:
                    description = description[:497] + "..."
                response += f"\n📝 <b>Описание:</b>\n{description}\n"

            # Организатор
            response += f"\n👔 Организатор: {org_name}\n"

            # Статус чемпионата
            if is_stopped:
                response += "⚠️ Чемпионат остановлен\n"

            # Отправляем сообщение с форматированием HTML
            await message.answer(response, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Ошибка при получении информации о чемпионате: {e}")

            # Пробуем отправить более информативное сообщение об ошибке
            error_message = "Произошла ошибка при получении информации о чемпионате."

            # Если ошибка в API
            if hasattr(e, 'response') and hasattr(e.response, 'status'):
                if e.response.status == 404:
                    error_message = "Чемпионат не найден."
                elif e.response.status == 403:
                    error_message = "У вас нет доступа к информации об этом чемпионате."
                elif e.response.status == 401:
                    error_message = "Требуется повторная авторизация. Отправьте команду /start."

            await message.answer(
                f"{error_message} Пожалуйста, попробуйте позже.",
                reply_markup=get_start_keyboard()
            )