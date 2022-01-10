from django.core.management import BaseCommand

from books_catalog.models import Genre, Author, Book


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def handle(self, *args, **options):
        print("start to seed genres")

        genre = Genre.objects.filter(name='Проза').get()

        author = Author(first_name="Александр", last_name='Пушкин')
        author.save()

        for book_name in ['Дубровский', 'Капитанская дочка']:
            book=Book(name=book_name,description="not yet description")
            book.save()
            book.author.add(author)
            book.save()
