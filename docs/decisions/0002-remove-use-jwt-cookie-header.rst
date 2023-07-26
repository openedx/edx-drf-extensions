2. Remove HTTP_USE_JWT_COOKIE Header
====================================

Status
------

Accepted

Context
-------

This ADR explains `why the request header HTTP_USE_JWT_COOKIE`_ was added.

Use of this header has several problems:

* The purpose and need for the ``HTTP_USE_JWT_COOKIE`` header is confusing. It has led to developer confusion when trying to test API calls using JWT cookies, but having the auth fail because they didn't realize this special header was also required.
* In some cases, the JWT cookies are sent to services, but go unused because of this header. Additional oauth redirects then become required in circumstances where they otherwise wouldn't be needed.
* Some features have been added, like `JwtRedirectToLoginIfUnauthenticatedMiddleware`_, that can be greatly simplified or possibly removed altogether if the ``HTTP_USE_JWT_COOKIE`` header were retired.


Decision
--------

Replace the `HTTP_USE_JWT_COOKIE` header with forgiving authentication when using JWT cookies. By "forgiving", we mean that JWT authentication would no longer raise exceptions for failed authentication when using JWT cookies, but instead would simply return None.

By returning None from JwtAuthentication, rather than raising an authentication failure, we enable services to move on to other classes, like SessionAuthentication, rather than aborting the authentication process. Failure messages could still be surfaced using `set_custom_metric` for debugging purposes.

Rather than checking for the `HTTP_USE_JWT_COOKIE`, the `JwtAuthCookieMiddleware`_ would always reconstitute the JWT cookie if the parts were available.

The proposal includes protecting all changes with a temporary rollout feature toggle ``ENABLE_FORGIVING_JWT_COOKIES``. This can be used to ensure no harm is done for each service before cleaning up the old header.

.. _JwtAuthCookieMiddleware: https://github.com/edx/edx-drf-extensions/blob/270cf521a72b506d7df595c4c479c7ca232b4bec/edx_rest_framework_extensions/auth/jwt/middleware.py#L164

Consequences
------------

* Makes authentication simpler, more clear, and more predictable.

  * For example, local testing of endpoints outside of MFEs will use JWT cookies rather than failing, which has been misleading for engineers.

* Greatly simplifies features like `JwtRedirectToLoginIfUnauthenticatedMiddleware`_.
* Service authentication can take advantage of JWT cookies more often.
* Services can more consistently take advantage of the JWT payload of the JWT cookie.
* Additional clean-up when retiring the ``HTTP_USE_JWT_COOKIE`` header will be needed:

  * ``HTTP_USE_JWT_COOKIE`` should be removed from frontend-platform auth code when ready.
  * ADR that explains `why the request header HTTP_USE_JWT_COOKIE`_ was created should be updated to point to this ADR.

.. _why the request header HTTP_USE_JWT_COOKIE: https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/oauth_dispatch/docs/decisions/0009-jwt-in-session-cookie.rst#login---cookie---api
.. _JwtRedirectToLoginIfUnauthenticatedMiddleware: https://github.com/edx/edx-drf-extensions/blob/270cf521a72b506d7df595c4c479c7ca232b4bec/edx_rest_framework_extensions/auth/jwt/middleware.py#L87
