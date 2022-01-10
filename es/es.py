from datetime import datetime

from elasticsearch._async import helpers
from elasticsearch.client import Elasticsearch

from books.settings import ES_HOST, CONFIG_NAME_ES_INDEX, ES_BATCH_SIZE
from books_catalog.models import Config


class ESClient(object):
    address = ES_HOST
    es: Elasticsearch = None
    index = ""

    __instance = None

    def __init__(self, address=ES_HOST):
        if not ESClient.__instance:
            print(" __init__ method called..")
            self.address = address
            self.es = Elasticsearch(hosts=ES_HOST)
            self.getElasticIndex()
        else:
            print("Instance already created:", self.getInstance())

    @classmethod
    def getInstance(cls):
        if not cls.__instance:
            cls.__instance = ESClient()
        return cls.__instance

    def getES(self):
        return self.es

    def addDocument(self, document):
        self.es.index(index=self.index, body={
            "genres": document["genres"],
            "first_name": document["first_name"],
            "last_name": document["last_name"],
            "title": document["title"],
            "annotation": document["annotation"],
            "@timestamp": datetime.utcnow(),

        }, id=document["id"])

    def deleteDocument(self, book_id):
        self.es.delete(index=self.index, id=book_id)

    def addDocuments(self, results):
        if len(results) >= ES_BATCH_SIZE:
            es_res = helpers.bulk(self.es, self.es_bulk(results, self.es_index))

            if es_res[0] != len(results):
                self.log.info("errors while put to es: " + str(es_res[1]))

    def setBulk(self, results, index_name):
        for res in results:
            yield {
                "_index": index_name,
                "genres": res["genres"],
                "first_name": res["first_name"],
                "last_name": res["last_name"],
                "title": res["title"],
                "annotation": res["annotation"],
                "@timestamp": datetime.utcnow(),
                "_id": res["id"],
            }

    def getElasticIndex(self):
        if self.index == "":
            try:
                es_index_conf = Config.objects.filter(name=CONFIG_NAME_ES_INDEX).get()
            except Config.DoesNotExist:
                es_index_conf = Config(name=CONFIG_NAME_ES_INDEX, value=datetime.now().strftime("%d_%m-%Y_%H_%M_%S"))
                es_index_conf.save()
            self.index = es_index_conf.value

        return self.index

    def renewElasticIndex(self):
        es_index_conf = Config.objects.filter(name=CONFIG_NAME_ES_INDEX).get()
        es_index_conf.value = datetime.now().strftime("%d_%m-%Y_%H_%M_%S")
        es_index_conf.save()
        self.index = es_index_conf.value
        return self.index

    def setElasticIndex(self, idx_name):
        try:
            es_index_conf = Config.objects.filter(name=CONFIG_NAME_ES_INDEX)
        except Config.DoesNotExist:
            es_index_conf = Config(name=CONFIG_NAME_ES_INDEX)

        self.index = idx_name
        es_index_conf.value = idx_name
        es_index_conf.save()
