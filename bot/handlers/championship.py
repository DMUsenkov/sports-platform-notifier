# Добавим в bot/handlers/championship.py (новый файл)

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from utils.logger import get_logger
from database.repositories.user_repository import UserRepository
from api.client import ApiClient
from bot.keyboards.keyboards import get_championship_menu_keyboard

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
            # Получаем рекомендуемые чемпионаты через API
            championships = await api_client.get_recommended_championships(user.id)

            if not championships:
                await message.answer(
                    "На данный момент у нас нет рекомендаций для вас. Пожалуйста, проверьте позже.",
                    reply_markup=get_championship_menu_keyboard()
                )
                return

            # Отправляем информацию о каждом рекомендуемом чемпионате
            await message.answer(
                "🏆 Вот чемпионаты, которые могут вас заинтересовать:",
                reply_markup=get_championship_menu_keyboard()
            )

            for championship in championships:
                # Формируем сообщение с информацией о чемпионате
                description = championship.get('description', '')
                if len(description) > 200:
                    description = description[:197] + "..."

                response = f"🏆 *{championship['name']}*\n\n"
                response += f"⚽ Вид спорта: {championship['sport']}\n"
                response += f"🌆 Город: {championship['city']}\n"
                response += f"👥 Размер команды: {championship['team_members_count']} участников\n"
                response += f"📅 Дедлайн подачи заявок: {championship['application_deadline']}\n\n"

                if description:
                    response += f"📝 *Описание:*\n{description}\n\n"

                response += f"Для получения подробной информации отправьте /championship_{championship['tournament_id']}"

                # Отправляем сообщение с форматированием Markdown
                await message.answer(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Ошибка при получении рекомендуемых чемпионатов для пользователя {user.id}: {e}")
            await message.answer(
                "Произошла ошибка при получении рекомендаций. Пожалуйста, попробуйте позже.",
                reply_markup=get_championship_menu_keyboard()
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
            # Извлекаем ID чемпионата из команды
            championship_id = int(message.text.split('_')[1])

            # Получаем детальную информацию о чемпионате через API
            championship = await api_client.get_championship_details(championship_id)

            if not championship:
                await message.answer("Чемпионат не найден.")
                return

            # Формируем сообщение с информацией о чемпионате
            response = f"🏆 *{championship['name']}*\n\n"
            response += f"⚽ Вид спорта: {championship['sport']}\n"
            response += f"🌆 Город: {championship['city']}\n"
            response += f"👥 Размер команды: {championship['team_members_count']} участников\n"
            response += f"📅 Дедлайн подачи заявок: {championship['application_deadline']}\n\n"

            # Информация о стадиях чемпионата
            if 'stages' in championship and championship['stages']:
                response += f"📊 *Этапы чемпионата:*\n"
                for stage in championship['stages']:
                    status = "✅ Опубликован" if stage.get('is_published') else "⏳ Не опубликован"
                    response += f"- {stage['name']}: {status}\n"

            # Полное описание
            if championship.get('description'):
                response += f"\n📝 *Описание:*\n{championship['description']}\n"

            # Организатор
            response += f"\n👔 Организатор: {championship.get('org_name', 'Не указан')}\n"

            # Статус чемпионата
            if championship.get('is_stopped'):
                response += "⚠️ Чемпионат остановлен\n"

            # Отправляем сообщение с форматированием Markdown
            await message.answer(response, parse_mode="Markdown")

        except ValueError:
            await message.answer("Неверный формат команды. Используйте /championship_<id>, например /championship_123")
        except Exception as e:
            logger.error(f"Ошибка при получении информации о чемпионате: {e}")
            await message.answer(
                "Произошла ошибка при получении информации о чемпионате. Пожалуйста, попробуйте позже."
            )