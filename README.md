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

```bash
foodgram/
├── .github/
│   └── workflows/            # CI/CD сценарии
├── backend/                  # Django backend
├── docs/                     # документация проекта
├── frontend/                 # React frontend
├── infra/                    
├── nginx/                    # конфигурация nginx
├── postman_collection/       # коллекция Postman
├── .gitignore
├── LICENSE
├── README.md
├── docker-compose.yml
├── docker-compose.production.yml
└── setup.cfg
