# Добавление новых клавиатур

def get_match_actions_keyboard(match_id: int, team_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для действий с матчем

    Args:
        match_id: ID матча
        team_id: ID команды пользователя

    Returns:
        InlineKeyboardMarkup: Клавиатура с действиями для матча
    """
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Отклонить участие", callback_data=f"decline_match_{match_id}_{team_id}")
    )
    return keyboard


def get_team_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Расширенная клавиатура для работы с командами

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками меню команд
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Мои команды"))
    keyboard.add(KeyboardButton("Приглашения"), KeyboardButton("Мои матчи"))
    keyboard.add(KeyboardButton("Главное меню"))
    return keyboard


def get_championship_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура для работы с чемпионатами

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками меню чемпионатов
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Мои чемпионаты"))
    keyboard.add(KeyboardButton("Рекомендуемые чемпионаты"))
    keyboard.add(KeyboardButton("Главное меню"))
    return keyboard

def get_start_keyboard() -> ReplyKeyboardMarkup:
    """
    Основная клавиатура для работы с ботом

    Returns:
        ReplyKeyboardMarkup: Основная клавиатура с кнопками меню
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Мои матчи"))
    keyboard.add(KeyboardButton("Мои чемпионаты"), KeyboardButton("Мои команды"))
    keyboard.add(KeyboardButton("Рекомендуемые чемпионаты"), KeyboardButton("Приглашения"))
    keyboard.add(KeyboardButton("Помощь"))
    return keyboard