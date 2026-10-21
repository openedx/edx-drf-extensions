""" Paginatator methods for edX API implementations."""

from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import InvalidPage, Paginator
from django.http import Http404
from rest_framework import pagination
from rest_framework.response import Response


class DefaultPagination(pagination.PageNumberPagination):
    """
    Default paginator for APIs in edx-platform.

    This is configured in settings to be automatically used
    by any subclass of Django Rest Framework's generic API views.
    """
    page_size_query_param = "page_size"
    page_size = 10
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        Annotate the response with pagination information.
        """
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'num_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'start': (self.page.number - 1) * self.get_page_size(self.request),
            'results': data
        })


def paginate_manually(request, items, serialize, pagination_class=DefaultPagination, view=None):
    """
    Paginate ``items`` by hand and return the paginated ``Response``.

    ADR 0032 requires the standard pagination envelope even on endpoints whose
    data is not a queryset flowing through DRF's generic ``list`` machinery —
    a plain ``ViewSet`` action, or results assembled from an API call. This is
    the shared spelling of the paginate-serialize-respond sequence those
    endpoints otherwise hand-write.

    Arguments:
        request: the DRF request (supplies the ``page``/``page_size`` params).
        items: a sequence or queryset (anything Django's ``Paginator`` can
            ``len()`` and slice; a bare generator will not do).
        serialize: callable receiving the page's items (a list) and returning
            their serialized representation.
        pagination_class: the DRF pagination class to use; defaults to
            :class:`DefaultPagination`.
        view: the view handling the request, when there is one (passed through
            to ``paginate_queryset``).

    Returns:
        rest_framework.response.Response: the paginated response.
    """
    paginator = pagination_class()
    page = paginator.paginate_queryset(items, request, view=view)
    return paginator.get_paginated_response(serialize(page))


class IterablePaginationMixin:
    """
    ADR 0032 pagination for views outside DRF's generic ``list`` machinery.

    Mix into a ``ViewSet`` or ``APIView`` whose handler builds its own item
    sequence (rather than exposing a queryset through ``GenericAPIView``), and
    return ``self.paginate_iterable(request, items)`` from the handler::

        class EnrollmentViewSet(IterablePaginationMixin, viewsets.ViewSet):
            serializer_class = CourseEnrollmentSerializer

            def list(self, request):
                enrollments = ops.list_enrollments_for_user(...)
                return self.paginate_iterable(request, enrollments)

    The view's ``pagination_class`` controls the envelope; it defaults to
    :class:`DefaultPagination` (the ADR 0032 seven-field envelope).
    """

    #: The DRF pagination class applied by :meth:`paginate_iterable`.
    pagination_class = DefaultPagination

    def paginate_iterable(self, request, items, serialize=None):
        """
        Paginate ``items`` (a sequence or queryset) and return the paginated
        ``Response``.

        ``serialize`` defaults to ``self.get_serializer(page, many=True).data``,
        matching DRF's generic views; pass a callable to serialize differently.
        """
        if self.pagination_class is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} uses IterablePaginationMixin but its 'pagination_class' is None."
            )
        if serialize is None:
            if not callable(getattr(self, "get_serializer", None)):
                raise ImproperlyConfigured(
                    f"{type(self).__name__}.paginate_iterable needs either a 'serialize' argument "
                    f"or a 'get_serializer' method on the view."
                )

            def serialize(page):
                return self.get_serializer(page, many=True).data

        return paginate_manually(
            request, items, serialize, pagination_class=self.pagination_class, view=self,
        )


class NamespacedPageNumberPagination(pagination.PageNumberPagination):
    """
    Pagination scheme that returns results with pagination metadata
    embedded in a "pagination" attribute.  Can be used with data
    that comes as a list of items, or as a dict with a "results"
    attribute that contains a list of items.
    """

    page_size_query_param = "page_size"

    def get_result_count(self):
        """
        Returns total number of results
        """
        return self.page.paginator.count

    def get_num_pages(self):
        """
        Returns total number of pages the results are divided into
        """
        return self.page.paginator.num_pages

    def get_paginated_response(self, data):
        """
        Annotate the response with pagination information
        """
        metadata = {
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.get_result_count(),
            'num_pages': self.get_num_pages(),
        }
        if isinstance(data, dict):
            if 'results' not in data:
                raise TypeError('Malformed result dict')
            data['pagination'] = metadata
        else:
            data = {
                'results': data,
                'pagination': metadata,
            }
        return Response(data)


def paginate_search_results(object_class, search_results, page_size, page):
    """
    Takes search results and returns a Page object populated
    with db objects for that page.

    :param object_class: Model class to use when querying the db for objects.
    :param search_results: search results.
    :param page_size: Number of results per page.
    :param page: Page number.
    :return: Paginator object with model objects
    """
    paginator = Paginator(search_results['results'], page_size)

    # This code is taken from within the GenericAPIView#paginate_queryset method.
    # It is common code, but
    try:
        page_number = paginator.validate_number(page)
    except InvalidPage as page_error:
        if page == 'last':
            page_number = paginator.num_pages
        else:
            raise Http404("Page is not 'last', nor can it be converted to an int.") from page_error

    try:
        paged_results = paginator.page(page_number)
    except InvalidPage as exception:
        raise Http404(
            "Invalid page {page_number}: {message}".format(
                page_number=page_number,
                message=str(exception)
            )
        ) from exception

    search_queryset_pks = [item['data']['pk'] for item in paged_results.object_list]
    queryset = object_class.objects.filter(pk__in=search_queryset_pks)

    def ordered_objects(primary_key):
        """ Returns database object matching the search result object"""
        for obj in queryset:
            if obj.pk == primary_key:
                return obj
        return None

    # map over the search results and get a list of database objects in the same order
    object_results = list(map(ordered_objects, search_queryset_pks))
    paged_results.object_list = object_results

    return paged_results
