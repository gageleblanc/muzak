import zerorpc
from muzak import Muzak
from muzak.drivers import MuzakStorageDriver


class MuzakRPC(object):
    def __init__(self, muzak_controller: Muzak, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.muzak = muzak_controller
        self.storage_driver: MuzakStorageDriver = self.muzak.storage_driver(self.muzak.storage_dir, self.muzak.config, debug=self.muzak.debug)

    def all_music(self):
        return self.storage_driver.music.values()[0]