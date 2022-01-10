import os
import shutil
from datetime import datetime

from django.core.management import BaseCommand

from books.settings import COVERS_DIR
from fb2.tools import clear_db


class Command(BaseCommand):
    help = 'Drop all'

    def handle(self, *args, **options):
        print("start to drop all")

        #Удалим все в базе данных
        clear_db()

        #Удалим все файлы в директории с обложками
        for ch in os.listdir(COVERS_DIR):
            print("Will delete cover path "+ch)
            shutil.rmtree(COVERS_DIR+"/"+ch)
