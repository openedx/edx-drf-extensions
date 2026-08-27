"""
Response-shaping helpers for Open edX REST APIs (ADR 0036).

edx-platform's ``docs/decisions/0036`` lets clients opt out of heavy response
payloads in two standard ways, both implemented here:

* ``?fields=a,b,c`` — keep only the named top-level keys of a serialized
  object (:func:`project`).
* ``?view=minimal`` — replace each serialized object with a view-defined
  minimal representation (:class:`MinimalViewMixin`).

Both are *shaping* helpers: they operate on already-serialized data (dicts and
lists of dicts) immediately before the response is returned, so the default
response shape — and therefore backwards compatibility — is untouched unless
the client asks.
"""
from django.core.exceptions import ImproperlyConfigured


def project(data, fields):
    """
    Return a new dict containing only the top-level keys of ``data`` named in
    ``fields``.

    Arguments:
        data: a ``dict`` (typically ``serializer.data``). Anything else is
            returned untouched.
        fields: an iterable of field names, or a comma-separated string (for
            example the raw value of a ``?fields=`` query parameter). Falsy →
            no filtering (``data`` is returned unchanged).

    Returns:
        A new ``dict`` containing only the requested top-level keys, or the
        original ``data`` when filtering is not applicable.

    Note:
        Only top-level keys are honoured. Dotted paths (``fields=children.x``)
        are stripped to their first segment (``children``) — full dotted-path
        traversal is intentionally not implemented, per the ADR 0036 guidance
        to reject silent over-fetching via that syntax.
    """
    if not fields or not isinstance(data, dict):
        return data
    names = fields.split(",") if isinstance(fields, str) else fields
    wanted = {str(name).strip().split(".", 1)[0] for name in names if str(name).strip()}
    if not wanted:
        return data
    return {key: value for key, value in data.items() if key in wanted}


class MinimalViewMixin:
    """
    ADR 0036 ``?view=minimal`` support for DRF views.

    Mix into a view and either set :attr:`minimal_fields` (the projection
    applied to each serialized object) or override
    :meth:`to_minimal_representation` for shapes a plain projection cannot
    express (for example collapsing an embedded sub-object to its id).

    The view applies the shaping explicitly, immediately before building the
    response::

        class EnrollmentViewSet(MinimalViewMixin, viewsets.ViewSet):
            minimal_fields = ("course_id", "mode", "is_active")

            def list(self, request):
                data = self.get_serializer(items, many=True).data
                return Response(self.shape_minimal(data, request))

    The default response shape is returned unchanged unless the client sends
    ``?view=minimal`` (both the parameter name and value are overridable via
    :attr:`minimal_view_query_param` and :attr:`minimal_view_value`).
    """

    #: Query parameter that selects the response preset.
    minimal_view_query_param = "view"
    #: Parameter value that selects the minimal preset.
    minimal_view_value = "minimal"
    #: Top-level fields kept by the default :meth:`to_minimal_representation`.
    #: Views that need a non-projection shape override the method instead.
    minimal_fields = None

    def is_minimal_view_requested(self, request=None):
        """Return True when the caller asked for the minimal preset."""
        request = request if request is not None else self.request
        params = getattr(request, "query_params", request.GET)
        return params.get(self.minimal_view_query_param) == self.minimal_view_value

    def to_minimal_representation(self, item):
        """
        Return the minimal representation of one serialized object.

        Defaults to projecting ``item`` onto :attr:`minimal_fields`; raises
        ``ImproperlyConfigured`` when the view configured neither the fields
        nor an override, so a requested minimal view never silently returns
        the full payload.
        """
        if self.minimal_fields is None:
            raise ImproperlyConfigured(
                f"{type(self).__name__} uses MinimalViewMixin but defines neither 'minimal_fields' "
                f"nor a 'to_minimal_representation' override."
            )
        return project(item, self.minimal_fields)

    def shape_minimal(self, data, request=None):
        """
        Apply the minimal representation to ``data`` when the client asked for it.

        ``data`` may be one serialized object (a dict) or a list of them; the
        original is returned untouched when the minimal preset was not requested.
        """
        if not self.is_minimal_view_requested(request):
            return data
        if isinstance(data, list):
            return [self.to_minimal_representation(item) for item in data]
        return self.to_minimal_representation(data)
