"""
Application configuration constants and code.
"""

# .. toggle_name: EDX_DRF_EXTENSIONS[ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE]
# .. toggle_implementation: DjangoSetting
# .. toggle_default: False
# .. toggle_description: Toggle for setting request.user with jwt cookie authentication. This makes the JWT cookie
#      user available to middleware while processing the request, if the session user wasn't already available. This
#      requires JwtAuthCookieMiddleware to work. It is recommended to set VERIFY_LMS_USER_ID_PROPERTY_NAME if possible
#      when using this feature.
# .. toggle_use_cases: temporary
# .. toggle_creation_date: 2019-10-15
# .. toggle_target_removal_date: 2024-12-31
# .. toggle_warning: This feature caused a memory leak in edx-platform. This toggle is temporary only if we can make it
#      work in all services, or find a replacement. Consider making this a permanent toggle instead.
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

# .. setting_name: EDX_DRF_EXTENSIONS[VERIFY_LMS_USER_ID_PROPERTY_NAME]
# .. setting_default: None ('lms_user_id' if found)
# .. setting_description: This setting should be set to the name of the user object property containing the LMS
#      user id, if one exists. Examples might be 'id' or 'lms_user_id'. To enhance security and provide ease of use
#      for this setting, if None is supplied, the property 'lms_user_id' will be used if found. In case of unforeseen
#      issues using lms_user_id, the check can be fully disabled using 'skip-check' as the property name. The default
#      was not set to 'lms_user_id' directly to avoid misconfiguration logging for services without an lms_user_id
#      property. The property named by this setting will be used by JWT cookie authentication to verify that the (LMS)
#      user id in the JWT is the same as the LMS user id for a service's session. This will cause failures in the case
#      of forgiving cookies, and will simply be used for additional monitoring for successful cookie authentication.
VERIFY_LMS_USER_ID_PROPERTY_NAME = 'VERIFY_LMS_USER_ID_PROPERTY_NAME'
