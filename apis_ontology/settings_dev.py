from .settings import *  # noqa: F403

SECRET_KEY = "unsecure_secret_key"
ALLOWED_HOSTS = ["localhost:8000", "127.0.0.1:8000"]
INSTALLED_APPS = INSTALLED_APPS + ["mine_frontend"]

DEBUG = True
