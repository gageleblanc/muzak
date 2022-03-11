from pathlib import Path
import os
from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.logging import Logging
from datetime import datetime
import muzak
from muzak import Muzak
from clilib.builders.app import EasyCLI


def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


class MuzakCLI:
    """
    Scan a directory to locate and organize audio files based on tags.
    """
    def __init__(self, debug: bool = False):
        """
        :param debug: Add additional debugging output
        """
        self.logger = Logging("Muzak", "cli").get_logger()
        self.debug = debug
        self.muzak: Muzak = None

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

    class Config:
        """
        Manage muzak configuration
        """
        def __init__(self, config_path: str = None):
            """
            :param config_path: Configuration file to use. Default is ~/.config/muzak/config.json
            """
            self.logger = Logging("Muzak", "Config").get_logger()
            if config_path is None:
                config_path = str(Path.home().joinpath(".config").joinpath("muzak").joinpath("config.json"))
            self.config = JSONConfigurationFile(config_path, muzak.config_schema, auto_create=muzak.default_config)

        def set(self, path: str, value: str):
            """
            Set config value
            :param path: Config path to set
            :param value: Value to set
            """
            if value == "None" or value == "null":
                value = None
            self.config[path] = value
            self.config.write()
            self.logger.info("Config updated!")

        def get(self, path: str):
            """
            Print value from config
            :param path: Config path to get
            """
            print(self.config[path])

    def validate_cache(self):
        """
        Validate saved muzak cache and remove missing files
        """
        self.muzak.validate_cache()

    def scan(self, path: str):
        """
        Scan given path and cache results for later
        """
        self.muzak = Muzak(debug=self.debug)
        self.logger.info("Starting Muzak scanner...")
        start_time = datetime.now()
        self.muzak.scan_path(path)
        end_time = (datetime.now() - start_time)
        self.logger.info("Muzak scanner completed in %s" % strfdelta(end_time, "{hours}:{minutes}:{seconds}"))

    def cleanup_dir(self, path: str):
        """
        Cleanup empty directories in the given path. This is best used after using the organize-cache command.
        :param path: Path to cleanup
        """
        self.logger.info("Cleaning up target directory: %s" % path)
        self._cleanup_dir(path)

    def organize_cache(self, destination: str, move: bool = False, cleanup_empty: bool = False, dry_run: bool = False):
        """
        Use cache to organize music in the given destination directory.
        :param destination: Destination path for organized music
        :param move: Move files to destination instead of copying
        :param cleanup_empty: Cleanup empty directories after organize operation. This is most useful when moving files.
        :param dry_run: Simulate organize operation without actually copying or moving files.
        """
        self.muzak = Muzak(debug=self.debug)
        self.logger.info("Starting Muzak organizer...")
        start_time = datetime.now()
        self.muzak.organize(destination, move, cleanup_empty, dry_run)
        end_time = (datetime.now() - start_time)
        self.logger.info("Muzak organizer completed in %s" % strfdelta(end_time, "{hours}:{minutes}:{seconds}"))

    def organize(self, path: str, destination: str, move: bool = False, cleanup_empty: bool = False, dry_run: bool = False):
        """
        Scan given path for music files, and then organize them in the given destination directory.
        :param path: Path to scan for music
        :param destination: Destination path for organized music
        :param move: Move files to destination instead of copying
        :param cleanup_empty: Cleanup empty directories after organize operation. This is most useful when moving files.
        :param dry_run: Simulate organize operation without actually copying or moving files.
        """
        self.muzak = Muzak(debug=self.debug)
        self.logger.info("Starting Muzak organizer...")
        start_time = datetime.now()
        # muzak = Muzak(debug=self.debug)
        self.muzak.scan_path(path)
        self.muzak.organize(destination, move, cleanup_empty, dry_run)
        end_time = (datetime.now() - start_time)
        self.logger.info("Muzak organizer completed in %s" % strfdelta(end_time, "{hours}:{minutes}:{seconds}"))


def cli():
    EasyCLI(MuzakCLI, enable_logging=True, debug=True)
