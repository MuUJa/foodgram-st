from django.contrib import admin
from .models import (
    Ingredient, Tag, Recipe, RecipeIngredient, Favorite, ShoppingCart
)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """
    Настройка админки для Ингредиентов
    """
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Настройка админки для Тегов
    """
    list_display = ('id', 'name', 'slug', 'color')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class RecipeIngredientInline(admin.TabularInline):
    """
    Инлайн для управления ингредиентами на странице рецепта
    """
    model = RecipeIngredient
    fields = ('ingredient', 'amount')
    autocomplete_fields = ['ingredient']
    extra = 1
    min_num = 1


class FavoritedByInline(admin.TabularInline):
    """
    Показывает, кто добавил рецепт в избранное
    """
    model = Favorite
    fields = ('user',)
    readonly_fields = ('user',)
    can_delete = False
    extra = 0
    verbose_name = "В избранном у пользователя"
    verbose_name_plural = "В избранном у пользователей"


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """
    Настройка админки для Рецептов
    """
    list_display = ('id', 'name', 'author', 'get_favorites_count', 'pub_date')
    search_fields = ('name', 'author__username')
    list_filter = ('author', 'name', 'tags')
    inlines = (RecipeIngredientInline, FavoritedByInline,)
    filter_horizontal = ('tags',)  # Или filter_vertical = ('tags',)
    autocomplete_fields = ['author']
    readonly_fields = ('pub_date', 'get_favorites_count',)

    fieldsets = (
        (None, {
            'fields': ('name', 'author', 'text', 'image')
        }),
        ('Ингредиенты и Теги', {
            'fields': ('tags', 'cooking_time')
        }),
        ('Дополнительная информация', {
            'fields': ('pub_date', 'get_favorites_count'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='В избранном (кол-во)')
    def get_favorites_count(self, obj):
        """
        Кастомный метод для подсчета,
        сколько раз рецепт был добавлен в избранное
        """
        return obj.favorited_by.count()


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """
    Админка для Избранного
    """
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    autocomplete_fields = ['user', 'recipe']


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """
    Админка для списка покупок
    """
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    autocomplete_fields = ['user', 'recipe']
