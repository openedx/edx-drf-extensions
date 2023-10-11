"""
Application configuration constants and code.
"""

# .. toggle_name: EDX_DRF_EXTENSIONS[ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE]
# .. toggle_implementation: DjangoSetting
# .. toggle_default: False
# .. toggle_description: Toggle for setting request.user with jwt cookie authentication
# .. toggle_use_cases: temporary
# .. toggle_creation_date: 2019-10-15
# .. toggle_target_removal_date: 2019-12-31
# .. toggle_warning: This feature fixed ecommerce, but broke edx-platform. The toggle enables us to fix over time.
# .. toggle_tickets: ARCH-1210, ARCH-1199, ARCH-1197
ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE = 'ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE'

# .. toggle_name: EDX_DRF_EXTENSIONS[ENABLE_FORGIVING_JWT_COOKIES]
# .. toggle_implementation: DjangoSetting
# .. toggle_default: False
# .. toggle_description: If True, return None rather than an exception when authentication fails with JWT cookies.
# .. toggle_use_cases: temporary
# .. toggle_creation_date: 2023-08-01
# .. toggle_target_removal_date: 2023-10-01
# .. toggle_tickets: https://github.com/openedx/edx-drf-extensions/issues/371
ENABLE_FORGIVING_JWT_COOKIES = 'ENABLE_FORGIVING_JWT_COOKIES'

# .. toggle_name: EDX_DRF_EXTENSIONS[ENABLE_JWT_VS_SESSION_USER_CHECK]
# .. toggle_implementation: DjangoSetting
# .. toggle_default: False
# .. toggle_description: If True, checks for mismatches of JWT cookie user and session user. If forgiving
#       JWT cookies is also enabled, mismatches will result in an error, rather than being forgiving. Also
#       adds monitoring of session user vs JWT cookie user.
# .. toggle_warning: Since edx-platform has user caching, this toggle is a safety valve in case it
#       starts causing memory issues, as has happened in the past. See ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE.
# .. toggle_use_cases: temporary
# .. toggle_creation_date: 2023-10-04
# .. toggle_target_removal_date: 2023-12-01
# .. toggle_tickets: https://github.com/openedx/edx-drf-extensions/issues/371
ENABLE_JWT_VS_SESSION_USER_CHECK = 'ENABLE_JWT_VS_SESSION_USER_CHECK'
