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


__version__ = "0.5.5"


default_config = {
    "output_format": "<artist>/<album>/<title>", 
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


class Muzak:
    def __init__(self, scan_cache: str = None, debug: bool = False, cached: bool = False, driver: str = None) -> None:
        if scan_cache is None:
            scan_cache = ".muzakscan"
        self._cache_path = scan_cache
        self._scanned_paths = []
        self.debug = debug
        self.logger = Logging("Muzak", debug=debug).get_logger()
        self.config = self._load_config()
        driver = self.config["storage_driver"]
        if driver is None:
            driver = "muzak.drivers:MuzakStorageDriver"
        self._storage_driver = self._load_storage_driver(driver)
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

    def _load_config(self) -> JSONConfigurationFile:
        config_path = Path.home().joinpath(".config").joinpath("muzak").joinpath("config.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        return JSONConfigurationFile(str(config_path), schema=config_schema, auto_create=default_config)

    def _load_file(self, path: str):
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
            self.logger.warn("Skipping file: [%s] (this is probably not a music file)" % path)
        except UnicodeEncodeError:
            self.logger.warn("Encountered UnicodeEncodeError on file: [%s], skipping..." % path)
            self._failed_scans.append(path)

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

    def scan_path(self, path: str):
        self.logger.info("Scanning path: [%s]" % path)
        self._scanned_paths.append(path)
        self.files.extend(self._find_files(path))
        self.find_music()
        self._update_cache()
        self.logger.info("Found %d tracks out of %d total scanned files" % (len(self.music.keys()), len(self.files)))

    def find_music(self):
        for item in self.files:
            if item in self.music:
                self.logger.info("Skipping item [%s] since we have it cached." % item)
                continue
            tag_dict = self._load_file(item)
            if tag_dict is not None:
                self.logger.info("Found track: %s" % tag_dict)
                self.music[item] = tag_dict
            else:
                self.logger.warn("Skipping file [%s] due to loading error" % item)

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
        storage_driver = self._storage_driver(destination, self.config, debug=self.debug)
        self.logger.info("Found %d tracks out of %d total scanned files" % before_tracks)
        # Create destination if not exists.
        destination = Path(destination)
        if not destination.exists():
            destination.mkdir(parents=True)

        for item, tag in self.music.copy().items():
            # Gracefully fail this iteration if file has been moved/deleted/something else
            try:
                storage_driver.store_file(item, tag, move=move, dry_run=dry_run)
            except FileNotFoundError:
                del self.music[item]
                self.logger.warn("File: %s not found, skipping ... " % item)
                continue
            # item_path = Path(item)
            # if not item_path.exists():
            #     self.logger.warn("File [%s] no longer exists. Skipping..." % item)
            #     continue
            
            # new_filename = destination.joinpath("%s%s" % (self._filename_from_tag(tag), item_path.suffix))
            # parent_dir = Path(new_filename).parent
            # if not dry_run:
            #     if not parent_dir.exists():
            #         parent_dir.mkdir(parents=True)
            # if move:
            #     self.logger.info("Moving [%s] => [%s]" % (item, new_filename))
            #     if not dry_run:
            #         shutil.copy(item, str(new_filename))
            #         os.unlink(item)
            # else:
            #     self.logger.info("Copying [%s] => [%s]" % (item, new_filename))
            #     if not dry_run:
            #         shutil.copy(item, str(new_filename))
        if not dry_run:
            self.validate_cache()
        if cleanup_empty:
            for path in self._scanned_paths:
                self._cleanup_dir(path)
        self.logger.info("Failed to load files: %s" % (self._failed_scans))
        self.logger.info("Found %d tracks out of %d total scanned files" % before_tracks)
