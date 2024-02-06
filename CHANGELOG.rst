Change Log
==========

..
   This file loosely adheres to the structure of https://keepachangelog.com/,
   but in reStructuredText instead of Markdown.

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
----------

[10.2.0] - 2024-01-26
---------------------

* Subclasses base exception ``JwtAuthenticationError`` from Django Rest Framework's ``AuthenticationFailed`` exception, allowing ``JwtAuthenticationError`` to be recognized and handled by the default exception handler of the Django Rest Framework.

[10.1.0] - 2024-01-26
---------------------

* Added permanent toggle EDX_DRF_EXTENSIONS[ENABLE_JWT_AND_LMS_USER_EMAIL_MATCH]:

    * This toggle should only get enabled in the LMS, and should remain disabled in all other services.
    * If enabled, makes sure that the user email in JWT cookies and LMS user email matches
    * If email matches, it allows authentication otherwise raise JwtUserEmailMismatchError error.

[10.0.0] - 2023-11-30
---------------------

Removed
~~~~~~~
* **BREAKING CHANGE:** Removed ENABLE_FORGIVING_JWT_COOKIES toggle. It is now permanently enabled.

  * The header USE-JWT-COOKIE was removed because it has been fully replaced by forgiving JWTs.
  * Removed temporary rollout custom attributes: use_jwt_cookie_requested, jwt_auth_request_user_not_found, and skip_jwt_vs_session_check.

[9.1.2] - 2024-01-07
--------------------
Updated
~~~~~~~
* Restores and fixes simplified JWT cookie vs session user check by checking username instead of lms user id (originally introduced in 9.1.0, and removed in 9.1.1).

  * Removed ``VERIFY_LMS_USER_ID_PROPERTY_NAME``, which is no longer needed.
  * Removed custom attribute ``jwt_auth_get_lms_user_id_status``, since we no longer attempt to get the lms_user_id from the user object.
  * Renames custom attribute ``jwt_auth_mismatch_session_lms_user_id`` to ``jwt_auth_mismatch_session_username``.
  * Adds custom attribute ``jwt_auth_mismatch_jwt_cookie_username``.
  * Adds custom attribute ``jwt_cookie_unsafe_decode_issue`` for when a JWT cookie cannot even be unsafely decoded.
  * Fixes mock JWT creation for tests to use ``preferred_username``, which is configured in each Open edX service.

[9.1.1] - 2024-01-04
--------------------
Updated
~~~~~~~
* Reverted 9.1.0 change until issue can be fixed.

[9.1.0] - 2024-01-03
--------------------
Updated
~~~~~~~
* (Now reverted) Simplified JWT cookie vs session user check by checking username instead of lms user id. Note: this was reverted on 9.1.1.

[9.0.1] - 2023-12-06
--------------------

Fixed
~~~~~

* Fixed bug for successful JWTs where the JWT user id was still using the service user id, rather than the LMS user id, so comparison against the LMS user id would fail.

Updated
~~~~~~~

* As part of the bug fix, the custom attribute ``failed_jwt_cookie_user_id`` was renamed to ``jwt_cookie_lms_user_id``, and will be set for all JWT cookies. Since this is only a breaking change for recently added monitoring, this won't be versioned as a breaking change.

[9.0.0] - 2023-11-27
--------------------

Fixed
~~~~~
* **BREAKING CHANGE**: Fixes a bug for any service other than the identity service (LMS/CMS), where the session's local service user id would never match the JWT LMS user id when compared.

  * The custom attribute jwt_auth_mismatch_session_user_id was renamed to jwt_auth_mismatch_session_lms_user_id to make this more clear.
  * The setting EDX_DRF_EXTENSIONS[VERIFY_LMS_USER_ID_PROPERTY_NAME] was added to enable choosing the user object property that contains the LMS user id, if one exists. If this is set to None (the default), the check will use the lms_user_id property if it is found, and otherwise will skip this additional protection. In case of an unforeseen issue, use 'skip-check' to skip the check, even when there is an lms_user_id property.
  * The custom attribute jwt_auth_get_lms_user_id_status was added to provide observability into the new functionality.
  * The breaking change only affects services with ENABLE_FORGIVING_JWT_COOKIES enabled. It now requires the new setting VERIFY_LMS_USER_ID_PROPERTY_NAME to be set appropriately in order to provide the existing Session vs JWT user id check. Note that only LMS/CMS will likely need to set this value.

[8.13.1] - 2023-11-15
---------------------

Fixed
~~~~~
* Fixed bug where JwtAuthentication called with a Django request instead of a DRF request would fail. Also added custom attribute jwt_auth_request_user_not_found to track down these unexpected cases.

