Part of `edX code`__.

__ https://code.edx.org/

edX Django REST Framework Extensions  |CI|_ |Codecov|_
==========================================================
.. |CI| image:: https://github.com/edx/edx-drf-extensions/workflows/Python%20CI/badge.svg?branch=master
.. _CI: https://github.com/edx/edx-drf-extensions/actions?query=workflow%3A%22Python+CI%22

.. |Codecov| image:: https://codecov.io/github/edx/edx-drf-extensions/coverage.svg?branch=master
.. _Codecov: https://codecov.io/github/edx/edx-drf-extensions?branch=master

This library includes various cross-cutting concerns related to APIs. API functionality added to this library must be required for multiple Open edX applications or multiple repositories.

Some of these concerns include extensions of `Django REST Framework <https://www.django-rest-framework.org/>`_ (DRF), which is how the repository initially got its name.

Publishing a Release
--------------------

After a PR merges, a new version of the package will automatically be released by Travis when the commit is tagged. Use::

    git tag -a X.Y.Z -m "Releasing version X.Y.Z"
    git push origin X.Y.Z

Do **not** create a Github Release, or ensure its message points to the CHANGELOG.rst and ADR 0001-use-changelog.rst.

JWT Authentication and REST API Endpoints
-----------------------------------------

JWT Authentication is the preferred method of authentication for Open edX API endpoints. See `JWT Authentication README`_ for more details.

.. _JWT Authentication README: ./auth/jwt/README.rst

CSRF API
--------

One feature of this library is a ``csrf`` app containing an API endpoint for retrieving CSRF tokens from the Django service in which it is installed. This is useful for frontend apps attempting to make POST, PUT, and DELETE requests to a Django service with Django's CSRF middleware enabled.

To make use of this API endpoint:

#. Install edx-drf-extensions in your Django project.
#. Add ``csrf.apps.CsrfAppConfig`` to ``INSTALLED_APPS``.
#. Add ``'edx_rest_framework_extensions.auth.jwt.middleware.JwtAuthCookieMiddleware'`` to ``MIDDLEWARE``.
#. Add ``csrf.urls`` to urls.py.

License
-------

The code in this repository is licensed under Apache 2.0 unless otherwise noted.

Please see ``LICENSE.txt`` for details.

How To Contribute
-----------------

Contributions are very welcome.

Please read `How To Contribute <https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst>`_ for details.

Even though they were written with ``edx-platform`` in mind, the guidelines should be followed for Open edX code in general.

Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@edx.org.
