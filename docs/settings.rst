Settings
========

All settings for this package reside in a dict, `EDX_DRF_EXTENSIONS`. Within this dict, the following keys should be
specified, depending on the functionality you are using.


BearerAuthentication
--------------------

.. py:currentmodule:: edx_rest_framework_extensions

These settings are used by the :class:`~authentication.BearerAuthentication` class.

``OAUTH2_USER_INFO_URL``
~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``None``

URL of an endpoint on the OAuth2 provider where :class:`~authentication.BearerAuthentication` can retrieve details
about the user associated with the provided access token. This endpoint should return a JSON object with user details
and ``HTTP 200`` if, and only if, the access token is valid. See
:meth:`BearerAuthentication.process_user_info_response() <authentication.BearerAuthentication.process_user_info_response>`
for an example of the expected data format.


JwtAuthentication
-----------------

.. py:currentmodule:: edx_rest_framework_extensions

These settings are used by the :class:`~authentication.JwtAuthentication` class. Since this class is based on
:class:`JSONWebTokenAuthentication`, most of its settings can be found in the documentation for ``rest_framework_jwt``
at http://getblimp.github.io/django-rest-framework-jwt/#additional-settings.

``JWT_AUTH['JWT_VERIFY_AUDIENCE']``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``True``

If you do *not* want to verify the JWT audience, set the ``'JWT_VERIFY_AUDIENCE'`` key in the ``JWT_AUTH`` setting
to ``False``.


``JWT_PAYLOAD_USER_ATTRIBUTES``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: ``('email',)``

The list of user attributes in the JWT payload that :class:`~authentication.JwtAuthentication` will use to update the
local ``User`` model. These payload attributes should exactly match the names the attributes on the local ``User``
model.
