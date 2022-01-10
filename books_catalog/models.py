from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=64, verbose_name="Название жанра", blank=False)
    fb2_name = models.CharField(max_length=16, verbose_name="Алиас в fb2", blank=True, unique=True)

    class Meta:
        verbose_name_plural = "Жанры"
        verbose_name = "Жанр"

    def __str__(self):
        return self.name


class Author(models.Model):
    first_name = models.CharField(max_length=128, verbose_name="Имя")
    last_name = models.CharField(max_length=128, verbose_name="Фамилия")

    class Meta:
        verbose_name_plural = "Авторы"
        verbose_name = "Автор"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return "(" + str(self.id) + ") " + self.last_name + ", " + self.first_name


class Book(models.Model):
    name = models.TextField(blank=False, verbose_name="Название")

    author = models.ForeignKey(Author, on_delete=models.RESTRICT)

    genres = models.ManyToManyField(Genre)

    year = models.IntegerField(verbose_name="Год издания", null=True, default=0)



    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Книги"
        verbose_name = "Книга"
        ordering = ['name']

class FB2File(models.Model):
    book = models.ForeignKey(Book, on_delete=models.RESTRICT)

    description = models.TextField(verbose_name="Описание")

    lang = models.CharField(max_length=2, verbose_name="Язык", null=True, blank=True)

    path = models.TextField(verbose_name="Путь до файла с книгой")
    archive_path = models.TextField(verbose_name="Путь до файла внутри архива, если путь - архив", null=True)
    archive_path_conv = models.TextField(verbose_name="Кодировка архива", null=True)

    hash = models.CharField(max_length=16, verbose_name="MD5 хэш файла", null=False, name="hash")

    indexes = [
        models.Index('hash', name="hash_idx"),
    ]

    cover_path = models.TextField(default="")

class Config(models.Model):
    name = models.TextField(blank=False, verbose_name="Название параметра")
    value = models.TextField(blank=False, verbose_name="Значение параметра")


class TgUser(models.Model):
    userid = models.BigIntegerField(blank=False, verbose_name="ID пользователя telegram", unique=True)
    lang = models.TextField(blank=True, verbose_name="Язык пользователя telegram")
    first_name = models.TextField(blank=True)
    last_name = models.TextField(blank=True)
    allowed = models.BooleanField(null=True, verbose_name="Разрешен ли пользователю доступ к боту", default=False)

class TgHistory(models.Model):
    tguser = models.ForeignKey(TgUser, on_delete=models.RESTRICT)
    date = models.DateTimeField(blank=False)
    text = models.TextField(blank=False)