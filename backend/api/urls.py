from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (IngredientViewSet, RecipeViewSet, SubscriptionViewSet,
                    TagViewSet, UserAvatarView)

router_v1 = DefaultRouter()

router_v1.register('ingredients', IngredientViewSet, basename='ingredients')
router_v1.register('tags', TagViewSet, basename='tags')
router_v1.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path(
        'users/subscriptions/',
        SubscriptionViewSet.as_view({'get': 'list'}),
        name='user-subscriptions-list'
    ),
    path(
        'users/<int:user_id>/subscribe/',
        SubscriptionViewSet.as_view(
            {'post': 'subscribe', 'delete': 'subscribe'}
        ),
        name='user-subscribe'
    ),
    path(
        'users/me/avatar/',
        UserAvatarView.as_view(),
        name='user-me-avatar'
    ),
    path('', include(router_v1.urls)),
]
