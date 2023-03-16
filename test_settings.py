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
        '{"keys": [{"use": "sig", "e": "AQAB", "kty": "RSA", "alg": "RS512", "n": "kuI1T8prOHqX7Q9ARgyi7DsyLGMEGOmhPefU'
        'dQpeE4RGGHiyxcQrGzqde2zjEdhinjpK_lo03StB5l9JDgyDjjd-R3bWUl1iC4gQY4aaP0kqg8iC_Fz5Kih9egCQd8_o_C1fi-iiWSWTDWyYtv'
        '0qHdaCslKnzXfNxvoIWRMvhtCMfgekAy3EaGtPEEnuW5bkA-N3ZQvBIIZDmyqW8k3YvrUb7klMUTulsPhybjOZ1uUaMmd8N3fEYEHtXgPO0SON'
        '2T0cuw9cDJ82ICPmXYgQsnZvEiaDC5eUENo-OUnutjR7JVNj8qqeCEU8Nhn05Ob1dqfmkwX_666ifgps8q-k6w", "kid": "BTZ9HA6K"}]}'
    ),

    'JWT_PRIVATE_SIGNING_JWK': (
        '{"alg": "RS512", "d": "dlW2O51JeowR4BO8ZXMCwy0BxA7VmziGBfjDCrQajMCxND_xTzE2xU4Y1_omihb5hJ5UEs0b799MzUuQ8LeWOTp'
        'uCycrjdncBoxNH9GubTQGA3vEQ4qn1pYeWO8hdNVUz-3CH1aBjS6fZV5LPomBp95NF1tOA1P0vcxsc07oqEQWuFGmhoEoasTtEQ5z1_4qMpRek'
        '37YBZkPMQjnqJpb9w9o5ysHlfKHZk2TS6WQQWVlrePqkILnAiZ_Dh0esF5K4l3Y7OuTXpyEjF3VLzQt9CgN5WsECxThSu-1-o7jm6vYgyr9df2'
        'QuYBEkc8T7ub_YoozGWHRRyiDzql6LuRoWQ", "dp": "3WL7vpeUH84Wm9dNv5x1OVGvkvIYZlf26KBvbD_qkGOBUuJeM5PoxZfqBSieCzaAW'
        'EB6cJu2dXXTgJ_CG0freaqvfDL0ZaOz2LuJ30rDNfYTPXeWJ-xHVBVtfETBHOim_s6SLa65OXkL3wYCMqUmmshwcr_qUcDlhC_mVAfx9d8", '
        '"dq": "Yia4MRROCSMRYQfaoJWgV47pVyvmqsQbPP9xpSfHRDT0K2CUSiQbNCP7cPfpEaOKZgxVBwSoLR5cv5Y8CDIarsfVTh1AwhrZLp5jd2o'
        'XLHwEuB90_mqKDdSR9_nqlvuNbVrradqJ8xdGsuJHS3fHGrfPDlCdRYEMJPLqFXdkLxk", "use": "sig", "e": "AQAB", "kty": "RSA"'
        ', "n": "kuI1T8prOHqX7Q9ARgyi7DsyLGMEGOmhPefUdQpeE4RGGHiyxcQrGzqde2zjEdhinjpK_lo03StB5l9JDgyDjjd-R3bWUl1iC4gQY4'
        'aaP0kqg8iC_Fz5Kih9egCQd8_o_C1fi-iiWSWTDWyYtv0qHdaCslKnzXfNxvoIWRMvhtCMfgekAy3EaGtPEEnuW5bkA-N3ZQvBIIZDmyqW8k3Y'
        'vrUb7klMUTulsPhybjOZ1uUaMmd8N3fEYEHtXgPO0SON2T0cuw9cDJ82ICPmXYgQsnZvEiaDC5eUENo-OUnutjR7JVNj8qqeCEU8Nhn05Ob1dq'
        'fmkwX_666ifgps8q-k6w", "q": "nSD4SDeGN_ZCr7oipXcoRDtjNCxcPcAg0xSD2Xz7dcCLE6cZpK2tO2oRHXlqWrPYyfNWYTzdeuT1q0xTf'
        'CrkGmFAtZ0Ql6dsR6LDUPDSDc1nxOT0d8-6HWHWuzMn8IezUIIGTueSufuIpj7ShiQpFnFY0s-osPwLsZodPjrqvd0", "p": "707mfZ0Uodz'
        'Jc1N6uDLs-iW6CZeGzVHuu52M-emokn4Hbt3GCN4VOmcm0jGgckKvzp5Ggp_3SjfmdNSrJ7y04KQSDN8qNr-CU4ZjkVeLkOwn0uIGCTToYrkTE'
        'kEj_psJqazmGuaHs0wHr2B_7LWV37YjdNB0v3214nDTIv4AtWc", "qi": "eX5DBm6Regly1ww-zxPilZxENtOfaEh8k0THaxlc7slUfXUdlL'
        'wJEE1u53f_35eI4AH1szypBIXjNx2fSBYVLa1GFYz2zxJpp8nurRK-if6F563Wh3pU7USqXvYPne868LyOLhWH_hriLlI7e8maGJbVL-YwhYnP'
        '-DEt-_xjPkM", "kid": "BTZ9HA6K"}'
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
