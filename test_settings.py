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

    'JWT_AUTH_COOKIE': 'edx-jwt-cookie',

    'JWT_AUDIENCE': 'test-aud',

    'JWT_DECODE_HANDLER': 'edx_rest_framework_extensions.auth.jwt.decoder.jwt_decode_handler',

    'JWT_ISSUER': 'test-iss',

    'JWT_LEEWAY': 1,

    'JWT_SECRET_KEY': 'test-key',

    'JWT_PUBLIC_SIGNING_JWK_SET': """
        {
          "keys": [
            {
              "kid": "BTZ9HA6K",
              "kty": "RSA",
              "n": "o5cn3ljSRi6FaDEKTn0PS-oL9EFyv1pI7dRgffQLD1qf5D6sprmYfWWokSsrWig8u2y0HChSygR6Jn5KXBqQn6FpM0dDJLnWQDRXHLl3Ey1iPYgDSmOIsIGrV9ZyNCQwk03wAgWbfdBTig3QSDYD-sTNOs3pc4UD_PqAvU2nz_1SS2ZiOwOn5F6gulE1L0iE3KEUEvOIagfHNVhz0oxa_VRZILkzV-zr6R_TW1m97h4H8jXl_VJyQGyhMGGypuDrQ9_vaY_RLEulLCyY0INglHWQ7pckxBtI5q55-Vio2wgewe2_qYcGsnBGaDNbySAsvYcWRrqDiFyzrJYivodqTQ",
              "e": "AQAB"
            }
          ]
        }
    """,  # noqa: E501

    'JWT_PRIVATE_SIGNING_JWK': """
        {
            "kid": "BTZ9HA6K",
            "kty": "RSA",
            "key_ops": [
                "sign"
            ],
            "n": "o5cn3ljSRi6FaDEKTn0PS-oL9EFyv1pI7dRgffQLD1qf5D6sprmYfWWokSsrWig8u2y0HChSygR6Jn5KXBqQn6FpM0dDJLnWQDRXHLl3Ey1iPYgDSmOIsIGrV9ZyNCQwk03wAgWbfdBTig3QSDYD-sTNOs3pc4UD_PqAvU2nz_1SS2ZiOwOn5F6gulE1L0iE3KEUEvOIagfHNVhz0oxa_VRZILkzV-zr6R_TW1m97h4H8jXl_VJyQGyhMGGypuDrQ9_vaY_RLEulLCyY0INglHWQ7pckxBtI5q55-Vio2wgewe2_qYcGsnBGaDNbySAsvYcWRrqDiFyzrJYivodqTQ",
            "e": "AQAB",
            "d": "HIiV7KNjcdhVbpn3KT-I9n3JPf5YbGXsCIedmPqDH1d4QhBofuAqZ9zebQuxkRUpmqtYMv0Zi6ECSUqH387GYQF_XvFUFcjQRPycISd8TH0DAKaDpGr-AYNshnKiEtQpINhcP44I1AYNPCwyoxXA1fGTtmkKChsuWea7o8kytwU5xSejvh5-jiqu2SF4GEl0BEXIAPZsgbzoPIWNxgO4_RzNnWs6nJZeszcaDD0CyezVSuH9QcI6g5QFzAC_YuykSsaaFJhZ05DocBsLczShJ9Omf6PnK9xlm26I84xrEh_7x4fVmNBg3xWTLh8qOnHqGko93A1diLRCrKHOvnpvgQ",
            "p": "3T3DEtBUka7hLGdIsDlC96Uadx_q_E4Vb1cxx_4Ss_wGp1Loz3N3ZngGyInsKlmbBgLo1Ykd6T9TRvRNEWEtFSOcm2INIBoVoXk7W5RuPa8Cgq2tjQj9ziGQ08JMejrPlj3Q1wmALJr5VTfvSYBu0WkljhKNCy1KB6fCby0C9WE",
            "q": "vUqzWPZnDG4IXyo-k5F0bHV0BNL_pVhQoLW7eyFHnw74IOEfSbdsMspNcPSFIrtgPsn7981qv3lN_staZ6JflKfHayjB_lvltHyZxfl0dvruShZOx1N6ykEo7YrAskC_qxUyrIvqmJ64zPW3jkuOYrFs7Ykj3zFx3Zq1H5568G0",
            "dp": "Azh08H8r2_sJuBXAzx_mQ6iZnAZQ619PnJFOXjTqnMgcaK8iSHLL2CgDIUQwteUcBphgP0uBrfWIBs5jmM8rUtVz4CcrPb5jdjhHjuu4NxmnFbPlhNoOp8OBUjPP3S-h-fPoaFjxDrUqz_zCdPVzp4S6UTkf6Hu-SiI9CFVFZ8E",
            "dq": "WQ44_KTIbIej9qnYUPMA1DoaAF8ImVDIdiOp9c79dC7FvCpN3w-lnuugrYDM1j9Tk5bRrY7-JuE6OaKQgOtajoS1BIxjYHj5xAVPD15CVevOihqeq5Zx0ZAAYmmCKRrfUe0iLx2QnIcoKH1-Azs23OXeeo6nysznZjvv9NVJv60",
            "qi": "KSWGH607H1kNG2okjYdmVdNgLxTUB-Wye9a9FNFE49UmQIOJeZYXtDzcjk8IiK3g-EU3CqBeDKVUgHvHFu4_Wj3IrIhKYizS4BeFmOcPDvylDQCmJcC9tXLQgHkxM_MEJ7iLn9FOLRshh7GPgZphXxMhezM26Cz-8r3_mACHu84"
        }
    """,  # noqa: E501

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
