from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Paginación por defecto; el front puede pedir ?page_size= hasta 200."""

    page_size_query_param = "page_size"
    max_page_size = 200
