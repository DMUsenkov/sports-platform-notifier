# Обновленные обработчики для колбэков от уведомлений
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('accept_team_'))
async def accept_team_invitation(callback_query: types.CallbackQuery):
    """
    Обработчик для принятия приглашения в команду

    Args:
        callback_query: Запрос от кнопки
    """
    await callback_query.answer("Обрабатываем ваше решение...")

    invitation_id = int(callback_query.data.split('_')[2])

    try:
        # Вызываем API для принятия приглашения
        result = await api_client.accept_team_invitation(invitation_id)

        if result.get('success'):
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n✅ Вы приняли приглашение! Вы теперь участник команды {result.get('team_name', '')}.",
                reply_markup=None
            )
        else:
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Не удалось принять приглашение: {result.get('error', 'неизвестная ошибка')}",
                reply_markup=None
            )
    except Exception as e:
        logger.error(f"Ошибка при принятии приглашения в команду {invitation_id}: {e}")
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
            reply_markup=None
        )


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('decline_team_'))
async def decline_team_invitation(callback_query: types.CallbackQuery):
    """
    Обработчик для отклонения приглашения в команду

    Args:
        callback_query: Запрос от кнопки
    """
    await callback_query.answer("Обрабатываем ваше решение...")

    invitation_id = int(callback_query.data.split('_')[2])

    try:
        # Вызываем API для отклонения приглашения
        result = await api_client.decline_team_invitation(invitation_id)

        if result.get('success'):
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Вы отклонили приглашение.",
                reply_markup=None
            )
        else:
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Не удалось отклонить приглашение: {result.get('error', 'неизвестная ошибка')}",
                reply_markup=None
            )
    except Exception as e:
        logger.error(f"Ошибка при отклонении приглашения в команду {invitation_id}: {e}")
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
            reply_markup=None
        )


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('accept_committee_'))
async def accept_committee_invitation(callback_query: types.CallbackQuery):
    """
    Обработчик для принятия приглашения в оргкомитет

    Args:
        callback_query: Запрос от кнопки
    """
    await callback_query.answer("Обрабатываем ваше решение...")

    invitation_id = int(callback_query.data.split('_')[2])

    try:
        # Вызываем API для принятия приглашения
        result = await api_client.accept_committee_invitation(invitation_id)

        if result.get('success'):
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n✅ Вы приняли приглашение! Вы теперь член оргкомитета {result.get('committee_name', '')}.",
                reply_markup=None
            )
        else:
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Не удалось принять приглашение: {result.get('error', 'неизвестная ошибка')}",
                reply_markup=None
            )
    except Exception as e:
        logger.error(f"Ошибка при принятии приглашения в оргкомитет {invitation_id}: {e}")
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
            reply_markup=None
        )


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('decline_committee_'))
async def decline_committee_invitation(callback_query: types.CallbackQuery):
    """
    Обработчик для отклонения приглашения в оргкомитет

    Args:
        callback_query: Запрос от кнопки
    """
    await callback_query.answer("Обрабатываем ваше решение...")

    invitation_id = int(callback_query.data.split('_')[2])

    try:
        # Вызываем API для отклонения приглашения
        result = await api_client.decline_committee_invitation(invitation_id)

        if result.get('success'):
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Вы отклонили приглашение.",
                reply_markup=None
            )
        else:
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n❌ Не удалось отклонить приглашение: {result.get('error', 'неизвестная ошибка')}",
                reply_markup=None
            )
    except Exception as e:
        logger.error(f"Ошибка при отклонении приглашения в оргкомитет {invitation_id}: {e}")
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n❌ Произошла ошибка при обработке приглашения. Пожалуйста, попробуйте позже.",
            reply_markup=None
        )