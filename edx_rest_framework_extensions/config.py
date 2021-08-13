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
# .. toggle_creation_date: 2020-08-12
# .. toggle_target_removal_date: 2021-12-31
# .. toggle_tickets: https://openedx.atlassian.net/browse/ARCHBOM-1218
ENABLE_FORGIVING_JWT_COOKIES = 'ENABLE_FORGIVING_JWT_COOKIES'
