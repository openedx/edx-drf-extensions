"""
Settings for edx-drf-extensions are all namespaced in the EDX_DRF_EXTENSIONS setting.
For example your project's `settings.py` file might look like this:

EDX_DRF_EXTENSIONS = {
    'OAUTH2_ACCESS_TOKEN_URL': 'https://example.com/oauth2/access_token'
}
"""

from django.conf import settings

DEFAULT_SETTINGS = {
    'OAUTH2_USER_INFO_URL': None,

    # Map JWT claims to user attributes.
    'JWT_PAYLOAD_USER_ATTRIBUTE_MAPPING': {
        'administrator': 'is_staff',
        'email': 'email',
    },
}


def get_setting(name):
    """ Returns the value of the named setting.

        Arguments:
            name (str): Name of the setting to retrieve

        Raises:
            KeyError: The specified setting does not exist.
    """
    try:
        return getattr(settings, 'EDX_DRF_EXTENSIONS', {})[name]
    except KeyError:
        return DEFAULT_SETTINGS[name]
