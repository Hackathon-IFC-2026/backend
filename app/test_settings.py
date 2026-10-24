from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
SECRET_KEY = 'kando-local-test-key-only-0123456789-abcdefghijklmnopqrstuvwxyz'
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
FRONTEND_BASE_URL = 'https://kando.test'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
EMAIL_HOST = 'smtp.example.test'
EMAIL_HOST_USER = 'sender@example.com'
EMAIL_HOST_PASSWORD = 'test-only-password'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_PORT = 587
