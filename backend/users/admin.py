from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Subscription


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Настройка админки для кастомной модели пользователя
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'username')
    list_filter = ('is_staff', 'is_superuser', 'is_active',
                   'groups')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    Настройка админки для модели подписок
    """
    list_display = ('id', 'user', 'author')
    search_fields = ('user__username', 'user__email',
                     'author__username', 'author__email')
    autocomplete_fields = ['user', 'author']
