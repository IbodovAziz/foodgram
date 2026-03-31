from django.contrib import admin
from django.contrib.admin import display

from .models import (
    Favorite,
    Follow,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    Tag,
)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Админ-панель для управления рецептами."""

    list_display = ('name', 'author', 'cooking_time', 'favorites_count',
                    'pub_date')
    list_display_links = ('name',)
    search_fields = ('name', 'author__username')
    list_filter = ('tags', 'pub_date', 'author')
    readonly_fields = ('pub_date',)

    @display(description='В избранном')
    def favorites_count(self, obj):
        """Количество добавлений рецепта в избранное."""
        return obj.favorites.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админ-панель для управления ингредиентами."""

    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)
    ordering = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Админ-панель для управления тегами рецептов."""

    list_display = ('name', 'slug')
    list_display_links = ('name',)
    search_fields = ('name', 'slug')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Админ-панель для управления избранными рецептами."""

    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    """Админ-панель для управления списками покупок."""

    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Админ-панель для управления подписками на авторов."""

    list_display = ('user', 'author')
    search_fields = ('user__username', 'author__username')


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    """Админ-панель для управления связями рецептов и ингредиентов."""

    list_display = ('recipe', 'ingredient', 'amount')
    list_display_links = ('recipe', 'ingredient')
    search_fields = ('recipe__name', 'ingredient__name')
