# Дополнения к файлу api/client.py

async def get_user_teams(self, user_id: int) -> List[Dict[str, Any]]:
    """
    Получение команд пользователя

    Args:
        user_id: ID пользователя

    Returns:
        Список команд пользователя
    """
    return await self._make_request("GET", f"users/{user_id}/teams")


async def get_user_championships(self, user_id: int) -> List[Dict[str, Any]]:
    """
    Получение чемпионатов пользователя

    Args:
        user_id: ID пользователя

    Returns:
        Список чемпионатов пользователя
    """
    return await self._make_request("GET", f"users/{user_id}/championships")


async def get_user_matches(self, user_id: int, status: str = "upcoming") -> List[Dict[str, Any]]:
    """
    Получение матчей пользователя

    Args:
        user_id: ID пользователя
        status: Статус матчей ("upcoming", "past", "all")

    Returns:
        Список матчей пользователя
    """
    return await self._make_request("GET", f"users/{user_id}/matches", {"status": status})


async def get_team_details(self, team_id: int) -> Dict[str, Any]:
    """
    Получение детальной информации о команде

    Args:
        team_id: ID команды

    Returns:
        Информация о команде
    """
    return await self._make_request("GET", f"teams/{team_id}")


async def get_championship_details(self, tournament_id: int) -> Dict[str, Any]:
    """
    Получение детальной информации о чемпионате

    Args:
        tournament_id: ID чемпионата

    Returns:
        Информация о чемпионате
    """
    return await self._make_request("GET", f"championships/{tournament_id}")


async def accept_team_invitation(self, invitation_id: int) -> Dict[str, Any]:
    """
    Принятие приглашения в команду

    Args:
        invitation_id: ID приглашения

    Returns:
        Результат операции
    """
    return await self._make_request("POST", f"invitations/team/{invitation_id}/accept")


async def decline_team_invitation(self, invitation_id: int) -> Dict[str, Any]:
    """
    Отклонение приглашения в команду

    Args:
        invitation_id: ID приглашения

    Returns:
        Результат операции
    """
    return await self._make_request("POST", f"invitations/team/{invitation_id}/decline")


async def accept_committee_invitation(self, invitation_id: int) -> Dict[str, Any]:
    """
    Принятие приглашения в оргкомитет

    Args:
        invitation_id: ID приглашения

    Returns:
        Результат операции
    """
    return await self._make_request("POST", f"invitations/committee/{invitation_id}/accept")


async def decline_committee_invitation(self, invitation_id: int) -> Dict[str, Any]:
    """
    Отклонение приглашения в оргкомитет

    Args:
        invitation_id: ID приглашения

    Returns:
        Результат операции
    """
    return await self._make_request("POST", f"invitations/committee/{invitation_id}/decline")


async def get_user_invitations(self, user_id: int, type: str = "all") -> List[Dict[str, Any]]:
    """
    Получение приглашений пользователя

    Args:
        user_id: ID пользователя
        type: Тип приглашений ("team", "committee", "all")

    Returns:
        Список приглашений
    """
    return await self._make_request("GET", f"users/{user_id}/invitations", {"type": type})


async def decline_match(self, match_id: int, team_id: int, reason: str) -> Dict[str, Any]:
    """
    Отклонение участия в матче

    Args:
        match_id: ID матча
        team_id: ID команды
        reason: Причина отказа

    Returns:
        Результат операции
    """
    data = {
        "team_id": team_id,
        "reason": reason
    }
    return await self._make_request("POST", f"matches/{match_id}/decline", data)