from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

hex_validator = RegexValidator(
    r'^#[0-9A-Fa-f]{6}$', 'Введите корректный HEX-код цвета.'
)


class Ingredient(models.Model):
    """
    Модель ингредиента
    """
    name = models.CharField(max_length=200)
    measurement_unit = models.CharField(max_length=200)

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class Tag(models.Model):
    """
    Модель тега
    """
    name = models.CharField(max_length=200, unique=True)
    color = models.CharField(
        max_length=7, unique=True, validators=[hex_validator]
    )
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """
    Модель рецепта
    """
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )

    name = models.CharField(max_length=200, verbose_name='Название')
    image = models.ImageField(upload_to='recipes/', verbose_name='Изображение')
    text = models.TextField(verbose_name='Описание')

    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )

    tags = models.ManyToManyField(
        Tag, related_name='recipes', verbose_name='Теги'
    )

    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления'
    )
    pub_date = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата публикации'
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """
    Связующая модель Рецепт-Ингредиент с количеством
    """
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        try:
            return (
                f"{self.ingredient.name} "
                f"({self.amount} {self.ingredient.measurement_unit}) "
                f"в \"{self.recipe.name}\""
            )
        except (Ingredient.DoesNotExist, Recipe.DoesNotExist, AttributeError):
            return (
                f"Ингредиент ID {self.ingredient_id} "
                f"в Рецепте ID {self.recipe_id}"
            )


class Favorite(models.Model):
    """
    Модель для добавления рецептов в избранное пользователя
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='unique_favorite'
            ),
        ]

    def __str__(self):
        try:
            user_repr = self.user.username
            recipe_repr = self.recipe.name
            return f"'{recipe_repr}' в избранном у {user_repr}"
        except (
            Recipe.DoesNotExist,
            settings.AUTH_USER_MODEL.DoesNotExist,
            AttributeError
        ):
            return (
                f"Избранное: Пользователь ID {self.user_id}, "
                f"Рецепт ID {self.recipe_id}"
            )


class ShoppingCart(models.Model):
    """
    Модель для добавления рецептов в список покупок пользователя
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_carts',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='unique_shopping_cart'
            ),
        ]

    def __str__(self):
        try:
            user_repr = self.user.username
            recipe_repr = self.recipe.name
            return f"'{recipe_repr}' в списке покупок у {user_repr}"
        except (
            Recipe.DoesNotExist,
            settings.AUTH_USER_MODEL.DoesNotExist,
            AttributeError
        ):
            return (
                f"Покупки: Пользователь ID {self.user_id}, "
                f"Рецепт ID {self.recipe_id}"
            )
