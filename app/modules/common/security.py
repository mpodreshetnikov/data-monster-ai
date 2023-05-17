def set_users_white_list(user_ids: list[str]):
    global __white_list__
    __white_list__ = user_ids

def is_user_allowed(user_id: str) -> bool:
    if not __white_list__:
        return True
    if user_id in __white_list__:
        return True
    return False