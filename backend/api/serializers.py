import base64
from collections import Counter

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from rest_framework import serializers
from recipes.models import (
    Favorite,
    Follow,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    Tag,
)

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для работы с base64 изображениями."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            filename = f'temp.{ext}'
            data = ContentFile(base64.b64decode(imgstr), name=filename)
        return super().to_internal_value(data)


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для изменения пароля пользователя."""

    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )

    def validate_current_password(self, value):
        """Валидация текущего пароля."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                'Пользователь не аутентифицирован'
            )
        user = request.user
        if not user.check_password(value):
            raise serializers.ValidationError('Неверный пароль')
        return value

    def validate(self, data):
        """Проверка, что новый пароль отличается от старого."""
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError(
                'Новый пароль должен отличаться от старого'
            )
        return data


class UserSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор пользователя.

    Используется для:
    - получения списка всех пользователей
    - просмотра профиля конкретного пользователя
    - просмотра профиля текущего аутентифицированного пользователя
    """

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.following.filter(author=obj).exists()
        return False

    def get_avatar(self, obj):
        """Возвращает URL аватара или пустую строку."""
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return ''


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя, [POST /api/users/]."""
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True,
        min_length=8,
        help_text='Пароль должен содержать минимум 8 символов',
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'password')
        read_only_fields = ('id',)

    def validate_email(self, value):
        """Валидация email."""

        normalized_email = value.strip().lower()
        if User.objects.filter(email=normalized_email).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует.'
            )
        return normalized_email

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class FollowSerializer(UserSerializer):
    """Сериализатор для отображения информации о подписках пользователя."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        return True

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        """Возвращает ограниченный список рецептов автора."""
        request = self.context.get('request')
        recipes = obj.recipes.all()

        if request:
            limit = request.query_params.get('recipes_limit')
            if limit and limit.isdigit():
                try:
                    recipes = recipes[:int(limit)]
                except (ValueError, TypeError):
                    pass

        return RecipeMinifiedSerializer(
            recipes, many=True, context=self.context
        ).data


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов рецептов."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения ингридиента в рецепте."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = fields


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """Сериализатор для ингридиентов при создании рецептов."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(
        min_value=1,
        max_value=10000
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого отображения рецепта."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientReadSerializer(
        many=True,
        source='ingredient_recipes'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingList.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    ingredients = RecipeIngredientWriteSerializer(
        many=True,
        required=True,
        label='Ингредиенты',
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True,
        label='Теги',
    )
    cooking_time = serializers.IntegerField(
        min_value=1,
        max_value=500,
        required=True
    )
    image = Base64ImageField(required=True)
    name = serializers.CharField(required=True, max_length=200)
    text = serializers.CharField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time'
        )

    def to_representation(self, instance):
        """Преобразование в сериализатор для чтения после сохранения."""
        return RecipeReadSerializer(
            instance,
            context=self.context
        ).data

    def create_ingredients(self, ingredients, recipe):
        """Создание связей рецепта с ингредиентами."""
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients
        ])

    def create(self, validated_data):
        """Создание рецепта с ингредиентами и тегами."""
        validated_data_copy = validated_data.copy()
        ingredients = validated_data_copy.pop('ingredients')
        tags = validated_data_copy.pop('tags')
        validated_data_with_author = {
            **validated_data_copy,
            'author': self.context['request'].user
        }
        recipe = super().create(validated_data_with_author)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта с ингредиентами и тегами."""
        validated_data_copy = validated_data.copy()
        ingredients = validated_data_copy.pop('ingredients', None)
        tags = validated_data_copy.pop('tags', None)
        if tags is not None:
            instance.tags.clear()
            instance.tags.set(tags)
        if ingredients is not None:
            instance.ingredient_recipes.all().delete()
            self.create_ingredients(ingredients, instance)
        for attr, value in validated_data_copy.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def validate_ingredients(self, ingredients):
        """Валидация ингредиентов."""
        if not ingredients:
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один ингредиент.'
            )
        ingredient_ids = [item['id'].id for item in ingredients]
        duplicate_ids = {
            id_ for id_, count in Counter(ingredient_ids).items()
            if count > 1
        }
        if duplicate_ids:
            duplicate_names = Ingredient.objects.filter(
                id__in=duplicate_ids
            ).values_list('name', flat=True)
            names_string = ', '.join(duplicate_names)
            raise serializers.ValidationError(
                f'Ингредиенты не должны повторяться: {names_string}.'
            )
        return ingredients

    def validate_tags(self, tags):
        """Валидация тегов."""
        if not tags:
            raise serializers.ValidationError(
                'Нужно выбрать хотя бы один тег.'
            )
        tag_ids = [tag.id for tag in tags]
        duplicate_ids = {
            id_ for id_, count in Counter(tag_ids).items()
            if count > 1
        }
        if duplicate_ids:
            names = Tag.objects.filter(
                id__in=duplicate_ids
            ).values_list('name', flat=True)
            names_string = ', '.join(names)
            raise serializers.ValidationError(
                f'Теги не должны повторяться: {names_string}.'
            )
        return tags

    def validate(self, data):
        """Общая валидация."""
        request_method = self.context['request'].method
        if request_method in ('POST', 'PATCH'):
            if 'ingredients' not in data or not data['ingredients']:
                raise serializers.ValidationError({
                    'ingredients': 'Это поле обязательно.'
                })
            if 'tags' not in data or not data['tags']:
                raise serializers.ValidationError({
                    'tags': 'Это поле обязательно.'
                })
        return data


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с аватаром."""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class AvatarDeleteSerializer(serializers.ModelSerializer):
    """Сериализатор для удаления аватара пользователя."""

    class Meta:
        model = User
        fields = ()

    def validate(self, data):
        """Проверяем, есть ли аватар для удаления."""
        user = self.instance
        if not user.avatar:
            raise serializers.ValidationError(
                {'detail': 'Аватар отсутствует'}
            )
        return data

    def save(self, **kwargs):
        """Удаляем аватар через метод модели."""
        user = self.instance
        user.remove_avatar()
        return user


