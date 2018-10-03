Part of `edX code`__.

__ http://code.edx.org/

edX Django REST Framework Extensions  |Travis|_ |Codecov|_
==========================================================
.. |Travis| image:: https://travis-ci.org/edx/edx-drf-extensions.svg?branch=master
.. _Travis: https://travis-ci.org/edx/edx-drf-extensions?branch=master

.. |Codecov| image:: http://codecov.io/github/edx/edx-drf-extensions/coverage.svg?branch=master
.. _Codecov: http://codecov.io/github/edx/edx-drf-extensions?branch=master

This library includes extensions of `Django REST Framework <http://www.django-rest-framework.org/>`_
useful for edX applications.

CSRF API
--------

This library also includes a ``csrf`` app containing an API endpoint for retrieving CSRF tokens from
the Django service in which it is installed. This is useful for frontend apps attempting to make POST,
PUT, and DELETE requests to a Django service with Django's CSRF middleware enabled.

To make use of this API endpoint:

#. Install edx-drf-extensions in your Django project.
#. Add ``csrf.apps.CsrfAppConfig`` to ``INSTALLED_APPS``.

License
-------

The code in this repository is licensed under AGPL unless otherwise noted.

Please see ``LICENSE.txt`` for details.

How To Contribute
-----------------

Contributions are very welcome.

Please read `How To Contribute <https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst>`_ for details.

Even though they were written with ``edx-platform`` in mind, the guidelines
should be followed for Open edX code in general.

Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@edx.org.

Mailing List and IRC Channel
----------------------------

You can discuss this code in the `edx-code Google Group`__ or in the ``#edx-code`` IRC channel on Freenode.

__ https://groups.google.com/forum/#!forum/edx-code
