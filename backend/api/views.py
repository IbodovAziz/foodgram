import hashlib

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from djoser.views import UserViewSet as DjoserUserViewSet

from foodgram.constants import TIMEOUT
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarDeleteSerializer,
    AvatarSerializer,
    FollowSerializer,
    IngredientSerializer,
    RecipeActionSerializer,
    RecipeMinifiedSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    SubscribeSerializer,
    TagSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    """Класс для базовой пагинации."""

    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100


class UserViewSet(DjoserUserViewSet):
    """ViewSet для работы с пользователями."""

    queryset = User.objects.all()
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action in {'create', 'list', 'retrieve'}:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'subscriptions':
            return FollowSerializer
        if self.action == 'avatar':
            if self.request.method == 'DELETE':
                return AvatarDeleteSerializer
            return AvatarSerializer
        if self.action == 'subscribe':
            return SubscribeSerializer
        return UserSerializer

    @action(
        methods=('put', 'delete'),
        detail=False,
        permission_classes=(IsAuthenticated,),
        url_path='me/avatar',
        url_name='me-avatar'
    )
    def avatar(self, request):
        """Обработка аватара (обновление и удаление)."""
        user = request.user
        if request.method == 'DELETE':
            user.remove_avatar()
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif request.method == 'PUT':
            serializer = self.get_serializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=('post', 'delete'),
        detail=True,
        permission_classes=(IsAuthenticated,),
        url_path='subscribe',
        url_name='subscribe'
    )
    def subscribe(self, request, pk=None):
        """Обработка подписки и отписки на автора."""
        author = get_object_or_404(User, pk=pk)
        serializer = self.get_serializer(
            data={},
            context={
                'request': request,
                'author': author,
                'request_method': request.method
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if request.method == 'POST':
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
        pagination_class=StandardResultsSetPagination,
        url_path='subscriptions',
        url_name='subscriptions'
    )
    def subscriptions(self, request):
        """Просмотр своих подписок."""
        authors = User.objects.filter(
            followers__user=request.user
        ).order_by('username')
        page = self.paginate_queryset(authors)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для тегов - только чтение для всех."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для ингредиентов - только чтение для всех."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с рецептами."""

    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'ingredient_recipes__ingredient')
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    def _handle_recipe_relation(self, request, pk, relation_type):
        """Общая логика для работы с отношениями рецептов."""
        recipe = self.get_object()
        action = 'add' if request.method == 'POST' else 'remove'
        serializer = RecipeActionSerializer(
            data={},
            context={
                'request': request,
                'recipe': recipe,
                'action_type': relation_type,
                'action': action
            }
        )
        serializer.is_valid(raise_exception=True)
        if action == 'add':
            serializer.save()
            response_serializer = RecipeMinifiedSerializer(
                recipe,
                context=self.get_serializer_context()
            )
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        else:
            serializer.delete(serializer.validated_data)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в избранное."""
        return self._handle_recipe_relation(request, pk, 'favorite')

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в список покупок."""
        return self._handle_recipe_relation(request, pk, 'shopping_cart')

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
        url_path='download_shopping_cart',
        url_name='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        """Выгрузка файла с количеством ингредиентов для рецептов из списка."""
        shopping_items = RecipeIngredient.objects.filter(
            recipe__in_shopping_lists__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        shopping_list = []
        for item in shopping_items:
            shopping_list.append(
                f'{item["ingredient__name"]} - {item["total_amount"]} '
                f'{item["ingredient__measurement_unit"]}'
            )
        content_lines = [
            'СПИСОК ПОКУПОК',
            ''
        ] + shopping_list + [
            '',
            f'Всего позиций: {len(shopping_items)}'
        ]
        response = HttpResponse(
            '\n'.join(content_lines),
            content_type='text/plain; charset=utf-8'
        )
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(
        detail=True,
        methods=('get',),
        url_path='get-link',
        permission_classes=(AllowAny,)
    )
    def get_short_link(self, request, pk=None):
        """Генерация короткой ссылки для рецепта."""
        recipe = self.get_object()
        short_hash = hashlib.md5(str(recipe.id).encode()).hexdigest()[:8]
        cache.set(f'short_link_{short_hash}', recipe.id, timeout=TIMEOUT)
        short_link = request.build_absolute_uri(f'/s/{short_hash}/')
        return Response({'short-link': short_link})


class ShortLinkRedirectView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, short_hash):
        recipe_id = cache.get(f'short_link_{short_hash}')
        if recipe_id is None:
            return Response(
                {'detail': 'Короткая ссылка не найдена.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return redirect(f'/recipes/{recipe_id}/')
