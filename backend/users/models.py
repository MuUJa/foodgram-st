from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Q, F


class CustomUser(AbstractUser):
    """
    Кастомная модель пользователя
    """
    email = models.EmailField('email address', unique=True)

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']


class Subscription(models.Model):
    """
    Модель подписки пользователя на автора
    """
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='subscriptions')

    author = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='subscribers')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'], name='unique_subscription'),
            models.CheckConstraint(
                check=~Q(user=F('author')), name='prevent_self_subscription'),
        ]

    def __str__(self):
        try:
            return f"{self.user.username} подписан на {self.author.username}"
        except (CustomUser.DoesNotExist, AttributeError):
            return (
                f"Подписка: Пользователь ID {self.user_id} -> "
                f"Автор ID {self.author_id}"
            )
