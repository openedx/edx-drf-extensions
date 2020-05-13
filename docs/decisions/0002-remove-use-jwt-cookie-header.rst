2. Remove USE_JWT_COOKIE Header
===============================

Status
------

Accepted

Context
-------

This ADR explains `why the request header USE_JWT_COOKIE`_ was added.

Use of this header has several problems:

* In some cases, the JWT Cookie could be available to services, but it goes unused because of this header.
* Some features have been added, like `JwtRedirectToLoginIfUnauthenticatedMiddleware`_, that can be greatly simplified or possibly removed altogether if the `USE_JWT_COOKIE` header were retired.


Decision
--------

Replace the `USE_JWT_COOKIE` with forgiving authentication when using JWT cookies. By "forgiving", we mean that JWT authentication would no longer raise exceptions for failed authentication when using JWT cookies, but instead would simply return None.

By returning None from JwtAuthentication, rather than raising an authentication failure, we enable services to move on to other classes, like SessionAuthentication, rather than aborting the authentication process. Failure messages could still be surfaced using `set_custom_metric` for debugging purposes.

Rather than checking for `USE_JWT_COOKIE`, the `JwtAuthCookieMiddleware`_ would *nearly* always reconstitute the JWT cookie if the parts were available. It would not reconstitute the JWT cookie if a JWT was also in the Authorization header, because the authorization header takes precedence.

Although this would be a breaking API change for JwtAuthentication (where enabled), the plan would be for the backward incompatibility to be encapsulated and fixed in edx-drf-extensions.

The proposal includes protecting all changes with a temporary rollout feature toggle `ENABLE_FORGIVING_JWT_COOKIES`. This can be used to ensure no harm is done for each service before cleaning up the old header.

.. _JwtAuthCookieMiddleware: https://github.com/edx/edx-drf-extensions/blob/270cf521a72b506d7df595c4c479c7ca232b4bec/edx_rest_framework_extensions/auth/jwt/middleware.py#L164

Consequences
------------

* Makes authentication simpler, more clear, and more predictable.

  * For example, local testing of endpoints outside of MFEs will use JWT cookies rather than failing, which has been misleading for engineers.

* Greatly simplifies features like `JwtRedirectToLoginIfUnauthenticatedMiddleware`_.
* Service authentication can take advantage of JWT cookies more often.
* Services can more consistently take advantage of the JWT payload of the JWT cookie.
* Additional clean-up when retiring `USE_JWT_COOKIE` will be needed:

  * `USE_JWT_COOKIE` should be removed from frontend-auth.
  * ADR that explains `why the request header USE_JWT_COOKIE`_ was created should be updated to point to this ADR.

.. _why the request header USE_JWT_COOKIE: https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/oauth_dispatch/docs/decisions/0009-jwt-in-session-cookie.rst#login---cookie---api
.. _JwtRedirectToLoginIfUnauthenticatedMiddleware: https://github.com/edx/edx-drf-extensions/blob/270cf521a72b506d7df595c4c479c7ca232b4bec/edx_rest_framework_extensions/auth/jwt/middleware.py#L87
