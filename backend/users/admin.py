from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Админ-панель для управления пользователями."""

    list_display = ('username', 'email', 'first_name', 'last_name',
                    'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    ordering = ('username',)
