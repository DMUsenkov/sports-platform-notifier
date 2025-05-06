import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_

from database.connection import get_db_session
from database.models import Notification, NotificationType, User

logger = logging.getLogger(__name__)


class NotificationRepository:
    """
    Репозиторий для работы с уведомлениями
    """

    @staticmethod
    def create(
            user_id: int,
            notification_type: NotificationType,
            title: str,
            content: str,
            metadata: Dict[str, Any] = None,
            scheduled_for: datetime = None
    ) -> Optional[Notification]:
        """
        Создание нового уведомления

        Args:
            user_id: ID пользователя
            notification_type: Тип уведомления
            title: Заголовок уведомления
            content: Содержание уведомления
            metadata: Дополнительные данные (опционально)
            scheduled_for: Время запланированной отправки (опционально)

        Returns:
            Объект созданного уведомления или None в случае ошибки
        """
        try:
            with get_db_session() as session:
                metadata_json = json.dumps(metadata) if metadata else None

                notification = Notification(
                    user_id=user_id,
                    type=notification_type,
                    title=title,
                    content=content,
                    metadata_json=metadata_json,  # Изменено с metadata на metadata_json
                    scheduled_for=scheduled_for
                )
                session.add(notification)
                session.flush()
                return notification
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при создании уведомления: {e}")
            return None

    @staticmethod
    def get_pending_notifications(limit: int = 100) -> List[Notification]:
        """
        Получение списка неотправленных уведомлений, которые нужно отправить

        Args:
            limit: Максимальное количество уведомлений

        Returns:
            Список уведомлений
        """
        try:
            with get_db_session() as session:
                now = datetime.now()

                # Получаем уведомления, которые еще не отправлены и либо не запланированы,
                # либо время отправки уже наступило
                return session.query(Notification).join(User).filter(
                    and_(
                        Notification.is_sent == False,
                        User.telegram_id.isnot(None),
                        User.is_active == True,
                        or_(
                            Notification.scheduled_for.is_(None),
                            Notification.scheduled_for <= now
                        )
                    )
                ).order_by(Notification.created_at).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении неотправленных уведомлений: {e}")
            return []

    @staticmethod
    def mark_as_sent(notification_id: int) -> bool:
        """
        Пометить уведомление как отправленное

        Args:
            notification_id: ID уведомления

        Returns:
            True, если обновление успешно, иначе False
        """
        try:
            with get_db_session() as session:
                notification = session.query(Notification).filter(Notification.id == notification_id).first()
                if notification:
                    notification.is_sent = True
                    notification.sent_at = datetime.now()
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении статуса уведомления {notification_id}: {e}")
            return False

    @staticmethod
    def delete_old_sent_notifications(days: int = 30) -> int:
        """
        Удаление старых отправленных уведомлений

        Args:
            days: Количество дней, после которых уведомления считаются устаревшими

        Returns:
            Количество удаленных уведомлений
        """
        try:
            with get_db_session() as session:
                from datetime import timedelta
                cutoff_date = datetime.now() - timedelta(days=days)

                # Получаем количество уведомлений для удаления
                count = session.query(Notification).filter(
                    and_(
                        Notification.is_sent == True,
                        Notification.sent_at <= cutoff_date
                    )
                ).count()

                # Удаляем уведомления
                session.query(Notification).filter(
                    and_(
                        Notification.is_sent == True,
                        Notification.sent_at <= cutoff_date
                    )
                ).delete(synchronize_session=False)

                return count
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при удалении старых уведомлений: {e}")
            return 0

    @staticmethod
    def create_match_reminder_notifications() -> int:
        """
        Создание напоминаний о матчах, которые будут через 24 часа

        Returns:
            Количество созданных уведомлений
        """
        # Примечание: Это заглушка, в реальном приложении здесь будет логика
        # для получения информации о матчах из основного приложения через API
        return 0