import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

from config.config import DATABASE_URL

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем движок SQLAlchemy для подключения к PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
)

# Создаем фабрику сессий
session_factory = sessionmaker(bind=engine)

# Создаем объект Session, который будет связан с текущим потоком
Session = scoped_session(session_factory)

logger = logging.getLogger(__name__)

@contextmanager
def get_db_session():
    """
    Контекстный менеджер для работы с сессией базы данных.
    Автоматически закрывает сессию после использования.
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при работе с базой данных: {e}")
        raise
    finally:
        session.close()

def init_db():
    """
    Инициализирует базу данных и создает все необходимые таблицы.
    """
    try:
        # Создаем все таблицы
        Base.metadata.create_all(engine)
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise