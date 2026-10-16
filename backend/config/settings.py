import os
from pathlib import Path
from urllib.parse import urlsplit
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY before starting production.')
    SECRET_KEY = 'local-development-only-do-not-use-in-production'
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]
render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5500/' if DEBUG else '').strip()
if FRONTEND_URL and '://' not in FRONTEND_URL:
    FRONTEND_URL = 'https://' + FRONTEND_URL
FRONTEND_URL = FRONTEND_URL.rstrip('/') + '/'
front = urlsplit(FRONTEND_URL)
if (not front.hostname or front.username or front.password or front.query or front.fragment
        or front.path != '/' or any(char.isspace() for char in FRONTEND_URL)
        or front.scheme not in ('http', 'https') or (not DEBUG and front.scheme != 'https')):
    raise ImproperlyConfigured('FRONTEND_URL must be an HTTPS directory URL without query or fragment.')
CORS_ALLOWED_ORIGINS = [f'{front.scheme}://{front.netloc}']
CORS_URLS_REGEX = r'^/api/'
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
SESSION_COOKIE_AGE = 28800
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
                 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
                 'corsheaders', 'exams']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
              'corsheaders.middleware.CorsMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
              'OPTIONS': {'context_processors': ['django.template.context_processors.request',
                         'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
database_url = os.environ.get('DATABASE_URL', '').strip()
if not DEBUG and not database_url:
    raise ImproperlyConfigured('Set DATABASE_URL to persistent PostgreSQL in production.')
DATABASES = {'default': dj_database_url.parse(database_url, conn_max_age=0) if database_url else
             {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
if database_url:
    db = DATABASES['default']
    if db['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('DATABASE_URL must be a PostgreSQL connection URL from Neon.')
    # Compatible with Neon's pooled endpoint and Django ASGI requests.
    db['DISABLE_SERVER_SIDE_CURSORS'] = True
    db.setdefault('OPTIONS', {}).setdefault('connect_timeout', 10)
    db['OPTIONS'].setdefault('sslmode', 'require')
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = 'no-referrer'
DATA_UPLOAD_MAX_MEMORY_SIZE = 16384
