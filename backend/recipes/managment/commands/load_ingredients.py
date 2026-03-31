import os

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from tqdm import tqdm

from recipes.models import Ingredient, Tag


class Command(BaseCommand):

    help = 'Импортирование CSV-файлов в модели Ingredient и Tag'

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        csv_path_ingredients = os.path.join(
            base_dir, 'data', 'ingredients.csv'
        )
        csv_path_tags = os.path.join(base_dir, 'data', 'tags.csv')

        if options.get('clear', False):
            Ingredient.objects.all().delete()
            Tag.objects.all().delete()
            self.stdout.write('Существующие данные очищены')

        self.import_ingredients(csv_path_ingredients)
        self.import_tags(csv_path_tags)
        self.stdout.write(
            self.style.SUCCESS('Все данные успешно импортированы!')
        )

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие данные перед импортом',
        )

    def import_ingredients(self, file_path):
        """Импорт ингредиентов с обработкой дубликатов."""
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл не найден: {file_path}')
            )
            return

        data_frame = pd.read_csv(file_path)
        records_count = len(data_frame)
        self.stdout.write(f'Найдено {records_count} записей в CSV')
        created_count = 0
        skipped_count = 0
        with tqdm(total=records_count, desc='Импорт ингредиентов') as pbar:
            for row_index, row in data_frame.iterrows():
                name = str(row.iloc[0]).strip()
                measurement_unit = str(row.iloc[1]).strip()
                try:
                    ingredient, created = Ingredient.objects.get_or_create(
                        name=name,
                        measurement_unit=measurement_unit
                    )
                except Exception as error:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Ошибка в строке {row_index}: {error}'
                        )
                    )
                    skipped_count += 1
                else:
                    if created:
                        created_count += 1
                    else:
                        skipped_count += 1
                finally:
                    pbar.update(1)
        success_message = (
            f'Ингредиенты: создано {created_count}, '
            f'пропущено {skipped_count}'
        )
        self.stdout.write(self.style.SUCCESS(success_message))

    def import_tags(self, file_path):
        """Импорт тегов с обработкой дубликатов."""
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл не найден: {file_path}')
            )
            return
        data_frame = pd.read_csv(file_path)
        records_count = len(data_frame)
        self.stdout.write(f'Найдено {records_count} записей в CSV')
        created_count = 0
        skipped_count = 0
        with tqdm(total=records_count, desc='Импорт тегов') as pbar:
            for row_index, row in data_frame.iterrows():
                name = str(row.iloc[0]).strip()
                slug = str(row.iloc[1]).strip()
                try:
                    tag, created = Tag.objects.get_or_create(
                        name=name,
                        slug=slug
                    )
                except Exception as error:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Ошибка в строке {row_index}: {error}'
                        )
                    )
                    skipped_count += 1
                else:
                    if created:
                        created_count += 1
                    else:
                        skipped_count += 1
                finally:
                    pbar.update(1)
        success_message = (
            f'Теги: создано {created_count}, '
            f'пропущено {skipped_count}'
        )
        self.stdout.write(self.style.SUCCESS(success_message))
