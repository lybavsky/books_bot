from django.core.management import BaseCommand

from books_catalog.models import Genre


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def handle(self, *args, **options):
        print("start to seed genres")

        genres = ['Фантастика', 'Проза', 'Поэзия']

        for genre in genres:
            db_genre = Genre(name=genre)
            db_genre.save()
