import json
import os

from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты из заранее подготовленного JSON-файла'

    def handle(self, *args, **kwargs):
        filepath = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        ),
            '..', '..', '..', 'data', 'ingredients.json')
        filepath = os.path.abspath(filepath)

        if not os.path.exists(filepath):
            self.stderr.write(self.style.ERROR(f'Файл не найден: {filepath}'))
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)

                created = 0

                for item in data:
                    obj, is_created = Ingredient.objects.get_or_create(
                        name=item['name'],
                        measurement_unit=item['measurement_unit']
                    )
                    if is_created:
                        created += 1

                self.stdout.write(self.style.SUCCESS(
                    f'Ингредиенты загружены! Создано {created} новых объектов.'
                ))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR('Ошибка при чтении JSON-файла'))
