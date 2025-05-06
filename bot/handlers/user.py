# Обновленный обработчик запроса "Мои матчи"
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
        # Получаем список матчей пользователя через API
        matches = await api_client.get_user_matches(user.id, status="upcoming")

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
        logger.error(f"Ошибка при получении матчей пользователя {user.id}: {e}")
        await message.answer(
            "Произошла ошибка при получении информации о матчах. Пожалуйста, попробуйте позже."
        )


# Обновленный обработчик запроса "Мои чемпионаты"
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
        # Получаем список чемпионатов пользователя через API
        championships = await api_client.get_user_championships(user.id)

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
        logger.error(f"Ошибка при получении чемпионатов пользователя {user.id}: {e}")
        await message.answer(
            "Произошла ошибка при получении информации о чемпионатах. Пожалуйста, попробуйте позже."
        )


# Обновленный обработчик запроса "Мои команды"
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
        # Получаем список команд пользователя через API
        teams = await api_client.get_user_teams(user.id)

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
        logger.error(f"Ошибка при получении команд пользователя {user.id}: {e}")
        await message.answer(
            "Произошла ошибка при получении информации о командах. Пожалуйста, попробуйте позже."
        )


# Новый обработчик для просмотра деталей команды
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
        logger.error(f"Ошибка при получении информации о команде: {e}")
        await message.answer(
            "Произошла ошибка при получении информации о команде. Пожалуйста, попробуйте позже."
        )


# Новая команда для просмотра приглашений
@dp.message_handler(commands=['invitations'])
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
        # Получаем список приглашений пользователя через API
        invitations = await api_client.get_user_invitations(user.id)

        if not invitations:
            await message.answer("У вас нет активных приглашений.")
            return

        # Формируем сообщение с информацией о приглашениях
        response = "📨 Ваши приглашения:\n\n"

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

    except Exception as e:
        logger.error(f"Ошибка при получении приглашений пользователя {user.id}: {e}")
        await message.answer(
            "Произошла ошибка при получении информации о приглашениях. Пожалуйста, попробуйте позже."
        )


# Обновленный обработчик команды /help
@dp.message_handler(commands=['help'])
@dp.message_handler(lambda message: message.text == "Помощь")
async def cmd_help(message: types.Message):
    """
    Обработчик команды /help

    Args:
        message: Сообщение от пользователя
    """
    help_text = (
        "📱 *Доступные команды:*\n\n"
        "• /start - начать работу с ботом\n"
        "• /help - показать это сообщение\n"
        "• /invitations - просмотр активных приглашений\n"
        "• /changephone - изменить номер телефона\n\n"

        "🏠 *Навигация:*\n"
        "• Мои матчи - просмотр предстоящих матчей\n"
        "• Мои чемпионаты - просмотр чемпионатов\n"
        "• Мои команды - просмотр ваших команд\n"
        "• Рекомендуемые чемпионаты - чемпионаты, которые могут вас заинтересовать\n"
        "• Приглашения - просмотр активных приглашений\n\n"

        "📝 *Дополнительные команды:*\n"
        "• /team_ID - просмотр информации о команде (например, /team_123)\n"
        "• /match_ID - просмотр информации о матче (например, /match_456)\n"
        "• /championship_ID - просмотр информации о чемпионате (например, /championship_789)\n\n"

        "❓ *Нужна помощь?*\n"
        "Если у вас возникли вопросы или проблемы, пожалуйста, напишите нам на support@sports-platform.ru"
    )

    await message.answer(help_text, parse_mode="Markdown", reply_markup=get_start_keyboard())