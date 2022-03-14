from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.logging import Logging
from pathlib import Path
import shutil
import json
import re
import os
from muzak.drivers.errors import MQLError, MQLSyntaxError


class MuzakStorageDriver:
    def __init__(self, storage_path: str, muzak_config: JSONConfigurationFile, debug: bool = False):
        self.storage_path = storage_path
        self._cache_path = str(Path(storage_path).joinpath(".muzakstorage"))
        self.debug = debug
        self.config = muzak_config
        self.logger = Logging("Muzak", "StorageDriver", debug=debug).get_logger()
        self.music = {}
        self._load_cache()
        self.mql = MuzakQL(self)

    def _load_cache(self):
        cache_data = {}
        if Path(self._cache_path).exists():
            with open(self._cache_path) as f:
                cache_data = json.load(f)
        
        self.music = cache_data

    def update_cache(self):
        self.logger.info("Writing cache: %s" % self._cache_path)
        if Path(self._cache_path).exists():
            os.unlink(self._cache_path)
        with open(self._cache_path, "w") as f:
            json.dump(self.music, f)

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

    # def rescan_storage(self):
    #     m = Muzak(debug=self.debug)
    #     m.scan_path(self.storage_path)
    #     m.validate_cache()
    #     self.music = m.music
    #     self._update_cache()

    def store_file(self, file_path: str, file_data: dict, move: bool = False, dry_run: bool = False, update_cache: bool = True):
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
        if update_cache and not dry_run:
            self.music[str(destination_path)] = file_data
            self.update_cache()

    def remove_file(self, file_path: str, cached: bool = False, dry_run: bool = False, update_cache: bool = True):
        if file_path in self.music:
            self.logger.info("Removing file [%s] from Muzak storage ..." % file_path)
            if not dry_run:
                del self.music[file_path]

            if not cached:
                if Path(file_path).exists():
                    self.logger.info("Removing file [%s] from filesystem ..." % file_path)
                    if not dry_run:
                        os.unlink(file_path)
                else:
                    self.logger.warn("File already doesn't exist, so skipping removal.")
            else:
                self.logger.info("Cached set to true, so leaving file on disk.")
            if update_cache:
                self.update_cache()
        else:
            self.logger.warn("File [%s] is not managed by Muzak, leaving it alone ...")
            return

    def remove_files(self, files: list, cached: bool = False, dry_run: bool = False):
        for f in files:
            self.remove_file(f, cached, dry_run, update_cache=False)
        self.update_cache()

    def store_files(self, files: dict, move: bool = False, dry_run: bool = False):
        for item, tag in files.items():
            self.store_file(item, tag, move, dry_run, update_cache=False)
        self.update_cache()


class MuzakQuery:
    def __init__(self, query_str: str):
        self.raw = query_str
        parsed = self._parse_query_string(query_str)
        self.command = parsed[0]
        self.subject = parsed[1]
        self.any = parsed[2]

    def __str__(self):
        return self.raw

    def _parse_query_string(self, query_str: str):
        """
        Parse query string 
        """
        _any = True
        if (query_str.startswith("[") and not query_str.endswith("]")) or (query_str.endswith("]") and not query_str.startswith("[")):
            raise MQLSyntaxError("Unterminated grouping brackets in query: %s" % query_str)
        if query_str.startswith("[") and query_str.endswith("]"):
            _any = False
            query_str = query_str[1:-1]
        query_command, query_str = query_str.split(" ", 1)
        query_parts = query_str.split(";")
        query_definition = {}
        for part in query_parts:
            if "=" not in part:
                raise AttributeError("Query String: [%s] is invalid near [%s]" % (query_str, part))
            key, value = part.split("=", 1)
            if not _any:
                query_definition[key] = value
            else:
                if key not in query_definition:
                    query_definition[key] = [value]    
                else:
                    query_definition[key].append(value)
        return query_command, query_definition, _any


class MuzakQueryResult:
    def __init__(self, query: MuzakQuery, result_set: list, changed: list):
        self.query = query
        self.result_set = result_set
        self.changed_records = len(changed)
        self.changed_set = changed


class MuzakQL:
    def __init__(self, storage_driver: MuzakStorageDriver):
        self._storage_driver = storage_driver
        self._storage_cache = storage_driver.music
        self.config = storage_driver.config
        self.debug = storage_driver.debug
        self.methods = {
            "select": self._select_query,
            "delete": self._delete_query
        }

    def _delete_query(self, query: MuzakQuery, limit: int = 0):
        results = self._select_query(query, limit)
        files = []
        for result in results.result_set:
            files.append(result["file_path"])
        self._storage_driver.remove_files(files)
        return MuzakQueryResult(query, results.result_set, results.result_set)

    def _select_query(self, query: MuzakQuery, limit: int = 0):
        results = []
        it = 1
        for path, tag in self._storage_cache.items():
            if not query.any:
                if query.subject.items() <= tag.items():
                    results.append({"file_path": path, "tag": tag})
            else:
                for item, value in query.subject.items():
                    if item in tag:
                        if tag[item] in value:
                            result = {"file_path": path, "tag": tag}
                            if result not in results:
                                results.append(result)
            if limit > 0:
                if it == limit:
                    break
            ++it
        return MuzakQueryResult(query, results, [])

    def execute(self, query_str: str, limit: int = 0):
        """
        Query Muzak cache and return matching tracks
        :param query_str: String to use for track query. Format should be <tag>=<expected_value>[;<tag>=<expected_value> ...]
        :param limit: Limit result set
        """
        query: MuzakQuery = MuzakQuery(query_str)
        if query.command.lower() in self.methods:
            return self.methods[query.command.lower()](query, limit)
        else:
            raise MQLError("MQL Command [%s] does not exist ..." % query.command)