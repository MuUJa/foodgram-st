from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Кастомный пагинатор, использующий query-параметр 'limit'
    """
    page_size_query_param = 'limit'
    max_page_size = 100
    page_size = 6
