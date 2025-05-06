from django_filters.rest_framework import FilterSet, CharFilter, filters
from recipes.models import Recipe, Tag, Ingredient


class RecipeFilter(FilterSet):
    """
    Фильтруем рецепты по тегам, автору, избранному и корзине
    """

    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    author = filters.NumberFilter(field_name='author__id')

    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ['author', 'tags']

    def filter_is_favorited(self, queryset, name, value):
        """
        Отдаем рецепты из избранного текущего пользователя,
        если value=True
        """
        user = self.request.user
        if user.is_authenticated and value:
            return queryset.filter(favorited_by__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """
        Отдаем рецепты из корзины текущего пользователя, если value=True
        """
        user = self.request.user
        if user.is_authenticated and value:
            return queryset.filter(in_shopping_carts__user=user)
        return queryset


class IngredientFilter(FilterSet):
    """
    Фильтруем ингредиенты по началу названия
    """

    name = CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']
