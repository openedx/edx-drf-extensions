JWT Authentication
==================

This directory contains extensions to enable JWT Authentication for your endpoints.

JWT Authentication Class
------------------------

JWT Authentication is mainly enabled by the JwtAuthentication_ class, which is a `Django Rest Framework (DRF)`_ authentication class. The REST endpoint declares which type(s) of authentication it supports or defaults to the *DEFAULT_AUTHENTICATION_CLASSES* value in DRF's *REST_FRAMEWORK* Django setting.

Here is an example of using Django Settings to set JwtAuthentication_ and ``SessionAuthentication`` as default for your Django application::

    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'edx_rest_framework_extensions.auth.jwt.authentication.JwtAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ),
    }

Here is an example of a DRF API endpoint implemented using JwtAuthentication_ explicitly::

    from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
    from rest_framework.views import APIView

    class MyAPIView(APIView):
        authentication_classes = (JwtAuthentication, )
        ...

Additional notes about this class:

  * JwtAuthentication_ extends the JSONWebTokenAuthentication_ class implemented in the django-rest-framework-jwt_ library.

  * JwtAuthentication_ is used to authenticate an API request only if it is listed in the endpoint's authentication_classes_ and the request's Authorization header specifies "JWT" instead of "Bearer".

  * **Note:** The Credentials service has its own implementation of JwtAuthentication and should be converted to use this common implementation.

.. _Django Rest Framework (DRF): https://github.com/encode/django-rest-framework
.. _JwtAuthentication: ./authentication.py
.. _authentication_classes: http://www.django-rest-framework.org/api-guide/authentication/#setting-the-authentication-scheme
.. _django-rest-framework-jwt: https://github.com/GetBlimp/django-rest-framework-jwt
.. _JSONWebTokenAuthentication: https://github.com/GetBlimp/django-rest-framework-jwt/blob/0a0bd402ec21fd6b9a5f715d114411836fbb2923/rest_framework_jwt/authentication.py#L71
