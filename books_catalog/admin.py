from django.contrib import admin

# Register your models here.
from books_catalog.models import Genre, Author, Book

admin.site.register(Genre)
admin.site.register(Author)
admin.site.register(Book)

