# Foodgram

Foodgram — это веб-приложение для публикации рецептов. Пользователи могут создавать рецепты, добавлять их в избранное, подписываться на авторов и формировать список покупок.

## Технологии

### Backend
- Python
- Django
- Django REST Framework

### Frontend
- React
- JavaScript

### Инфраструктура
- Docker
- Docker Compose
- Nginx

## Структура проекта

foodgram/
├── .github/
│   └── workflows/               # CI/CD сценарии
├── backend/                     # backend-приложение Django
├── docs/                        # документация проекта
├── frontend/                    # frontend-приложение
├── infra/                       # инфраструктурные файлы для запуска
├── nginx/                       # конфигурация nginx
├── postman_collection/          # коллекция запросов Postman
├── .gitignore
├── LICENSE
├── README.md
├── docker-compose.production.yml
├── docker-compose.yml
└── setup.cfg