[8.13.0] - 2023-10-30
---------------------

Fixed
~~~~~
* Bug fix for when both ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE and the JWT cookie user vs session user check behind ENABLE_FORGIVING_JWT_COOKIES were enabled at the same time.

Added
~~~~~
* Added custom attributes set_user_from_jwt_status and skip_jwt_vs_session_check.

Updated
~~~~~~~
* ADR for removing HTTP_USE_JWT_COOKIE, which explains forgiven JWT cookies, was updated to explain the cases where the JWT cookie user and session user do not match.

Removed
~~~~~~~
* Toggle EDX_DRF_EXTENSIONS[ENABLE_JWT_VS_SESSION_USER_CHECK] has been removed. This check is now a default part of the ENABLE_FORGIVING_JWT_COOKIES functionality. ENABLE_JWT_VS_SESSION_USER_CHECK was just a temporary roll-out toggle that was already proven out everywhere ENABLE_FORGIVING_JWT_COOKIES was already enabled.

[8.12.0] - 2023-10-16
---------------------

Changed
~~~~~~~
* Made changes to the recent ENABLE_JWT_VS_SESSION_USER_CHECK custom attributes. Although this is technically a breaking change, skipping major release because of limited use of these attributes.

    * The jwt_auth_session_user_id attribute has been renamed to clarify that this attribute only appears in the case of a mismatch.
    * Dropped jwt_auth_and_session_user_mismatch, which is redundant to simply checking for the existence of jwt_auth_mismatch_session_user_id.
    * Updated annotations for jwt_auth_request_user_not_found, because it has proven to be a real case in Production and not just in testing.

[8.11.1] - 2023-10-11
---------------------

Added
~~~~~
* Added support for Django 4.2

[8.11.0] - 2023-10-04
---------------------

Added
~~~~~
* Added toggle EDX_DRF_EXTENSIONS[ENABLE_JWT_VS_SESSION_USER_CHECK] to enable the following:

    * New custom attributes is_jwt_vs_session_user_check_enabled, jwt_auth_session_user_id, jwt_auth_and_session_user_mismatch, and invalid_jwt_cookie_user_id for monitoring and debugging.
    * When forgiving JWT cookies are also enabled, user mismatches will now result in a failure, rather than a forgiving JWT.

Changed
~~~~~~~
* BREAKING CHANGE: For tests only, the test utility method generate_unversioned_payload now requires that the user argument contains an id attribute. In the case of a Mock user, you must set user.id.

[8.10.0] - 2023-09-19
---------------------

Added
~~~~~
* (`#354 <https://github.com/openedx/edx-drf-extensions/pull/354>`_) Implemented ``verify_jwk_signature_using_keyset`` function.
  This function allows for easy verification of JSON Web Key (JWK) signatures using a provided keyset.

[8.9.3] - 2023-09-13
--------------------

Fixed
~~~~~

* Added more useful exception logging when JWT auth fails.  The exception we
  get for that did not have enough detail about how the auth check failed so we
  dig deeper to an exception that is more useful and log that.

[8.9.2] - 2023-08-31
--------------------

Fixed
~~~~~
* Fixes exceptional case where JwtAuthentication should not CSRF protect a request that has both a JWT token in the authorization header and a JWT cookie, since the cookie should be ignored.

Changed
~~~~~~~
* Updated one of the values of the custom attribute jwt_auth_result from 'skipped' to 'n/a'.


[8.9.1] - 2023-08-22
--------------------

Removed
~~~~~~~

* Removed unused direct dependency on ``six``.
* Removed unused direct dependency on ``python-dateutil``.


Fixed
~~~~~
* Fixed Django 40 middleware deprecation warning

[8.9.0] - 2023-08-14
--------------------

Added
~~~~~

* Added capability to forgive JWT cookie authentication failures as a replacement for the now deprecated ``USE-JWT-COOKIE`` header. See DEPR https://github.com/openedx/edx-drf-extensions/issues/371.
  * For now, this capability must be enabled using the ``ENABLE_FORGIVING_JWT_COOKIES`` toggle.
  * Added temporary custom attributes ``is_forgiving_jwt_cookies_enabled`` and ``use_jwt_cookie_requested`` to help with this deprecation.
* Added custom attributes ``has_jwt_cookie`` and ``jwt_auth_result`` for JWT authentication observability.

Changed
~~~~~~~

