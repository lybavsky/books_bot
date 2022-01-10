import json

from fb2.job import FB2Job


class FB2Structure:

    def __init__(self, job):
        self.job = FB2Job(job.id, job.path, job.archive_path, job.archive_path_conv)
        self.genres = []
        self.first_name = ""

        self.last_name = ""

        self.title = ""
        self.annotation = ""
        self.cover_filename = ""
        self.cover_bytes = None

        self.lang = ""
        self.src_lang = ""

        self.year = ""

        self.id = -1

        self.hash = ""

    def add_genre(self, genre):
        self.genres.append(genre)

    def set_first_name(self, first_name):
        self.first_name = first_name

    def set_last_name(self, last_name):
        self.last_name = last_name

    def set_title(self, title):
        self.title = title

    def set_annotation(self, annotation):
        self.annotation = annotation

    def set_lang(self, lang):
        self.lang = lang

    def set_id(self, id):
        self.id = id

    def set_src_lang(self, src_lang):
        self.src_lang = src_lang

    def set_coverfile(self, name, bytes):
        if bytes == None or name == "":
            return
        self.cover_bytes = bytes
        self.cover_filename = name

    def get_coverfile(self):
        return (self.cover_filename, self.cover_bytes)

    def set_year(self, year):
        self.year = year

    def set_hash(self, hash):
        self.hash = hash

    def get_hash(self):
        return self.hash

    def get(self):
        return {
            "genres": self.genres,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "title": self.title,
            "annotation": self.annotation,
            "cover_filename": self.cover_filename,
            "path": self.job.path,
            "archive_path": self.job.archive_path,
            "archive_path_conv": self.job.archive_path_conv,
            "lang": self.lang,
            "src_lang": self.src_lang,
            "year": self.year,
            "id": self.id,
            "hash": self.hash,

        }

    def print(self):
        print("id: ", self.id)
        print("author: ", self.last_name + " ", self.first_name)
        print("title: ", self.title)
        print("genres: ", self.genres)
        print("lang: ", self.lang)
        print("src_lang: ", self.src_lang)
        print("annotation: ", self.annotation)
        print("year", self.year)
        print(self.job.path, ("->", self.job.archive_path) if self.job.archive_path != "" else "")
        print("\n\n")
