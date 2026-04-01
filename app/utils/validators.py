import re


USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")


def validate_username(username: str) -> bool:
    return bool(USERNAME_REGEX.fullmatch(username))


def validate_password(password: str) -> bool:
    # Minimum 8 chars with at least one letter and one number.
    if len(password) < 8:
        return False
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return has_letter and has_digit
