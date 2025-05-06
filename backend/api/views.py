from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_extra_fields.fields import Base64ImageField
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import (
    generics, parsers, permissions, serializers, status, viewsets
)
from rest_framework.decorators import action
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response

from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient, ShoppingCart, Tag
)
from users.models import CustomUser, Subscription
from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (
    CustomUserSerializer, IngredientSerializer, RecipeCreateUpdateSerializer,
    RecipeSerializer, RecipeShortSerializer, SubscriptionSerializer,
    TagSerializer
)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API эндпоинт для просмотра ингредиентов
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, ]
    pagination_class = None
    filter_backends = [DjangoFilterBackend, ]
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API эндпоинт для просмотра тегов
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny, ]
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """
    API эндпоинт для просмотра рецептов
    """
    queryset = Recipe.objects.prefetch_related(
        'tags', 'author', 'recipe_ingredients__ingredient'
    ).all().order_by('-pub_date')
    permission_classes = [IsAuthorOrAdminOrReadOnly, ]
    filter_backends = [DjangoFilterBackend, ]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        elif self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        recipe_instance = self.perform_create(write_serializer)

        read_serializer = RecipeSerializer(
            recipe_instance,
            context=self.get_serializer_context()
        )
        headers = self.get_success_headers(read_serializer.data)
        return Response(
            read_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def perform_create(self, serializer):
        return serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        write_serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        write_serializer.is_valid(raise_exception=True)
        recipe_instance = self.perform_update(write_serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        read_serializer = RecipeSerializer(
            recipe_instance, context=self.get_serializer_context()
        )
        return Response(read_serializer.data)

    def perform_update(self, serializer):
        return serializer.save()

    def _add_or_remove_relation(
            self, request, pk, related_model, serializer_class
    ):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        instance_exists = related_model.objects.filter(
            user=user, recipe=recipe
        ).exists()

        if request.method == 'POST':
            if instance_exists:
                return Response(
                    {'errors': 'Рецепт уже добавлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            related_model.objects.create(user=user, recipe=recipe)
            serializer = serializer_class(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            deleted, _ = related_model.objects.filter(
                user=user, recipe=recipe
            ).delete()
            if deleted == 0:
                return Response(
                    {'errors': 'Рецепт не найден в списке'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post', 'delete'], url_path='favorite',
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        return self._add_or_remove_relation(
            request, pk, Favorite, RecipeShortSerializer
        )

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart',
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self._add_or_remove_relation(
            request, pk, ShoppingCart, RecipeShortSerializer
        )

    @action(detail=True, methods=['get'], url_path='get-link',
            permission_classes=[permissions.AllowAny])
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        link_data = {'short-link': str(recipe.pk)}
        return Response(link_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='download_shopping_cart',
            permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients_summary = RecipeIngredient.objects.filter(
            recipe__in_shopping_carts__user=user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        if not ingredients_summary:
            return Response(
                {'errors': 'Список покупок пуст'},
                status=status.HTTP_400_BAD_REQUEST
            )

        shopping_list_text = "Список покупок Foodgram:\n\n"
        for item in ingredients_summary:
            name = item['ingredient__name']
            unit = item['ingredient__measurement_unit']
            amount = item['total_amount']
            shopping_list_text += f"• {name} ({unit}) — {amount}\n"

        response = HttpResponse(
            shopping_list_text, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="foodgram_shopping_list.txt"'
        )
        return response


class UserAvatarSerializer(serializers.Serializer):
    """
    Сериализатор для приема аватара в base64
    """
    avatar = Base64ImageField(required=True, allow_null=False)

    class Meta:
        fields = ('avatar',)


class UserAvatarView(generics.GenericAPIView):
    """
    View для обновления/удаления аватара текущего пользователя
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.JSONParser]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        user = self.get_object()

        input_serializer = UserAvatarSerializer(data=request.data)
        if input_serializer.is_valid():
            avatar_file = input_serializer.validated_data['avatar']
        else:
            return Response(
                input_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        user.avatar = avatar_file
        user.save(update_fields=['avatar'])
        avatar_url = request.build_absolute_uri(
            user.avatar.url
        ) if user.avatar else None

        response_data = {
            "avatar": avatar_url
        }
        if avatar_url is None:
            return Response(
                {"detail": (
                    "Не удалось получить URL аватара после сохранения."
                )},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(response_data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        if not user.avatar or not user.avatar.name:
            return Response(
                {'detail': 'Аватар не установлен.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionViewSet(viewsets.ViewSetMixin, generics.ListAPIView):
    """
    API эндпоинт для управления подписками
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return SubscriptionSerializer
        return SubscriptionSerializer

    def get_queryset(self):
        user = self.request.user
        return user.subscriptions.all()

    def subscribe(self, request, user_id=None):
        user = request.user
        author = get_object_or_404(CustomUser, id=user_id)

        if user == author:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription_exists = Subscription.objects.filter(
            user=user, author=author
        ).exists()

        if request.method == 'POST':
            if subscription_exists:
                return Response(
                    {'errors': 'Вы уже подписаны на этого автора'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription = Subscription.objects.create(
                user=user, author=author
            )
            serializer = self.get_serializer(
                subscription, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            if not subscription_exists:
                return Response(
                    {'errors': 'Вы не были подписаны на этого автора'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.filter(user=user, author=author).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


User = get_user_model()


class CustomUserViewSet(DjoserUserViewSet):
    """
    Вьюсет для управления пользователями
    """
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    def get_instance(self):
        user = self.request.user
        if isinstance(user, AnonymousUser):
            raise NotAuthenticated()
        return user

    @action(detail=False, methods=['get'], url_path='subscriptions',
            permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        user = self.request.user
        queryset = user.subscriptions.all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, id=None):
        user = self.request.user
        author = get_object_or_404(User, id=id)
        if user == author:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription_exists = Subscription.objects.filter(
            user=user, author=author
        ).exists()
        if request.method == 'POST':
            if subscription_exists:
                return Response(
                    {'errors': 'Вы уже подписаны на этого автора'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription = Subscription.objects.create(
                user=user, author=author
            )
            serializer = SubscriptionSerializer(
                subscription, context={'request': request}
            )
            return Response(
                serializer.data, status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            deleted, _ = Subscription.objects.filter(
                user=user, author=author
            ).delete()
            if deleted == 0:
                return Response(
                    {'errors': 'Вы не были подписаны на этого автора'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        methods=['put', 'delete'], detail=False, url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[parsers.JSONParser]
    )
    def avatar(self, request, *args, **kwargs):
        user = self.request.user
        if request.method == 'PUT':
            serializer = UserAvatarSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            avatar_file_obj = serializer.validated_data['avatar']
            user.avatar = avatar_file_obj
            user.save(update_fields=['avatar'])

            avatar_url = None
            if user.avatar:
                try:
                    avatar_url = request.build_absolute_uri(user.avatar.url)
                except ValueError:
                    avatar_url = user.avatar.url
                except Exception:
                    pass

            avatar_url = avatar_url if avatar_url is not None else ""

            response_data = {'avatar': avatar_url}
            return Response(response_data, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            if not user.avatar or not user.avatar.name:
                return Response(
                    {'detail': 'Аватар не установлен.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