* Two features that were gated on the presence of the ``USE-JWT-COOKIE`` header will now be gated on the presence of a JWT cookie instead, regardless of the state of the new ``ENABLE_FORGIVING_JWT_COOKIES`` toggle. The new behavior should be nearly equivalent in most cases, and should cause no issues in the exceptional cases. The two features include CSRF protection for JWT cookies, and the setting of the request user when ``ENABLE_SET_REQUEST_USER_FOR_JWT_COOKIE`` is enabled.

[8.8.0] - 2023-05-16
--------------------

Removed
~~~~~~~

* Removed dependency on ``pyjwkest``. Uses existing PyJWT dependency instead.

**Warning:** This change causes edx-drf-extensions to become a bit more strict about how it handles unexpected whitespace inside of Base64-encoded keys. For example, the following JSON is hard-wrapped inside a YAML single-quoted string, and edx-drf-extensions will start failing to load this in version 8.8.0::

    JWT_PUBLIC_SIGNING_JWK_SET: '{
      "keys": [
        {
          "e": "AQAB",
          "kid": "prod-key-001",
          "kty": "RSA",
          "n": "VGhpcyBpcyBqdXN0IHNvbWUgZGVtb25zdHJhd
             GlvbiB0ZXh0IHJhdGhlciB0aGFuIGFjdHVhbCBrZ
             XkgbWF0ZXJpYWwuICAK"
          }
        ]
      }'

Newlines are ignored within Base64, but are illegal inside JSON strings. However, the YAML parser actually replaces the newlines with single spaces due to the single-quoting, so the JSON will actually contain a modulus (``n``) value with two spaces breaking up the Base64. Spaces are in turn not allowed in Base64. Due to interactions between various Base64 parsers, URL-safe encoding, and how padding is handled by the Python base64 standard library, this will be read as intended by pyjwkest but not by PyJWT. This is not a bug, just a difference in how malformed inputs are handled.

The safe way to encode this JSON is without hard wrapping::

    JWT_PUBLIC_SIGNING_JWK_SET: |
      {
        "keys": [
          {
            "e": "AQAB",
            "kid": "prod-key-001",
            "kty": "RSA",
            "n": "VGhpcyBpcyBqdXN0IHNvbWUgZGVtb25zdHJhdGlvbiB0ZXh0IHJhdGhlciB0aGFuIGFjdHVhbCBrZXkgbWF0ZXJpYWwuICAK"
          }
        ]
      }

Before upgrading to version 8.8.0, ensure your keys are properly encoded with no whitespace of any sort inside of runs of Base64.

[8.7.0] - 2023-04-14
--------------------

Added
~~~~~

* Add ``edx_drf_extensions_version`` to help with rollout of changes in this library across services.

Removed
~~~~~~~

* Removed exception case for ``InvalidTokenError`` that was never invoked.

[8.6.0] - 2023-04-12
--------------------

Added
~~~~~

* Added ``jwt_auth_check_symmetric_key``, ``jwt_auth_asymmetric_verified``, ``jwt_auth_symmetric_verified``, and ``jwt_auth_verification_failed`` custom attributes to aid in deprecation and removal of symmetric keys.
* Added ``jwt_auth_issuer`` and ``jwt_auth_issuer_verification`` custom attributes.

Changed
~~~~~~~

* Changed ``jwt_auth_verify_keys_count`` custom attribute to aid in key rotations, to instead be ``jwt_auth_verify_asymmetric_keys_count`` and ``jwt_auth_verify_all_keys_count``. The latter count is only used in the case that the token can't be verified with the asymmetric keys alone.

[8.5.3] - 2023-04-11
--------------------

Fixed
~~~~~

* (Hopefully) fixed the ability to publish edx-drf-extensions, by adding a ``long_description`` to setup.py. There was no real 8.5.1 or 8.5.2.

[8.5.0] - 2023-04-05
--------------------

Added
~~~~~

* Added ``jwt_auth_verify_keys_count`` custom attribute to aid in key rotations

[8.4.1] - 2022-12-18
--------------------

Added
~~~~~

* Additional logging in `authenticate_credentials` within the JWT authentication middleware for debugging purposes.

[8.4.0] - 2022-12-16
--------------------

Added
~~~~~

* Added custom attribute enduser.id, following OpenTelemetry convention. This works with some New Relic automatic tooling around users. The old custom attribute request_user_id should be considered deprecated.

[8.3.1] - 2022-09-09
--------------------

Fixed
~~~~~~~

* Fixed disabled user error by reverting change to JwtAuthentication.

[8.3.0] - 2022-09-07
--------------------

Changed
~~~~~~~

* JwtAuthentication will fail for disabled users (with unusable password).

[8.2.0] - 2022-08-24
--------------------

Added
~~~~~

