import glob
import os
import uuid
from glob import glob
from threading import Lock
from typing import IO

from books.settings import COVERS_DIR, MANUAL_UPLOAD_DIR, BOOKS_DIR
from books_catalog.models import Book, Author, Genre, FB2File, TgHistory, TgUser
from fb2.consts import GENRES
from fb2.job import FB2Job

import zipfile
import io

from fb2.struct import FB2Structure
from fb2.parser import parse_fb2


def validate_form_fb2(file: IO):
    print(file)

    ba = file.read()

    if str(file).endswith(".zip"):
        zf = zipfile.ZipFile(io.BytesIO(ba), "r")
        for fileinfo in zf.infolist():
            ba = zf.read(fileinfo)
            break
        zf.close()

    job = FB2Job(id=-1, path="", archive_path="", archive_path_conv="", fb2_str=ba)

    try:
        fb2_res = parse_fb2(job)

        return {"res": fb2_res, "bytes": ba}
    except Exception as e:
        return Exception(str(e))


def get_cover_dirname(id: int):
    return COVERS_DIR + "/" + str(int(id / 1000))


def save_cover(id: int, bs, suffix=".jpg"):
    fpath = get_cover_path(id, suffix)

    f = open(fpath, "bw")
    f.write(bs)
    f.flush()
    f.close()

    return fpath


def save_fb2_file(bs):
    if not os.path.isdir(BOOKS_DIR + "/" + MANUAL_UPLOAD_DIR):
        os.makedirs(BOOKS_DIR + "/" + MANUAL_UPLOAD_DIR, exist_ok=True)
    unique_filename = BOOKS_DIR + "/" + MANUAL_UPLOAD_DIR + "/" + str(uuid.uuid4()) + ".fb2"

    f = open(unique_filename, "bw")
    f.write(bs)
    f.flush()
    f.close()

    return unique_filename


def get_cover_path(id: int, suffix=".jpg"):
    dirname = get_cover_dirname(id)
    if not os.path.isdir(dirname):
        os.makedirs(dirname, exist_ok=True)

    fpath = dirname + "/" + str(id) + suffix

    return fpath


genres_lock = Lock()
author_lock = Lock()


def save_book_to_db(struct: FB2Structure):
    # print(struct)

    with author_lock:
        try:
            if struct.first_name != None:
                fname = struct.first_name
            else:
                fname = "Unknown"

            if struct.last_name != None:
                lname = struct.last_name
            else:
                lname = "Unknown"
            author = Author.objects.filter(first_name__exact=fname, last_name__exact=lname).get()
        except Author.DoesNotExist:
            author = Author(first_name=fname, last_name=lname)
            author.save()

    genres = []
    for genre in struct.genres:
        str_genre = genre
        if genre in GENRES:
            str_genre = GENRES[genre]

        if genre == None or genre == "":
            genre = "Unknown"
            str_genre = "Unknown"

        with genres_lock:
            try:
                genre = Genre.objects.filter(fb2_name__exact=genre).get()
            except Genre.DoesNotExist:
                print("Will create genre " + genre + " (" + str_genre + ")")
                genre = Genre(fb2_name=genre, name=str_genre)
                genre.save()

        genres.append(genre)

        try:
            year_int = int(struct.year)
        except ValueError:
            year_int = 0

        if struct.title == None or struct.title == "":
            struct.title = "Unknown"

        if book_exists(struct.hash):
            print(
                "Book with hash already exists: " + struct.hash + ": " + struct.title + " (" + lname + " " + fname + ")")
            return -1

        try:
            book = Book.objects.filter(name=struct.title, author=author).get()
        except Book.DoesNotExist:
            book = Book(name=struct.title, author=author, year=year_int)
            book.save()

        book.genres.set(genres)

        book_id = book.id

        fb2file = FB2File(book=book,
                          description=struct.title,
                          path=struct.job.path,
                          archive_path=struct.job.archive_path,
                          archive_path_conv=struct.job.archive_path_conv,
                          hash=struct.hash,
                          lang=struct.lang
                          )

        fb2file.save()

        if struct.cover_filename != "" and struct.cover_bytes != None:
            cover = struct.cover_bytes
            cover_ext = struct.cover_filename.split(".")[-1]
            cpath = save_cover(fb2file.id, cover, suffix="." + cover_ext)
            fb2file.cover_path = cpath

        fb2file.save()

        return book_id


def books_count(dirs):
    count = 0
    for dir in dirs:
        print("Will get count files in dir " + dir)

        fb2s = glob(dir + "/**/*.fb2", recursive=True)
        count += len(fb2s)

        zip_archs = glob(dir + "/**/*.zip", recursive=True)
        for zip_arch in zip_archs:
            try:
                zipf = zipfile.ZipFile(zip_arch, "r")
                for zipf_f in zipf.filelist:
                    if zipf_f.filename.endswith(".fb2"):
                        count += 1
            except zipfile.BadZipFile as e:
                ()

    return count


def clear_db():
    TgHistory.objects.all().delete()
    TgUser.objects.all().delete()
    FB2File.objects.all().delete()
    Book.objects.all().delete()
    Author.objects.all().delete()
    Genre.objects.all().delete()


def book_exists(hash: str):
    return FB2File.objects.filter(hash=hash).exists()
