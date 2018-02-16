from secrets import choice
from string import ascii_letters, digits


def generate_username():
    return generate_token(8)


def generate_token(length):
    return ''.join(choice(ascii_letters + digits) for i in range(length))
