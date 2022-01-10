import threading
from threading import Thread, Event

from books_catalog.models import Book


class Status(object):
    __instance = None

    thread: Thread = None
    event: Event = None

    dblock: threading.Lock = None

    # -1 - не запущена/успех?
    # -2 - не запущена/ошибка
    # 0 - запущена, количество обработанных книг
    scan_status: int = -1
    scan_error: str = ""
    scan_processed: int = 0

    books_all = 0

    def __init__(self):
        if not Status.__instance:
            print(" __init__ method called..")
            self.dblock = threading.Lock()
            self.setScanStatus(-1)
            self.scan_processed = Book.objects.count()
        else:
            print("Instance already created:", self.getInstance())

    def startScan(self, f):
        self.setScanProcessed(0)
        self.setBooksAll(0)
        self.setScanStatus(0)
        self.event = Event()
        self.event.clear()
        self.thread = threading.Thread(name="scaner", target=f, args=(self.event,))
        self.thread.start()

    def stopScan(self):
        if self.event != None:
            self.event.set()
        self.event = None
        if self.thread != None:
            self.thread.join()
        self.thread = None

        self.setScanStatus(-1)

    def isActive(self):
        return self.thread != None

    def setScanStatus(self, status):
        self.scan_status = status

    def setScanError(self, err):
        self.scan_error = err
        self.scan_status = -2

    def setScanProcessed(self, processed):
        self.scan_processed = processed

    def setBooksAll(self, all):
        self.books_all = all

    def getScanInfo(self):
        return {
            "status": self.scan_status,
            "processed": self.scan_processed,
            "books_all": self.books_all,
            "erro": self.scan_error
        }
        self.scan_status = status

    def getScanStatus(self):
        return self.scan_status

    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            cls.__instance = Status()
        return cls.__instance