* Added only asymmetric jwt decoding functionality in decoder

Changed
~~~~~~~

* Rename toggle_warnings to toggle_warning for consistency with setting_warning.

[8.1.0] - 2022-01-28
--------------------

Dropped
~~~~~~~

* Dropped Support for Django22, 30, 31

[8.0.1] - 2021-11-01
--------------------

Changed
~~~~~~~

* Resolve RemovedInDjango4.0 warnings.


[8.0.0] - 2021-09-30
--------------------

Changed
~~~~~~~

* **BREAKING CHANGE:** Updated ``EnsureJWTAuthSettingsMiddleware`` to understand and work with permissions combined using DRF's in-built support. This allows switching away from ``rest_condition``. Any view that still uses ``rest_condition`` will cause the middleware to throw an error.


[7.0.1] - 2021-08-10
--------------------

Fixed
~~~~~

* Removed dropped ``require_exp`` and ``require_iat`` options from jwt.decode and instead used ``require`` option with both ``exp`` and ``iat``. For more info visit this: https://pyjwt.readthedocs.io/en/stable/changelog.html#dropped-deprecated-require-options-in-jwt-decode
* This fixes an error in previous release which had a multiple breaking changes


[7.0.0] - 2021-08-03
--------------------

Changed
~~~~~~~

* **BREAKING CHANGE:** ``generate_jwt_token``: Now returns string (instead of bytes), and no longer requires decoding. This was to keep consistent with change to ``jwt.encode`` in `pyjwt` upgrade (see below).
* **BREAKING CHANGE:** Upgraded dependency ``pyjwt[crypto]`` to 2.1.0, which introduces its own breaking changes that may affect consumers of this library. Pay careful attention to the 2.0.0 breaking changes documented in https://pyjwt.readthedocs.io/en/stable/changelog.html#v2-0-0.

[6.6.0] - 2021-07-13
--------------------

Added
~~~~~

* Added support for django3.1 and 3.2

[6.5.0] - 2021-02-12
--------------------

Added
~~~~~

* Added a new custom attribute `jwt_auth_failed` to both monitor failures, and to help prepare for future refactors.


[6.4.0] - 2021-01-19
--------------------

Added
~~~~~

* Added a new custom attribute `request_is_staff_or_superuser`

[6.3.0] - 2021-01-12
--------------------

Removed
~~~~~~~

* Drop support for Python 3.5

[6.2.0] - 2020-08-24
--------------------

Updated
~~~~~~~

* Renamed "custom metric" to "custom attribute" throughout the repo. This was based on a `decision (ADR) captured in edx-django-utils`_.

  * Deprecated RequestMetricsMiddleware due to rename.  Use RequestCustomAttributesMiddleware instead.

.. _`decision (ADR) captured in edx-django-utils`: https://github.com/openedx/edx-django-utils/blob/master/edx_django_utils/monitoring/docs/decisions/0002-custom-monitoring-language.rst

[6.1.2] - 2020-07-19
--------------------

Fixed
~~~~~~~

* `_get_user_from_jwt` no longer throws an `UnsupportedMediaType` error for failing to parse "new user" requests.



[6.1.1] - 2020-07-19
--------------------

Fixed
~~~~~~~

* Latest `drf-jwt` is throwing error in case of any other Authorization Header. Fixing that issue in `JwtAuthentication` class.



[6.1.0] - 2020-06-26
--------------------

Changed
~~~~~~~

* Update `drf-jwt` to pull in new allow-list(they called it blacklist) feature.

Added
~~~~~

Fixed
~~~~~



[6.0.0] - 2020-05-05
--------------------

Changed
~~~~~~~

* **BREAKING CHANGE**: Renamed 'request_auth_type' to 'request_auth_type_guess'. This makes it more clear that this metric could report the wrong value in certain cases. This could break dashboards or alerts that relied on this metric.
* **BREAKING CHANGE**: Renamed value `session-or-unknown` to `session-or-other`. This name makes it more clear that it is the method of authentication that is in question, not whether or not the user is authenticated. This could break dashboards or alerts that relied on this metric.

Added
~~~~~

* Added 'jwt-cookie' as new value for 'request_auth_type_guess'.
* Added new 'request_authenticated_user_found_in_middleware' metric. Helps identify for what middleware step the request user was set, if it was set. Example values: 'process_request', 'process_view', 'process_response', or 'process_exception'.

Fixed
~~~~~

* Fixed/Added setting of authentication metrics for exceptions as well.
* Fixed 'request_auth_type_guess' to be more accurate when recording values of 'unauthenticated' and 'no-user'.
