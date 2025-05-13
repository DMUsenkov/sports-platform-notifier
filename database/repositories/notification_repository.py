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
        try:
            from api.client import ApiClient
            import asyncio
            from datetime import datetime, timedelta
            import json

            # Создаем клиент для взаимодействия с API
            api_client = ApiClient()

            # Получаем матчи на ближайшие 2 дня
            # Запускаем асинхронный код в синхронном контексте
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Получаем матчи на ближайшие 2 дня
                matches = loop.run_until_complete(api_client.get_upcoming_matches(days=2))

                # Фильтруем матчи, которые будут через 24 часа
                tomorrow = datetime.now() + timedelta(days=1)
                tomorrow_start = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
                tomorrow_end = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59)

                tomorrow_matches = []
                for match in matches:
                    # Предполагается, что в матче есть поле date_time в ISO формате
                    if 'date_time' in match:
                        match_date_time = datetime.fromisoformat(match['date_time'])
                        if tomorrow_start <= match_date_time <= tomorrow_end:
                            tomorrow_matches.append(match)

                # Создаем уведомления для каждого участника матча
                notifications_count = 0

                with get_db_session() as session:
                    for match in tomorrow_matches:
                        # Получаем информацию о командах
                        team1 = loop.run_until_complete(api_client.get_team_details(match['team1_id']))
                        team2 = loop.run_until_complete(api_client.get_team_details(match['team2_id']))

                        # Создаем уведомления для участников обеих команд
                        for team, opponent in [(team1, team2), (team2, team1)]:
                            for member in team.get('members', []):
                                user = session.query(User).filter(User.id == member['user_id']).first()

                                if user and user.is_active and user.telegram_id:
                                    # Формируем метаданные для уведомления
                                    metadata = {
                                        'championship_name': match.get('tournament_name', ''),
                                        'opponent_name': opponent.get('name', ''),
                                        'match_date': match.get('date', '').split('T')[0] if 'date' in match else '',
                                        'match_time': match.get('time', ''),
                                        'venue': match.get('location_name', ''),
                                        'address': match.get('location_address', '')
                                    }

                                    # Создаем уведомление
                                    notification = Notification(
                                        user_id=user.id,
                                        type=NotificationType.MATCH_REMINDER,
                                        title="Напоминание о матче",
                                        content=f"Завтра у вашей команды матч в {match.get('time', '')}",
                                        metadata_json=json.dumps(metadata)
                                    )

                                    session.add(notification)
                                    notifications_count += 1

                logger.info(f"Создано {notifications_count} напоминаний о матчах")
                return notifications_count

            finally:
                # Закрываем event loop
                loop.close()

        except Exception as e:
            logger.error(f"Ошибка при создании напоминаний о матчах: {e}")
            return 0