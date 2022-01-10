import os
import queue
import logging
import shutil
import threading
import time
import zipfile
import zlib
from queue import Full
from threading import Thread, Event

from django.db import OperationalError
from elasticsearch import helpers

from glob import glob

from books.settings import MAX_QUEUE_FB2, MAX_QUEUE_ARCHIVE, MAX_QUEUE_RES, LOGGER_NAME, MAX_WORKERS_FB2, \
    MAX_WORKERS_ARCHIVE, ES_BATCH_SIZE, COVERS_DIR, BOOKS_DIR, COVERS_ENABLED

from es.es import ESClient
from fb2.job import FB2JobFactory
from fb2.parser import parse_fb2

from fb2.tools import save_book_to_db, clear_db, books_count

from fb2.status import Status

class FB2Parser:
    queue_fb2 = queue.Queue(maxsize=MAX_QUEUE_FB2)
    event_fb2 = threading.Event()

    queue_archive = queue.Queue(maxsize=MAX_QUEUE_ARCHIVE)
    event_archive = threading.Event()

    queue_res = queue.Queue(maxsize=MAX_QUEUE_RES)
    event_res = threading.Event()

    processed_counter = 0
    processed_lock = threading.Lock()

    def __init__(self, dirs, idx, save_covers, stop_event):
        """
        init class for FB2Parser

        :param dirs: array of directory paths
        :param idx: name of elasticsearch index
        :param save_covers: is covers save
        """

        self.event_fb2 = threading.Event()
        self.event_archive = threading.Event()
        self.event_res = threading.Event()

        Status.getInstance().setScanStatus(0)

        self.log = logging.getLogger(LOGGER_NAME)
        self.log.setLevel(logging.INFO)

        print("Start fb2 parser")
        self.dirs = dirs
        self.save_covers = save_covers

        self.fb2f = FB2JobFactory()

        self.es = ESClient.getInstance()

        self.es_index = self.es.getElasticIndex()

        self.es.es.indices.delete(index=self.es_index, ignore=[400, 404])

        Status.getInstance().setBooksAll(books_count(self.dirs))

        print("Starting result worker")
        Thread(target=self.res_worker, args=(0, self.queue_res, self.event_res, stop_event)).start()

        print("Starting show processed worker")
        Thread(target=self.show_processed, daemon=False, args=(self.event_res, stop_event)).start()

        fb2_workers = []
        for fb2_i in range(MAX_WORKERS_FB2):
            print("Starting fb2 worker " + str(fb2_i))
            fb2_thread = Thread(target=self.fb2_worker, args=(fb2_i, self.queue_fb2, self.event_fb2, stop_event))
            fb2_thread.start()
            fb2_workers.append(fb2_thread)

        for arch_i in range(MAX_WORKERS_ARCHIVE):
            print("Starting arch worker " + str(arch_i))
            arch_thread = Thread(target=self.archive_worker,
                                 args=(arch_i, self.queue_archive, self.event_archive, stop_event))
            arch_thread.start()



        for dir in self.dirs:
            print("Starting scan dir "+dir)
            self.parse_dir(dir, stop_event)

        for fb2_worker in fb2_workers:
            fb2_worker.join()

        print("Exit from main scaner thread")
        Status.getInstance().setScanStatus(-1)

    def show_processed(self, event, stop_event: Event):
        while not event.is_set():
            if stop_event.is_set():
                print("Stop processed worker by stop_event")
                return

            print("processed: " + str(self.processed_counter))
            Status.getInstance().setScanProcessed(self.processed_counter)
            time.sleep(5)

        print("Exit processed worker")
        return

    def fb2_worker(self, worker_id, in_queue, event, stop_event: Event):
        print("start fb2_worker #" + str(worker_id))

        while not event.is_set() or not in_queue.empty():
            if stop_event.is_set():
                print("exiting by stop_event fb2_worker #" + str(worker_id))
                self.event_res.set()
                return

            if in_queue.empty():
                time.sleep(1)
                continue

            fb2_job = in_queue.get()
            # print("fb2 worker #" + str(worker_id) + " got job " + fb2_job.info())
            try:
                fb2res = parse_fb2(fb2_job)
                # print(fb2res.get())
                # print("processed " + str(self.processed_counter))
                self.processed_inc()
                self.queue_res.put(fb2res)
            except Exception as e:
                # print(fb2_job)
                # print(fb2res)
                print("Error while parse " + fb2_job.info() + ": " + str(e))

        print("exiting fb2_worker #" + str(worker_id))
        self.event_res.set()

    def processed_inc(self):
        with self.processed_lock:
            self.processed_counter += 1

    def archive_worker(self, worker_id, in_queue, event, stop_event: Event):
        print("start archive_worker #" + str(worker_id))
        while not event.is_set() or not in_queue.empty():
            if stop_event.is_set():
                print("exiting by stop_event archive_worker #" + str(worker_id))
                self.event_fb2.set()
                return

            if in_queue.empty():
                time.sleep(1)
                continue

            archive_job = in_queue.get()
            # print("arch worker #" + str(worker_id) + " got job " + archive_job)
            if len(archive_job) > 4:
                if archive_job[-4:] == ".zip":
                    try:
                        zipf = zipfile.ZipFile(archive_job, "r")
                        for zipf_f in zipf.filelist:
                            if not zipf_f.filename.endswith(".fb2"):
                                continue
                            try:
                                fn_conv = zipf_f
                                try:
                                    fn_conv = zipf_f.filename.encode("cp437").decode("cp866")
                                except Exception as e:
                                    print("Can not convert archive filename: " + str(e))

                                job_str = zipf.read(zipf_f)
                                fb2job = self.fb2f.get(archive_job, zipf_f.filename, fn_conv, job_str)
                                self.queue_fb2.put(fb2job)
                            except zlib.error as e:
                                print("ERROR:" +
                                      "can not process archive " + zipf_f.filename + " in " + archive_job + " " + str(
                                    e))
                    except zipfile.BadZipFile as e:
                        print("Bad zip file " + archive_job + ": " + str(e))

        # Поскольку файлы не в архиве мы клали в очередь не в треде,
        # то, раз мы распарсили архивы, значит, можно выключать треды парсинга ивентов
        print("exiting archive_worker #" + str(worker_id))
        self.event_fb2.set()

    def res_worker(self, worker_id, in_queue, event, stop_event: Event):
        print("start result #" + str(worker_id))

        results_lock = threading.Lock()
        results = []
        while not event.is_set() or not in_queue.empty():
            if stop_event.is_set():
                print("exiting by stop_event es_worker #" + str(worker_id))
                return

            if in_queue.empty():
                time.sleep(1)
                continue

            fb2res = in_queue.get()

            tries = 0
            while tries < 5:
                try:
                    with L():
                        book_id = save_book_to_db(fb2res)
                        break
                except OperationalError as e:
                    print("Has error ", e)
                    tries += 1
                    if tries == 4:
                        stop_event.set()

            if book_id==-1:
                continue

            fb2res.set_id(book_id)

            results_lock.acquire()
            results.append(fb2res.get())
            results_lock.release()

            if len(results) >= ES_BATCH_SIZE:
                es_res = helpers.bulk(self.es.es, self.es_bulk(results, self.es_index))

                if es_res[0] != len(results):
                    print("errors while put to es: " + str(es_res[1]))

                results_lock.acquire()
                results = []
                results_lock.release()

        es_res = helpers.bulk(self.es.es, self.es_bulk(results, self.es_index))
        if es_res[0] != len(results):
            print("errors while put to es: " + str(es_res[1]))

        print("exiting es_worker #" + str(worker_id))

    def es_bulk(self, results, index_name):
        for res in results:
            yield {
                "_index": index_name,
                "genres": res["genres"],
                "first_name": res["first_name"],
                "last_name": res["last_name"],
                "title": res["title"],
                "annotation": res["annotation"],
                "_id": res["id"],
            }

    def parse_dir(self, dir, stop_event: Event):
        """
        Парсим директорию @dir и отдаем в воркеры найденные файлы
        """
        print("Will parse files in dir " + dir)

        fb2s = glob(dir + "/**/*.fb2", recursive=True)
        for fb2 in fb2s:
            ok = False
            while not ok:
                try:
                    self.queue_fb2.put(self.fb2f.get(path=fb2), timeout=5)
                    ok = True
                except Full:
                    if stop_event.is_set():
                        print("exiting by stop_event from parse_dir")
                        return

        zip_archs = glob(dir + "/**/*.zip", recursive=True)
        for zip_arch in zip_archs:
            ok = False
            while not ok:
                try:
                    self.queue_archive.put(zip_arch, timeout=5)
                    ok = True
                except Full:
                    if stop_event.is_set():
                        print("exiting by stop_event from parse_dir")
                        return

        # Как распарсили архивы, выключаем воркер архивов по ивенту
        self.event_archive.set()




def rescan(stop_event: Event):
    clear_db()
    # Удалим все файлы в директории с обложками
    for ch in os.listdir(COVERS_DIR):
        print("Will delete cover path " + ch)
        shutil.rmtree(COVERS_DIR + "/" + ch)

    FB2Parser([BOOKS_DIR], ESClient.getInstance().getElasticIndex(), COVERS_ENABLED, stop_event)


# Функция для блокировки
def L():
    return Status.getInstance().dblock
