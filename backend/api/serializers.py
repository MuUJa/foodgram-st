from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserCreateSerializer
from users.models import Subscription
from recipes.models import (
    Ingredient, Tag, Recipe, RecipeIngredient, Favorite, ShoppingCart
)
User = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения информации о пользователе
    """
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(
        read_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if (not request or request.user.is_anonymous
                or not isinstance(obj, User)):
            return False
        user = request.user
        if user == obj:
            return False
        return Subscription.objects.filter(user=user, author=obj).exists()


class CustomUserCreateSerializer(UserCreateSerializer):
    """
    Сериализатор для регистрации юзера
    """
    class Meta(UserCreateSerializer.Meta):
        pass

    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    def validate_username(self, value):
        if value.lower() == 'me':
            raise serializers.ValidationError(
                "Имя пользователя 'me' запрещено.")
        return value


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для тега
    """
    class Meta:
        model = Tag
        fields = '__all__'

    def to_internal_value(self, data):
        try:
            return Tag.objects.get(id=data)
        except Tag.DoesNotExist:
            raise ValidationError(f"Тег с id={data} не найден.")


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ингредиента
    """
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')

    def to_internal_value(self, data):
        try:
            return Ingredient.objects.get(id=data)
        except Ingredient.DoesNotExist:
            raise ValidationError(f"Ингредиент с id={data} не найден.")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения ингредиентов внутри рецепта с их количеством
    """
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all(),
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.IntegerField(
        min_value=1,
        error_messages={'min_value': 'Количество должно быть не меньше 1.'})

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения рецепта
    """
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipe_ingredients', read_only=True)
    image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'text', 'cooking_time',
            'image',
            'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart'
        )

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return ""

    def get_is_favorited(self, obj):
        print("Context in get_is_favorited:", self.context)
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj
        ).exists()


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания/обновления Рецепта
    """
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), required=False)
    ingredients = RecipeIngredientSerializer(many=True)
    image = Base64ImageField(required=True, allow_null=False)
    cooking_time = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': 'Время приготовления должно быть не меньше 1.'
        }
    )

    class Meta:
        model = Recipe
        fields = ('name', 'text', 'cooking_time',
                  'image', 'tags', 'ingredients')
        read_only_fields = ('author',)

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        image_data = data.get('image')

        if not image_data:
            raise serializers.ValidationError(
                {'image': 'Это поле не может быть пустым.'})
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Нужно добавить хотя бы один ингредиент.'})

        ingredient_ids = []
        for item in ingredients:
            ingredient = item['ingredient']
            if ingredient.id in ingredient_ids:
                raise serializers.ValidationError(
                    {'ingredients':
                        f'Ингредиент "{ingredient.name}" добавлен дважды.'})
            ingredient_ids.append(ingredient.id)

        if tags and len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться.'})

        cooking_time = data.get('cooking_time')
        if cooking_time <= 0:
            raise serializers.ValidationError(
                {'cooking_time':
                    'Время приготовления должно быть больше нуля.'})

        return data

    @transaction.atomic
    def create(self, validated_data):
        tags_data = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients')
        user = self.context['request'].user
        validated_data.pop('author', None)
        recipe = Recipe.objects.create(author=user, **validated_data)
        if tags_data is not None:
            recipe.tags.set(tags_data)
        recipe_ingredients_to_create = []
        for ingredient_item in ingredients_data:
            recipe_ingredients_to_create.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ingredient_item['ingredient'],
                    amount=ingredient_item['amount']
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredients_to_create)
        print(recipe_ingredients_to_create)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)

        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)
        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            recipe_ingredients_to_create = []
            for ingredient_item in ingredients_data:
                recipe_ingredients_to_create.append(
                    RecipeIngredient(
                        recipe=instance,
                        ingredient=ingredient_item['ingredient'],
                        amount=ingredient_item['amount']
                    )
                )
            RecipeIngredient.objects.bulk_create(recipe_ingredients_to_create)
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления рецепта в избранное
    """
    id = serializers.IntegerField(source='recipe.id', read_only=True)
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = Base64ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True)

    class Meta:
        model = Favorite
        fields = ('id', 'name', 'image', 'cooking_time')


class ShoppingCartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления рецепта в список покупок
    """
    id = serializers.IntegerField(source='recipe.id', read_only=True)
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = Base64ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Короткий сериализатор рецепта (для отображения в подписках).
    """
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения подписок
    """
    email = serializers.EmailField(source='author.email', read_only=True)
    id = serializers.IntegerField(source='author.id', read_only=True)
    username = serializers.CharField(source='author.username', read_only=True)
    first_name = serializers.CharField(
        source='author.first_name', read_only=True)
    last_name = serializers.CharField(
        source='author.last_name', read_only=True)
    avatar = serializers.ImageField(
        source='author.avatar', read_only=True,
        required=False, allow_null=True)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='author.recipes.count', read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name',
            'avatar',
            'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=request.user, author=obj.author
        ).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        qs = Recipe.objects.filter(author=obj.author).order_by('id')
        if recipes_limit:
            try:
                limit = int(recipes_limit)
                qs = qs[:limit]
            except ValueError:
                pass
        return RecipeShortSerializer(qs, many=True, context=self.context).data
