from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.logging import Logging
from pathlib import Path
import shutil
import json
import re
import os


class MuzakStorageDriver:
    def __init__(self, storage_path: str, muzak_config: JSONConfigurationFile, debug: bool = False):
        self.storage_path = storage_path
        self._cache_path = str(Path(storage_path).joinpath(".muzakscan"))
        self.debug = debug
        self.config = muzak_config
        self.logger = Logging("Muzak", "StorageDriver", debug=debug).get_logger()

    def _file_not_found(self, file_path: str):
        raise FileNotFoundError("%s: file [%s] does not exist!" % (self.__class__.__name__, file_path))

    def _filename_from_tag(self, tag):
        fmt = self.config["output_format"]
        defaults = self.config["default_tags"]
        for item, value in tag.items():
            fmt_tag = "<%s>" % item
            if isinstance(value, str):
                value = value.replace("/", " ")
                value = value.replace("\\", " ")
                fmt_val = re.sub(r'[^\w.\d\(\)\&\s-]', '', str(value))
            else:
                fmt_val = re.sub(r'[^\w.\d\(\)\&\s-]', '', defaults.get(item, "Unknown"))
            fmt = fmt.replace(fmt_tag, fmt_val)
            fmt = " ".join(fmt.split())
        for tag, value in defaults.items():
            fmt_tag = "<%s>" % tag
            fmt = fmt.replace(fmt_tag, value)
        return fmt

    def store_file(self, file_path: str, file_data: dict, move: bool = False, dry_run: bool = False):
        if dry_run:
            self.logger.info("store_file - dry_run mode")
        file_path = Path(file_path)
        if not file_path.exists():
            self._file_not_found(file_path)

        file_extension = file_path.suffix
        destination_path = Path(self.storage_path).joinpath("%s%s" % (self._filename_from_tag(file_data), file_extension))
        destination_parent_path = destination_path.parent
        if not destination_parent_path.exists():
            self.logger.debug("Auto-creating parent path ...")
            destination_parent_path.mkdir(exist_ok=True, parents=True)

        tries = 3
        while True:
            try:
                if move:
                    self.logger.info("Moving [%s] => [%s]" % (str(file_path), destination_path))
                    if not dry_run:
                        shutil.copy(str(file_path), str(destination_path))
                        os.unlink(str(file_path))
                else:
                    self.logger.info("Copying [%s] => [%s]" % (str(file_path), destination_path))
                    if not dry_run:
                        shutil.copy(str(file_path), str(destination_path))
            except PermissionError:
                self.logger.warn("Encountered permission error, retrying (%d/3)" % tries)
                tries -= 1
                if tries:  # if tries != 0
                    continue  # not necessary, just for clarity
                else:
                    self.logger.warn("Skipping file [%s], permission error encountered. This can happen on cross-filesystem moves." % file_path)
                    return
            else:
                break


class MuzakQL:
    def __init__(self, storage_driver: MuzakStorageDriver, config: JSONConfigurationFile, debug: bool = False):
        self._storage_driver = storage_driver
        self.config = config
        self.debug = debug

    
