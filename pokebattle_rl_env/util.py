from secrets import choice
from string import ascii_lowercase, ascii_letters, digits


def generate_username():
    return generate_token(8, lower=True)


def generate_token(length, lower=False):
    return ''.join(choice(digits + ascii_lowercase if lower else ascii_letters) for i in range(length))
