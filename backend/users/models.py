from django.contrib.auth.models import AbstractUser
from django.db import models

from foodgram.constants import (USER_EMAIL_LENGTH, USER_FIRST_NAME_LENGTH,
                                USER_LAST_NAME_LENGTH, USER_USERNAME_LENGTH)


class User(AbstractUser):
    """Модель пользователя."""

    first_name = models.CharField(
        'Имя',
        max_length=USER_FIRST_NAME_LENGTH,
        blank=False,
        null=False,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=USER_LAST_NAME_LENGTH,
        blank=False,
        null=False,
    )
    username = models.CharField(
        'Имя пользователя',
        max_length=USER_USERNAME_LENGTH,
        unique=True,
        blank=False,
        null=False,
        help_text='Обязательное поле. Только буквы, цифры и @/./+/-/_.'
    )
    email = models.EmailField(
        'email address',
        unique=True,
        max_length=USER_EMAIL_LENGTH,
        blank=False,
        null=False,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        null=True,
        blank=True,
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    def remove_avatar(self):
        """Удаляет аватар пользователя."""
        if self.avatar:
            self.avatar.delete(save=False)
            self.avatar = None
            self.save()
