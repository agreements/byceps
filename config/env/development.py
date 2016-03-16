from datetime import timedelta
from pathlib import Path


DEBUG = True
PERMANENT_SESSION_LIFETIME = timedelta(14)
SECRET_KEY = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
SESSION_COOKIE_SECURE = True

LOCALE = 'de_DE.UTF-8'
LOCALES_FORMS = ['de']

SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://byceps:boioioing@127.0.0.1/byceps'
SQLALCHEMY_ECHO = False

REDIS_URL = 'redis://127.0.0.1:6379/0'

MODE = 'public'
PARTY = 'example-party-1'

PATH_DATA = Path('./data')
PATH_CONTENT = PATH_DATA / 'party_content' / PARTY
PATH_USER_AVATAR_IMAGES = PATH_DATA / 'users/avatars'

BOARD_TOPICS_PER_PAGE = 10
BOARD_POSTINGS_PER_PAGE = 10

MAIL_DEBUG = True
MAIL_DEFAULT_SENDER = 'BYCEPS <noreply@example.com>'
MAIL_SUPPRESS_SEND = True