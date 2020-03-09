"""
These settings are here to use during tests, because django requires them.

In a real-world use case, apps in this project are installed into other
Django applications, so these settings will not be used.
"""

SECRET_KEY = 'insecure-secret-key'

ROOT_URLCONF = 'csrf.urls'

INSTALLED_APPS = (
    'csrf.apps.CsrfAppConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'edx_rest_framework_extensions',
    'rest_framework_jwt',
    'waffle',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'default.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

EDX_DRF_EXTENSIONS = {}

# USER_SETTINGS overrides for djangorestframework-jwt APISettings class
# See https://github.com/GetBlimp/django-rest-framework-jwt/blob/master/rest_framework_jwt/settings.py
JWT_AUTH = {

    'JWT_AUDIENCE': 'test-aud',

    'JWT_DECODE_HANDLER': 'edx_rest_framework_extensions.auth.jwt.decoder.jwt_decode_handler',

    'JWT_ISSUER': 'test-iss',

    'JWT_LEEWAY': 1,

    'JWT_SECRET_KEY': 'test-key',

    'JWT_SUPPORTED_VERSION': '1.0.0',

    'JWT_VERIFY_AUDIENCE': False,

    'JWT_VERIFY_EXPIRATION': True,

    'JWT_AUTH_HEADER_PREFIX': 'JWT',
    # JWT_ISSUERS enables token decoding for multiple issuers (Note: This is not a native DRF-JWT field)
    # We use it to allow different values for the 'ISSUER' field, but keep the same SECRET_KEY and
    # AUDIENCE values across all issuers.
    'JWT_ISSUERS': [
        {
            'ISSUER': 'test-issuer-1',
            'SECRET_KEY': 'test-secret-key',
            'AUDIENCE': 'test-audience',
        },
        {
            'ISSUER': 'test-issuer-2',
            'SECRET_KEY': 'test-secret-key',
            'AUDIENCE': 'test-audience',
        }
    ],
}
