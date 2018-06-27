"""
Application configuration constants and code.
"""

NAMESPACE_SWITCH = 'oauth2'
SWITCH_ENFORCE_JWT_SCOPES = 'enforce_jwt_scopes'
NAMESPACED_SWITCH_ENFORCE_JWT_SCOPES = '{}.{}'.format(NAMESPACE_SWITCH, SWITCH_ENFORCE_JWT_SCOPES)
