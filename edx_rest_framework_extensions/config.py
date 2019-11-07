"""
Application configuration constants and code.
"""

# .. toggle_name: oauth2.enforce_jwt_scopes
# .. toggle_implementation: WaffleSwitch
# .. toggle_default: False
# .. toggle_description: Enforces JWT Scopes for an IDA. See https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/oauth_dispatch/docs/decisions/0006-enforce-scopes-in-LMS-APIs.rst  # noqa E501 line too long
# .. toggle_category: authorization
# .. toggle_use_cases: incremental_release
# .. toggle_creation_date: 2018-06-28
# .. toggle_expiration_date: 2020-12-31
# .. toggle_warnings: Toggle may be referenced from multiple IDAs.
# .. toggle_tickets: ARCH-154
# .. toggle_status: supported
OAUTH_TOGGLE_NAMESPACE = 'oauth2'  # IMPORTANT: Constant is part of the public api.  Do NOT rename.
SWITCH_ENFORCE_JWT_SCOPES = 'enforce_jwt_scopes'  # IMPORTANT: Constant is part of the public api.  Do NOT rename.
NAMESPACED_SWITCH_ENFORCE_JWT_SCOPES = '{}.{}'.format(OAUTH_TOGGLE_NAMESPACE, SWITCH_ENFORCE_JWT_SCOPES)

# .. toggle_name: EDX_DRF_EXTENSIONS[ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE]
# .. toggle_implementation: DjangoSetting
# .. toggle_default: False
# .. toggle_description: Toggle for setting request.user with jwt cookie authentication
# .. toggle_category: micro-frontend
# .. toggle_use_cases: incremental_release
# .. toggle_creation_date: 2019-10-15
# .. toggle_expiration_date: 2019-12-31
# .. toggle_warnings: This feature fixed ecommerce, but broke edx-platform. The toggle enables us to fix over time.
# .. toggle_tickets: ARCH-1210, ARCH-1199, ARCH-1197
# .. toggle_status: supported
ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE = 'ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE'

# .. toggle_name: EDX_DRF_EXTENSIONS[ENABLE_ANONYMOUS_ACCESS_ROLLOUT]
# .. toggle_implementation: DjangoSetting
# .. toggle_default: False
# .. toggle_description: Toggle for enabling some functionality related to anonymous access
# .. toggle_category: micro-frontend
# .. toggle_use_cases: incremental_release
# .. toggle_creation_date: 2019-11-06
# .. toggle_expiration_date: 2019-12-31
# .. toggle_warnings: Requires coordination with MFE updates of frontend-auth refactor.
# .. toggle_tickets: ARCH-1229
# .. toggle_status: supported
ENABLE_ANONYMOUS_ACCESS_ROLLOUT = 'ENABLE_ANONYMOUS_ACCESS_ROLLOUT'
