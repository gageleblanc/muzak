import json
import re
import os
import shutil
from pathlib import Path
# from django.test import tag
# from tinytag import TinyTag, TinyTagException
# import eyed3
import taglib
import importlib
from clilib.util.logging import Logging
from clilib.config.config_loader import JSONConfigurationFile

from muzak.drivers import MuzakStorageDriver


__version__ = "0.8.3"


default_config = {
    "output_format": "<artist>/<album>/<title>",
    "storage_directory": "",
    "default_tags": {
        "album": "Unknown",
        "albumartist": "Various Artists",
        "artist": "Various Artists",
        "bitrate": "0 kBits/s",
        "comment": "None",
        "composer": "Unknown",
        "disc": "0",
        "disc_total": "0",
        "duration": "0",
        "filesize": "0",
        "genre": "Unknown",
        "samplerate": "0",
        "title": "Unknown",
        "track": "0",
        "track_total": "0",
        "year": "Unknown"
    }
}

config_schema = {
    "output_format": str,
    "storage_directory": str,
    "default_tags": {
        "album": str,
        "albumartist": str,
        "artist": str,
        "bitrate": str,
        "comment": str,
        "composer": str,
        "disc": str,
        "disc_total": str,
        "duration": str,
        "filesize": str,
        "genre": str,
        "samplerate": str,
        "title": str,
        "track": str,
        "track_total": str,
        "year": str
    }
}

def load_file(path: str):
    logger = Logging("Muzak", "FileLoader").get_logger()
    try:
        music_file = taglib.File(path)
        tag_dict = {}
        for tag, value in music_file.tags.items():
            if isinstance(value, list):
                if len(value) > 0:
                    value = value[0]
            else:
                value = None
            tag_lower = tag.lower()
            tag_dict[tag_lower] = value
        return tag_dict
    except OSError:
        logger.warn("Skipping file: [%s] (this is probably not a music file)" % path)
    except UnicodeEncodeError:
        logger.warn("Encountered UnicodeEncodeError on file: [%s], skipping..." % path)


