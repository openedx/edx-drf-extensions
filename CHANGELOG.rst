Change Log
==========

..
   This file loosely adheres to the structure of https://keepachangelog.com/,
   but in reStructuredText instead of Markdown.

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
----------

*

[7.0.0] - 2020-07-15
--------------------

Changed
~~~~~~~

* Refactored a large permissions.py module into multiple modules within a new permissions folder in order to clarify the different sets of permissions for their different purposes. In particular, separated Permissions related to enforcing OAuth Scopes and Restricted Applications from other Basic permissions in order to avoid confusion on which permissions to use for basic functionality.

* To continue to support clients who imported permissions from the old permissions.py module, those permissions are exported from the permissions/__init__.py module for backward compatibility (with the following caveat). *(Note: This works since Python's import statement is the same whether the code is imported from a module named XXX or from an __init__.py module in a directory named XXX.)*

* **BREAKING CHANGE** All permissions moved into the oauth_scopes.py module are *not* exported from the permissions/__init__.py module since these permissions are not expected to be used widely and far in the future. The only clients of these permissions are in edx-platform, which will be updated once these changes are released.

Added
~~~~~

* Created a new permissions folder for containing and organizing Permission classes.
* Created new permissions-related modules: basic.py, oauth_scopes.py, and redirect.py.


[6.1.0] - 2020-06-26
--------------------

Changed
~~~~~~~

* Update `drf-jwt` to pull in new allow-list(they called it blacklist) feature.


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
