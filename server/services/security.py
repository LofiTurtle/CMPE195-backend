def validate_password(password: str) -> bool:
    """
    Checks if the password is valid.
    :param password: The password to validate
    :return: Whether the password meets all validation criteria
    """
    if len(password) < 8:
        return False

    return True
