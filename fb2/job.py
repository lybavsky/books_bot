import threading


class FB2JobFactory:
    counter = 0
    counter_lock = threading.Lock()

    def get(self, path, archive_path="", archive_path_conv="", fb2_str=""):
        with self.counter_lock:
            id = self.counter
            self.counter += 1
        return FB2Job(id, path, archive_path, archive_path_conv, fb2_str)


class FB2Job:
    def __init__(self, id, path, archive_path="", archive_path_conv="", fb2_str=""):
        self.id = id
        self.path = path
        self.archive_path = archive_path
        self.archive_path_conv = archive_path_conv
        self.fb2_str = fb2_str

    def get_str(self):
        return self.fb2_str

    def get_path(self):
        return self.path

    def info(self):
        if self.archive_path != "":
            return self.path + " -> " + self.archive_path
        else:
            return self.path