class SubscribeSerializer(serializers.Serializer):
    """Сериализатор для создания и удаления подписки на автора."""

    def validate(self, data):
        """Валидация данных для подписки/отписки."""
        request = self.context.get('request')
        author = self.context.get('author')
        request_method = self.context.get('request_method')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                {'detail': 'Пользователь не аутентифицирован'}
            )
        user = request.user
        if user == author:
            raise serializers.ValidationError(
                {'detail': 'Нельзя подписаться на самого себя'}
            )
        is_subscribed = user.following.filter(author=author).exists()
        if request_method == 'POST':
            if is_subscribed:
                raise serializers.ValidationError(
                    {'detail': 'Вы уже подписаны на этого автора'}
                )
        elif request_method == 'DELETE':
            if not is_subscribed:
                raise serializers.ValidationError(
                    {'detail': 'Вы не подписаны на этого автора'}
                )
        data['author'] = author
        data['user'] = user
        return data

    def save(self, **kwargs):
        """Создаем или удаляем подписку."""
        request_method = self.context.get('request_method')
        author = self.validated_data.get('author')
        user = self.validated_data.get('user')
        if request_method == 'POST':
            follow = Follow.objects.create(user=user, author=author)
            return follow
        elif request_method == 'DELETE':
            deleted_count, _ = user.following.filter(author=author).delete()
            return deleted_count > 0

    def to_representation(self, instance):
        """Преобразуем результат для ответа."""
        request_method = self.context.get('request_method')
        if request_method == 'POST':
            author = self.validated_data.get('author')
            return FollowSerializer(author, context=self.context).data
        return {}


class RecipeActionSerializer(serializers.Serializer):
    """Универсальный сериализатор для операций с рецептами."""

    def validate(self, data):
        """Валидация в зависимости от типа действия."""
        request = self.context.get('request')
        recipe = self.context.get('recipe')
        action_type = self.context.get('action_type')
        action = self.context.get('action')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                {'detail': 'Пользователь не аутентифицирован'}
            )
        if not recipe:
            raise serializers.ValidationError({'detail': 'Рецепт не указан'})
        if action_type == 'favorite':
            model = Favorite
            already_exists_message = f'Рецепт "{recipe.name}" уже в избранном!'
            not_found_message = f'Рецепта "{recipe.name}" нет в избранном!'
        else:
            model = ShoppingList
            already_exists_message = 'Рецепт уже в списке покупок.'
            not_found_message = 'Рецепта нет в списке покупок.'
        exists = model.objects.filter(
            user=request.user, recipe=recipe
        ).exists()
        if action == 'add' and exists:
            raise serializers.ValidationError(
                {'detail': already_exists_message}
            )
        if action == 'remove' and not exists:
            raise serializers.ValidationError(
                {'detail': not_found_message}
            )
        data['user'] = request.user
        data['recipe'] = recipe
        data['model'] = model
        return data

    def create(self, validated_data):
        """Создает запись (для POST запросов)."""
        user = validated_data['user']
        recipe = validated_data['recipe']
        model = validated_data['model']
        instance = model.objects.create(user=user, recipe=recipe)
        return instance

    def delete(self, validated_data):
        """Удаляет запись (для DELETE запросов)."""
        user = validated_data['user']
        recipe = validated_data['recipe']
        model = validated_data['model']
        deleted_count, _ = model.objects.filter(
            user=user, recipe=recipe
        ).delete()
        return deleted_count > 0
