import logging
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError

from database.connection import get_db_session
from database.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Репозиторий для работы с пользователями
    """

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """
        Получение пользователя по ID

        Args:
            user_id: ID пользователя

        Returns:
            Объект пользователя или None, если пользователь не найден
        """
        try:
            with get_db_session() as session:
                return session.query(User).filter(User.id == user_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении пользователя по ID {user_id}: {e}")
            return None

    @staticmethod
    def get_by_phone(phone_number: str) -> Optional[User]:
        """
        Получение пользователя по номеру телефона

        Args:
            phone_number: Номер телефона пользователя

        Returns:
            Объект пользователя или None, если пользователь не найден
        """
        try:
            with get_db_session() as session:
                return session.query(User).filter(User.phone_number == phone_number).first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении пользователя по номеру телефона {phone_number}: {e}")
            return None

    @staticmethod
    def get_by_telegram_id(telegram_id: str) -> Optional[User]:
        """
        Получение пользователя по Telegram ID

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Объект пользователя или None, если пользователь не найден
        """
        try:
            with get_db_session() as session:
                return session.query(User).filter(User.telegram_id == telegram_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении пользователя по Telegram ID {telegram_id}: {e}")
            return None

    @staticmethod
    def update_telegram_id(phone_number: str, telegram_id: str) -> bool:
        """
        Обновление Telegram ID пользователя

        Args:
            phone_number: Номер телефона пользователя
            telegram_id: Новый Telegram ID

        Returns:
            True, если обновление успешно, иначе False
        """
        try:
            with get_db_session() as session:
                user = session.query(User).filter(User.phone_number == phone_number).first()
                if user:
                    user.telegram_id = telegram_id
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении Telegram ID для пользователя {phone_number}: {e}")
            return False

    @staticmethod
    def get_all_active_with_telegram() -> List[User]:
        """
        Получение всех активных пользователей с привязанным Telegram ID

        Returns:
            Список пользователей
        """
        try:
            with get_db_session() as session:
                return session.query(User).filter(
                    User.is_active == True,
                    User.telegram_id.isnot(None)
                ).all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении активных пользователей с Telegram: {e}")
            return []

    @staticmethod
    def create(phone_number: str, first_name: str, last_name: str, telegram_id: str = None) -> Optional[User]:
        """
        Создание нового пользователя

        Args:
            phone_number: Номер телефона
            first_name: Имя
            last_name: Фамилия
            telegram_id: Telegram ID (опционально)

        Returns:
            Объект созданного пользователя или None в случае ошибки
        """
        try:
            with get_db_session() as session:
                user = User(
                    phone_number=phone_number,
                    first_name=first_name,
                    last_name=last_name,
                    telegram_id=telegram_id
                )
                session.add(user)
                session.flush()
                return user
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
            return None