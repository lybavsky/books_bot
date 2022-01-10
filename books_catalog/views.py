import base64
import mimetypes

import zipfile
from io import BytesIO
from pprint import pprint

from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from books.settings import PROJECT_ROOT
from books_catalog.forms import UploadFileForm
from books_catalog.models import Genre, Author, Book, FB2File, TgUser, TgHistory
from es.es import ESClient
from fb2.job import FB2Job

from fb2.struct import FB2Structure
from fb2.tools import validate_form_fb2, save_book_to_db, save_fb2_file
from fb2.scaner import L, rescan

from fb2.status import Status


def genres_view(request: HttpRequest):
    genres = Genre.objects.all()
    print(genres)
    context = {'genres': genres}
    return render(request, "genres.html", context)


def authors_view(request: HttpRequest):
    authors = Author.objects.all()
    print(authors)
    context = {'authors': authors}
    return render(request, "authors.html", context)


def books_view(request: HttpRequest):
    books = Book.objects.all()
    print(books)
    context = {'books': books}
    return render(request, "books.html", context)


def book_view(request: HttpRequest, book_id: int):
    try:
        book = Book.objects.filter(id=book_id).get()
    except Book.DoesNotExist:
        return redirect(reverse("books"))

    context = {'book': book, 'fb2file_set': book.fb2file_set.all()}
    return render(request, "book.html", context)


def books_view_genre(request: HttpRequest, genre_id: int):
    books = Book.objects.filter(genres__id=genre_id)
    genre = Genre.objects.get(id=genre_id)
    context = {'books': books, 'genre': genre}
    return render(request, "books.html", context)


def books_view_author(request: HttpRequest, author_id: int):
    books = Book.objects.filter(author_id=author_id)
    author = Author.objects.get(id=author_id)
    context = {'books': books, 'author': author}
    return render(request, "books.html", context)


def genre_new(request: HttpRequest):
    if request.method == 'GET':
        return render(request, "genre_new.html")
    else:

        try:
            val = request.POST.get("genre")
            genre = Genre()
            genre.name = val
            genre.save()
        except IntegrityError as e:
            ()
        return redirect(reverse("genres"))


def genre_delete(request: HttpRequest, genre_id):
    try:
        g = Genre.objects.get(id=genre_id)
        g.delete()
    except Genre.DoesNotExist:
        ""
    return redirect(reverse("genres"))


def upload(request: HttpRequest):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            res = validate_form_fb2(request.FILES['file'])
            val_res = res["res"]
            val_str = {
                "title": val_res.title,
                "fname": val_res.first_name,
                "lname": val_res.last_name,
                "lang": val_res.lang,
                "year": val_res.year,
                "annotation": val_res.annotation,
                "genres": val_res.genres,
                "bytes": base64.b64encode(res["bytes"]).decode("ascii"),
                "hash": val_res.hash,
            }
            if val_res.cover_bytes != None and val_res.cover_filename != "":
                val_str["cover_bytes"] = base64.b64encode(val_res.cover_bytes).decode("ascii")
                val_str["cover_filename"] = val_res.cover_filename

            if type(val_res) is Exception:
                print(str(val_res))
                return render(request, "upload.html", {'form': form, 'error_msg': str(val_res)})

            request.session['val_str'] = val_str
            return redirect(reverse("validate"))
    else:
        form = UploadFileForm()

    return render(request, "upload.html", {'form': form})


def validate(request: HttpRequest):
    val_str = request.session.get("val_str", "")
    if val_str == "":
        request.session.flush()
        return redirect(reverse("upload"))

    if request.method == 'GET':
        return render(request, "validate.html", {'data': val_str})
    else:

        bs = val_str["bytes"]
        filename = save_fb2_file(base64.b64decode(bs.encode("ascii")))

        job = FB2Job(id=-1, path=filename, archive_path="", archive_path_conv="")

        struct = FB2Structure(job)
        struct.first_name = val_str["fname"]
        struct.last_name = val_str["lname"]
        struct.genres = val_str["genres"]
        struct.lang = val_str["lang"]

        struct.path = filename
        struct.archive_path = ""
        struct.archive_path_conv = ""

        struct.hash = val_str["hash"]

        try:
            struct.year = int(val_str["year"])
        except ValueError:
            struct.year = -1
        struct.title = val_str["title"]
        struct.annotation = val_str["annotation"]
        struct.cover_bytes = base64.b64decode(val_str["cover_bytes"].encode("ascii"))
        struct.cover_filename = val_str["cover_filename"]

        struct.job.path = filename

        with L():
            book_id = save_book_to_db(struct)
            if book_id == -1:
                form = UploadFileForm()
                return render(request, "upload.html", {'form': form, 'error_msg': "Book already exist"})

        ESClient.getInstance().addDocument({
            "genres": val_str["genres"],
            "first_name": val_str["fname"],
            "last_name": val_str["lname"],
            "title": val_str["title"],
            "annotation": val_str["annotation"],
            "id": book_id,
        })

        return redirect(reverse("book", args=(book_id,)))


def book_download(request: HttpRequest, book_id: int):
    fb2 = FB2File.objects.filter(id=book_id).get()

    if fb2.archive_path != None and fb2.archive_path != "":
        zipf = zipfile.ZipFile(fb2.path, "r")
        bs = zipf.read(fb2.archive_path)
        fbs = BytesIO(bs)
    else:
        f = open(fb2.path, 'rb')
        fbs = f.read()

    response = HttpResponse(fbs, content_type="application/x-fictionbook")

    response['Content-Disposition'] = "attachment; filename=%s" % (str(book_id) + ".fb2")
    return response


def cover_view(request: HttpRequest, cover_id: int):
    try:
        cover = FB2File.objects.filter(id=cover_id).get()
        if cover.cover_path == None or cover.cover_path == "":
            pth = PROJECT_ROOT + "/books_catalog/static/img/noimage.png"
        else:
            pth = cover.cover_path
    except Book.DoesNotExist:
        pth = PROJECT_ROOT + "/books_catalog/static/img/noimage.png"

    f = open(pth, 'rb')

    mime = mimetypes.guess_type(pth)

    response = HttpResponse(f, content_type=mime)

    covername = pth.split("/")[-1]

    response['Content-Disposition'] = "attachment; filename=%s" % covername
    return response


def scan_start(request: HttpRequest):
    if Status.getInstance().getScanStatus() != 0:
        Status.getInstance().startScan(rescan)
        return JsonResponse({"status": "ok"})
    else:
        return JsonResponse({"status": "already started"})


def scan_stop(request: HttpRequest):
    if Status.getInstance().getScanStatus() == 0:
        Status.getInstance().stopScan()
        return JsonResponse({"status": "ok"})
    else:
        return JsonResponse({"status": "already stopped"})


def scan_info(request: HttpRequest):
    return JsonResponse(Status.getInstance().getScanInfo())


def tg_list(request: HttpRequest):
    if request.method == "POST":

        userid = request.POST.get("userid")
        act = request.POST.get("act")


        pprint(act)
        pprint(userid)

        try:
            user: TgUser = TgUser.objects.filter(userid=userid).get()
            user.allowed = (act == "true")
            user.save()
        except TgUser.DoesNotExist:
            ()

    users = TgUser.objects.all()
    return render(request, "tg_list.html", {"users": users})


def tg_history(request: HttpRequest):
    history = TgHistory.objects.all().order_by('-id')[:500]
    return render(request, "tg_history.html", {"history": history})
