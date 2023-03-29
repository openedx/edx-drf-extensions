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

    'JWT_PUBLIC_SIGNING_JWK_SET': (
        '{"keys": ['
            '{'  # noqa: E131
                '"e": "AQAB",'  # noqa: E131
                '"key_ops": ['
                    '"verify"'
                '],'
                '"kty": "RSA",'
                '"n": "2mAhTY3TjBGEg60l5ACLHGh1w89I8s7BEZtbnEQo0LkkIQha-lYiVT4N'
                    'MKqnKua3lvNP7x-tQzoniWjY2gELzx_K34G8hDqsUyHRPBQfeBC1K7Cah3'
                    'bbCSk0uI0tQcfwuywf-C4gTEI2sV9OpppN7hWdL6vUKpeBhvLejuInD22G'
                    'Mbsi5HT46dFf9M-2SZ3rJSZmF0HJ2oQFlP5-fi3AN4nDokLpURgHNpCzJP'
                    '73NL5UUqIKkrHOaggWS7TIGPoEW5FKDHkHZ4vmtWYFDh1noJyKQ0DxN6Es'
                    'Hn-o045yVlRHo1eiYo2_M62VrfUPuMbuRUUzIcSskN1wZIpXICcwDw"'
                '}'
        ']}'
    ),

    'JWT_PRIVATE_SIGNING_JWK': (
        '{'
            '"d": "WDPEr8TtoaD_s4mviLh5d6dvjX-_WKcOz1Q_O85B6BAnmhn8WSmKI4D1Jed_'  # noqa: E131
                'rrHSjGtJKW3TdxhZmMQa9m6-vNF8CSunH4dtTASYNNpx3XZuHq_tsnJcxQX6L-KB2Z'  # noqa: E131
                'Ru1MLdRMoorHSAD8NNirg_ar8bJoKSJwPbwsx8_Rw2J6HXa0mxhD4OqcvfbP3YgN9b'
                'Tv3OJyQDaoRQrr7Z28yvJuhKLeDVp3e1E4KYMV-vBRgPWZEJqZgzxxEbjOedvGvmrk'
                'dUDST8XQz5NL90ezbwd_kjZhQbtDWvmRUzHlp6m1H0jA9_JgPwVcZyD5rRCyJsdfdY'
                '2xaD0kViWPiJPVV6jQ",'
            '"dp": "udffOX_mT2RFUbgmjivd4hVD4dv8GYLnC4e4gQeMAkR1VGZZ748bVLpPWgB'
                'pgtZZPc2-gUwKLeJE1vqtvMqWKOYYb0sw1lZlLA3te0OCxZsWAkYSezbtD7xDOghmP'
                '5fR3lopoQFAGAGA9RHzBpevpaYWpGfvOnVbnoN5isjFVs0",'
            '"dq": "dUGJbJzMG8ER3fnWIKas-WndxT2qiu1_nkmRFT6fRz9A2QrP6qQt_kUyj33'
                'L3yNFefrTYth2zUQ5YfgRa4UESweX1qoTBfMR7pI0eJux7aXHNqC5jul2EQDWI7dKl'
                'rPPWjn_wvPXldnVXRN0uTR2rSU2Hlf5_zBG-5D7qCzO_Gk",'
            '"e": "AQAB",'
            '"key_ops": ['
                '"sign"'
            '],'
            '"kty": "RSA",'
            '"n": "2mAhTY3TjBGEg60l5ACLHGh1w89I8s7BEZtbnEQo0LkkIQha-lYiVT4NMKqn'
                'Kua3lvNP7x-tQzoniWjY2gELzx_K34G8hDqsUyHRPBQfeBC1K7Cah3bbCSk0uI0tQc'
                'fwuywf-C4gTEI2sV9OpppN7hWdL6vUKpeBhvLejuInD22GMbsi5HT46dFf9M-2SZ3r'
                'JSZmF0HJ2oQFlP5-fi3AN4nDokLpURgHNpCzJP73NL5UUqIKkrHOaggWS7TIGPoEW5'
                'FKDHkHZ4vmtWYFDh1noJyKQ0DxN6EsHn-o045yVlRHo1eiYo2_M62VrfUPuMbuRUUz'
                'IcSskN1wZIpXICcwDw",'
            '"p": "37Nh_BpKy2qm6IG8fdWbnTMU00jEOhxiIX2WjJZVkH3ld2ripBBWrv5uEE4b'
                'FFb8UuY08F-YwVNgquvjfDKbPFhwkfbXX5E9VXK-PqciVqydVQn_8xrGIc20GmxG3f'
                'oyADnQhpA0Bx3mNUIP7r9SWv_cPVgCMWQ-uQtBsj3InAs",'
            '"q": "-efpm0APY7ql3QgcD1u9mVLtyy4i7__SRrUeLWL1LRf-eHrBOTHoE72a54sk'
                'Y4_yqCNo_qZq-gOvZaEneYSvfuRNCyexJNTbmWa93xEe_2Gpa9gbb9UmZlMDBLDQLh'
                'MyyLcau1jZ3jYj_TWlXFYdawLf2CgHyRKVUc2cAd5keo0",'
            '"qi": "OsVy5_AL9KQK5FXjgdfd5naDpVZrtnDqZY3CTkz-ZHjTktUKjt866rm4Ed8'
                'tzL_cGOP0MsxzJ0H9ufxV2_5knYl3POXdB6UQUbd_bqB8oXKup78LpUKJIt4AjmxQG'
                'roR6zgbCPJLKQM5NIlf7eeaMVd6aBMTPwCx6PxidtVxcYk"'
        '}'
    ),

    'JWT_SIGNING_ALGORITHM': 'RS512',

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