class Muzak:
    def __init__(self, scan_cache: str = None, debug: bool = False, cached: bool = False, driver: str = None) -> None:
        if scan_cache is None:
            scan_cache = str(Path.home().joinpath(".config").joinpath("muzak").joinpath(".muzakscan"))
        self._cache_path = scan_cache
        self._scanned_paths = []
        self.debug = debug
        self.logger = Logging("Muzak", debug=debug).get_logger()
        self.config = self._load_config()
        driver = self.config["storage_driver"]
        if driver is None:
            driver = "muzak.drivers:MuzakStorageDriver"
        storage_dir = self.config["storage_directory"]
        if len(storage_dir) == 0:
            storage_dir = Path.home().joinpath(".muzak").joinpath("storage")
            if not storage_dir.exists():
                storage_dir.mkdir(parents=True, exist_ok=True)
        else:
            storage_dir = Path(storage_dir)
            if not storage_dir.exists():
                storage_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir = str(storage_dir)
        self.storage_driver = self._load_storage_driver(driver)
        self.files = []
        self.music = {}
        self._failed_scans = []
        self._load_cache()

    def _load_storage_driver(self, storage_driver_path: str) -> MuzakStorageDriver:
        driver_path_parts = storage_driver_path.split(":", 1)
        if len(driver_path_parts) < 2:
            raise AttributeError("Given module path: %s is not valid. Please supply module path in the following format: path.to.module:ClassName")
        module_path = driver_path_parts[0]
        class_name = driver_path_parts[1]
        module = importlib.import_module(module_path)
        if not hasattr(module, class_name):
            raise ImportError("Storage driver class: [%s] does not exist in module [%s]" % (class_name, module_path))
        StorageDriver = getattr(module, class_name)
        if not issubclass(StorageDriver, MuzakStorageDriver):
            raise TypeError("Imported class [%s] is not a subclass of MuzakStorageDriver." % StorageDriver.__name__)
        return StorageDriver

    def _load_config(self) -> JSONConfigurationFile:
        config_path = Path.home().joinpath(".config").joinpath("muzak").joinpath("config.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return JSONConfigurationFile(str(config_path), schema=config_schema, auto_create=default_config)

    def _cleanup_dir(self, path: str):
        if not os.path.isdir(path):
            return
        files = os.listdir(path)
        for f in files:
            full_path = os.path.join(path, f)
            if os.path.isdir(full_path):
                self._cleanup_dir(full_path)
        
        files = os.listdir(path)
        if len(files) == 0:
            self.logger.info("Removing empty directory: [%s]" % path)
            os.rmdir(path)
        
    def _find_files(self, path: str):
        self.logger.info("Searching in path: %s" % path)
        files = []
        scan_path = Path(path)
        listing = os.listdir(path)
        for item in listing:
            item_path = scan_path.joinpath(item)
            if item_path.is_dir():
                self.logger.info("Found directory: %s" % item_path)
                l = self._find_files(str(item_path))
                for f in l:
                    self.logger.info("Found file %s in %s" % (f, item_path))
                files.extend(l)
            elif item_path.is_file():
                self.logger.info("Found file: %s" % item_path)
                files.append(str(item_path))
            else:
                self.logger.info("Item %s is not file or dir" % item)
        return files

    def _parse_query_string(self, query_str: str, _and: bool = False):
        """
        Parse query string 
        """
        query_parts = query_str.split(";")
        query_definition = {}
        for part in query_parts:
            if "=" not in part:
                raise AttributeError("Query String: [%s] is invalid near [%s]" % (query_str, part))
            key, value = part.split("=", 1)
            if _and:
                query_definition[key] = value
            else:
                if key not in query_definition:
                    query_definition[key] = [value]    
                else:
                    query_definition[key].append(value)
        return query_definition

    def _load_cache(self):
        cache_data = {"files": [], "music": {}}
        if Path(self._cache_path).exists():
            with open(self._cache_path) as f:
                cache_data = json.load(f)
        
        cache_files = cache_data.get("files", [])
        cache_music = cache_data.get("music", {})
        self.files.extend(cache_files)
        self.files = list(set(self.files))
        cache_music.update(self.music)
        self.music = cache_music

    def _update_cache(self):
        self.logger.info("Writing cache: %s" % self._cache_path)
        self.files = list(set(self.files))
        cache = {"files": self.files, "music": self.music}
        if Path(self._cache_path).exists():
            os.unlink(self._cache_path)
        with open(self._cache_path, "w") as f:
            json.dump(cache, f)

    def validate_cache(self):
        self.logger.info("Validating cache ...")
        self._load_cache()
        for item in self.files.copy():
            if not Path(item).exists():
                self.logger.info("File [%s] does not exist, removing from cache." % item)
                self.files.remove(item)
                if item in self.music:
                    del self.music[item]
        self._update_cache()

    def scan_path(self, path: str, update_cache: bool = True):
        self.logger.info("Scanning path: [%s]" % path)
        self._scanned_paths.append(path)
        self.files.extend(self._find_files(path))
        self.find_music()
        if update_cache:
            self._update_cache()
        self.logger.info("Found %d tracks out of %d total scanned files" % (len(self.music.keys()), len(self.files)))

    def query(self, query_str: str, limit: int = 0):
        """
        Query Muzak cache and return matching tracks
        :param query_str: String to use for track query. Format should be <tag>=<expected_value>[;<tag>=<expected_value> ...]
        :param limit: Limit result set
        """
        storage_driver: MuzakStorageDriver = self.storage_driver(self.storage_dir, self.config, debug=self.debug)
        result = storage_driver.mql.execute(query_str, limit)
        return result

    def find_music(self):
        for item in self.files:
            if item in self.music:
                self.logger.info("Skipping item [%s] since we have it cached." % item)
                continue
            tag_dict = load_file(item)
            if tag_dict is not None:
                self.logger.info("Found track: %s" % tag_dict)
                self.music[item] = tag_dict
            else:
                self.logger.warn("Skipping file [%s] due to loading error" % item)
                self._failed_scans.append(item)

    def organize(self, destination: str, move: bool = True, cleanup_empty: bool = False, dry_run: bool = False):
        """
        Organize detected music files in the given destination folder. Optionally cleanup
        empty directories afterwards.
        :param destination: Destination directory for organized music.
        :param move: Move files to destination instead of copying. Default is true.
        :param cleanup_empty: Cleanup empty directories after music has been organized. This is false by default.
        """
        before_tracks = (len(self.music.keys()), len(self.files))
        self.logger.info("Initializing storage driver ...")
        storage_driver: MuzakStorageDriver = self.storage_driver(destination, self.config, debug=self.debug)
        self.logger.info("Found %d tracks out of %d total scanned files" % before_tracks)
        # Create destination if not exists.
        destination = Path(destination)
        if not destination.exists():
            destination.mkdir(parents=True)

        for item, tag in self.music.copy().items():
            # Gracefully fail this iteration if file has been moved/deleted/something else
            try:
                storage_driver.store_file(item, tag, move=move, dry_run=dry_run, update_cache=False)
            except FileNotFoundError:
                del self.music[item]
                self.logger.warn("File: %s not found, skipping ... " % item)
                continue
        if not dry_run:
            storage_driver.update_cache()
            self.validate_cache()
        if cleanup_empty:
            for path in self._scanned_paths:
                self._cleanup_dir(path)
        self.logger.info("Failed to load files: %s" % (self._failed_scans))
        self.logger.info("Found %d tracks out of %d total scanned files" % before_tracks)
