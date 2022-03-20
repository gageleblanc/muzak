from pathlib import Path
import os
import json
from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.logging import Logging
from datetime import datetime
import muzak
from muzak import Muzak
from clilib.builders.app import EasyCLI
from tabulate import tabulate
from muzak.drivers import MuzakQueryResult, MuzakStorageDriver
from muzak.drivers.errors import MQLError

if not os.name == 'nt':
    import readline
# # This is specifically for windows, shouldn't matter because of conhost (maybe?)
# try:
#   import readline
# except ImportError:
#   pass

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

    class Operator:
        """
        Manage Muzak administration
        """
        def __init__(self, config_path: str = None, debug: bool = False):
            """
            :param config_path: Configuration file to use. Default is ~/.config/muzak/config.json
            """
            self.debug = debug
            self.logger = Logging("Muzak", "Operator", debug=debug).get_logger()
            if config_path is None:
                config_path = str(Path.home().joinpath(".config").joinpath("muzak").joinpath("config.json"))
            self.config = JSONConfigurationFile(config_path, muzak.config_schema, auto_create=muzak.default_config)

        def rescan_storage(self, full_scan: bool = False):
            """
            Rescan configured storage directory for newly added music
            """
            muzak = Muzak(debug=self.debug)
            storage_driver = muzak.storage_driver(muzak.storage_dir, muzak.config, debug=self.debug)
            if not full_scan:
                muzak.music = storage_driver.music
            muzak.scan_path(storage_driver.storage_path, update_cache=False)
            storage_driver.music = muzak.music
            storage_driver.update_cache()
            
        def reindex_metadata(self):
            """
            Re-index storage metadata such as available labels and track count
            """
            muzak = Muzak(debug=self.debug)
            storage_driver: MuzakStorageDriver = muzak.storage_driver(muzak.storage_dir, muzak.config, debug=self.debug)
            storage_driver.reindex_metadata()

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
        self.muzak = Muzak(debug=self.debug)
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

    def _query_printer(self, result: MuzakQueryResult) -> MuzakQueryResult:
        if len(result.result_set) > 0:
            if result.query.command == "show":
                # build stupid table structure
                res = result.result_set[0]
                tbl = []
                if isinstance(res, list):
                    for x in res:
                        tbl.append([x])
                else:
                    tbl.append([res])
                table = tabulate(tbl, [result.query.subject[0]], tablefmt="grid")
            else:
                headers = result.result_set[0]["tag"].keys()
                values = [x["tag"].values() for x in result.result_set]
                table = tabulate(values, headers, tablefmt="grid")
            print(table)
        print("%d records returned" % len(result.result_set))
        print("%d records changed" % result.changed_records)

    def _query_wrapper(self, query: str, storage_driver: MuzakStorageDriver, output_json: bool = False, quiet: bool = False):
        try:
            start_time = datetime.now()
            result: MuzakQueryResult = storage_driver.mql.execute(query)
            end_time = (datetime.now() - start_time)
            if not output_json:
                if not quiet:
                    self._query_printer(result)
                print("Query executed in %s seconds" % str(round(end_time.total_seconds(), 4)))
            else:
                print(json.dumps(result.result_set))
        except MQLError as e:
            print("%s: %s" % (e.__class__.__name__, e))

    def query(self, query: str = None, output_json: bool = False, quiet: bool = False):
        """
        Search for tracks based on query and return list
        :param query: Query to run against Muzak storage
        :param output_json: Output only json
        :param quiet: Don't print table
        """
        self.muzak = Muzak(debug=self.debug)
        storage_driver = self.muzak.storage_driver(self.muzak.storage_dir, self.muzak.config, debug=self.debug)
        if query is None:
            print("Muzak interactive query prompt")
            print("Muzak version %s" % muzak.__version__)
            while True:
                try:
                    user_query = input("\r\nMuzakQL> ")
                except (KeyboardInterrupt, EOFError):
                    print("exit")
                    break
                if user_query.strip().lower() == "exit":
                    break
                if user_query.startswith("\\"):
                    if user_query[1:] == "quiet":
                        quiet = not quiet
                        print("quiet = %s" % quiet)
                    elif user_query[1:] == "output_json":
                        output_json = not output_json
                        print("output_json = %s" % output_json)
                    else:
                        print("Invalid command: %s" % user_query)
                    continue
                self._query_wrapper(user_query, storage_driver, output_json, quiet)
        else:
            self._query_wrapper(query, storage_driver, output_json, quiet)

    def organize_cache(self, destination: str = None, move: bool = False, cleanup_empty: bool = False, dry_run: bool = False):
        """
        Use cache to organize music in the given destination directory.
        :param destination: Destination path for organized music
        :param move: Move files to destination instead of copying
        :param cleanup_empty: Cleanup empty directories after organize operation. This is most useful when moving files.
        :param dry_run: Simulate organize operation without actually copying or moving files.
        """
        self.muzak = Muzak(debug=self.debug)
        self.logger.info("Starting Muzak organizer...")
        if destination is None:
            destination = self.muzak.config["storage_directory"]
        start_time = datetime.now()
        self.muzak.organize(destination, move, cleanup_empty, dry_run)
        end_time = (datetime.now() - start_time)
        self.logger.info("Muzak organizer completed in %s" % strfdelta(end_time, "{hours}:{minutes}:{seconds}"))

    def organize(self, path: str, destination: str = None, move: bool = False, cleanup_empty: bool = False, dry_run: bool = False):
        """
        Scan given path for music files, and then organize them in the given destination directory.
        :param path: Path to scan for music
        :param destination: Destination path for organized music. Default is your configured storage_directory.
        :param move: Move files to destination instead of copying
        :param cleanup_empty: Cleanup empty directories after organize operation. This is most useful when moving files.
        :param dry_run: Simulate organize operation without actually copying or moving files.
        """
        self.muzak = Muzak(debug=self.debug)
        self.logger.info("Starting Muzak organizer...")
        if destination is None:
            destination = self.muzak.config["storage_directory"]
        start_time = datetime.now()
        # muzak = Muzak(debug=self.debug)
        self.muzak.scan_path(path)
        self.muzak.organize(destination, move, cleanup_empty, dry_run)
        end_time = (datetime.now() - start_time)
        self.logger.info("Muzak organizer completed in %s" % strfdelta(end_time, "{hours}:{minutes}:{seconds}"))


def cli():
    EasyCLI(MuzakCLI, enable_logging=True, debug=True)
