from django.conf.urls.static import static
from django.urls import path
from django.views.generic import RedirectView

from books import settings
from books.settings import BASE_DIR
from books_catalog.views import genres_view, authors_view, books_view, upload, genre_new, genre_delete, \
    books_view_genre, validate, book_view, book_download, cover_view, scan_stop, scan_start, scan_info, \
    books_view_author, tg_list, tg_history

urlpatterns = [
                  path("", RedirectView.as_view(url='genres')),
                  path("genres/", genres_view, name='genres'),
                  path("genres/new", genre_new, name='genre_new'),
                  path("genre/<int:genre_id>/", books_view_genre, name="books_by_genre"),
                  path("genres/<int:genre_id>/delete", genre_delete, name='genre_delete'),
                  path("authors/", authors_view, name='authors'),
                  path("authors/<int:author_id>/", books_view_author, name='books_by_author'),

                  path("books/", books_view, name="books"),
                  path("book/<int:book_id>", book_view, name="book"),
                  path("book/<int:book_id>/download", book_download, name="book_download"),
                  path("books/upload", upload, name="upload"),
                  path("books/validate", validate, name="validate"),

                  path("scan/start", scan_start, name="scan_start"),
                  path("scan/stop", scan_stop, name="scan_stop"),
                  path("scan/status", scan_info, name="scan_info"),

                  path("tguser/list", tg_list, name="tg_list"),
                  path("tguser/history", tg_history, name="tg_history"),

                  path("cover/<int:cover_id>", cover_view, name="cover"),
              ] + static(settings.STATIC_URL, document_root=BASE_DIR / "books_catalog/static")
