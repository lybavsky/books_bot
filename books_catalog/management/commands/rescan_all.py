
from django.core.management import BaseCommand

from fb2.scaner import rescan


class Command(BaseCommand):
    help = 'Rescan all'

    def handle(self, *args, **options):
        print("start to scan books")

        #Удалим все в базе данных
        rescan()

