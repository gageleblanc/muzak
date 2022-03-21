from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.logging import Logging
from pathlib import Path
import shutil
import json
import re
import os
import taglib
from muzak.drivers.query import QueryParser
from muzak.drivers.errors import MQLError, MQLSyntaxError


metadata_schema = {
    "labels": list,
    "count": int
}

metadata_default = {
    "labels": [],
    "count": 0
}


class MuzakStorageDriver:
    def __init__(self, storage_path: str, muzak_config: JSONConfigurationFile, debug: bool = False):
        self.storage_path = storage_path
        self._cache_path = str(Path(storage_path).joinpath(".muzakstorage"))
        self.debug = debug
        self.config = muzak_config
        self.metadata = JSONConfigurationFile(os.path.join(storage_path, ".muzakmetadata"), schema=metadata_schema, auto_create=metadata_default)
        self.logger = Logging("Muzak", "StorageDriver", debug=debug).get_logger()
        self.music = {}
        self._load_cache()
        self.mql = MuzakQL(self, debug=debug)

    def _load_cache(self):
        cache_data = {}
        if Path(self._cache_path).exists():
            with open(self._cache_path) as f:
                cache_data = json.load(f)
        
        self.music = cache_data

    def update_cache(self):
        self.logger.debug("Writing cache: %s ..." % self._cache_path)
        if Path(self._cache_path).exists():
            os.unlink(self._cache_path)
        with open(self._cache_path, "w") as f:
            json.dump(self.music, f)
        self.logger.debug("Writing metadata ...")
        self.metadata.write()

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

    def reindex_metadata(self, update_cache: bool = True):
        self.logger.info("Re-indexing metadata for storage: [%s]" % self.storage_path)
        labels = []
        songs = self.music.values()
        songs_len = len(songs)
        self.logger.debug("%d songs known to Muzak" % songs_len)
        self.metadata["count"] = songs_len
        for tag in self.music.values():
            for label in tag.keys():
                if label not in labels:
                    self.logger.debug("Found label: [%s]" % label)
                    labels.append(label)
        self.metadata["labels"] = labels
        if update_cache:
            self.update_cache()

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
        if not dry_run:
            for label in file_data.keys():
                if not isinstance(self.metadata["labels"], list):
                    self.metadata["labels"] = []
                if label not in self.metadata["labels"]:
                    self.metadata["labels"].append(label)
            self.metadata["count"] += 1
            self.music[str(destination_path)] = file_data
            if update_cache:
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
            if update_cache and not dry_run:
                self.update_cache()
        else:
            self.logger.warn("File [%s] is not managed by Muzak, leaving it alone ...")
            return

    def update_file(self, file_path: str, new_data: dict, update_cache: bool = True):
        if file_path in self.music:
            self.logger.debug("Updating file: [%s]" % file_path)
            self.music[file_path].update(new_data)
            f = taglib.File(file_path)
            if f is not None:
                for key, value in new_data.items():
                    if not isinstance(value, list):
                        f.tags[key.upper()] = [value]
                    else:
                        f.tags[key.upper()] = value
                f.save()
            if update_cache:
                self.update_cache()
    
    def update_files(self, files: list, new_data: dict):
        for f in files:
            self.update_file(f, new_data, update_cache=False)
        self.update_cache()

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
        parser = QueryParser(self.raw)
        parsed = parser.parse_query()
        self.command = parsed[0]
        self.subject = parsed[1]
        self.target = parsed[2]
        self.limit = parsed[3]
        self.any = parsed[4]

    def __str__(self):
        return self.raw

    def __repr__(self):
        return "MuzakQuery: command=%s; subject=%s; target=%s; limit=%d; any=%s;" % (self.command, self.subject, self.target, self.limit, self.any)

    def _parse_query_string(self, query_str: str):
        """
        Parse query string 
        """
        if " " not in query_str:
            raise MQLSyntaxError("Invalid query: %s" % query_str)
        query_command, query_str = query_str.split(" ", 1)
        query_subject = query_str
        def_parts = []
        limit = 0
        _any = True

        if "limit" in query_str.lower():
            query_str, limit = re.split("limit", query_str, re.IGNORECASE)
            query_subject = query_str
            limit = int(limit)
        if "where" in query_str.lower():
            query_subject, def_str = re.split("where", query_str, flags=re.IGNORECASE)
            def_str = def_str.strip()
            if (def_str.startswith("[") and not def_str.endswith("]")) or (def_str.endswith("]") and not def_str.startswith("[")):
                raise MQLSyntaxError("Unterminated condition brackets in query near: %s" % def_str)
            if def_str.startswith("[") and def_str.endswith("]"):
                _any = False
                def_str = def_str[1:-1]
            def_parts = [x.strip() for x in def_str.strip().split(";")]
        if query_subject:
            query_subject = [x.strip() for x in query_subject.strip().split(",")]
            if "=" in query_subject[0]:
                subject_dict = {}
                for subject in query_subject:
                    if "=" not in subject:
                        raise MQLSyntaxError("Invalid query subject near: %s" % (",".join(query_subject)))
                    subject_parts = subject.split("=", 1)
                    subject_dict[subject_parts[0]] = subject_parts[1]
                query_subject = subject_dict
        if query_subject == "":
            query_subject = None
        query_str = query_str.strip()
        # query_parts = query_str.split(";")
        query_definition = {}
        for part in def_parts:
            if "=" not in part:
                if query_subject is not None:
                    raise AttributeError("Query String: [%s] is invalid near [%s]" % (query_str, part))
                else:
                    query_subject = def_parts
                    break
            key, value = part.split("=", 1)
            if value == "\\None":
                value = None
            if not _any:
                query_definition[key] = value
            else:
                if key not in query_definition:
                    query_definition[key] = [value]    
                else:
                    query_definition[key].append(value)
        return query_command, query_definition, query_subject, _any, limit


class MuzakQueryResult:
    def __init__(self, query: MuzakQuery, result_set: list, changed: list):
        self.query = query
        self.result_set = result_set
        self.changed_records = len(changed)
        self.changed_set = changed


class MuzakQL:
    def __init__(self, storage_driver: MuzakStorageDriver, debug: bool = False):
        self.debug = debug
        self.logger = Logging("Muzak", "Query", debug=debug).get_logger()
        self._storage_driver = storage_driver
        self._storage_cache = storage_driver.music
        self.config = storage_driver.config
        self.debug = storage_driver.debug
        self.methods = {
            "select": self._select_query,
            "delete": self._delete_query,
            "update": self._update_query,
            "show": self._show_properties
        }

    def _show_properties(self, query: MuzakQuery, limit: int = 0):
        if len(query.subject) > 0:
            value = self._storage_driver.metadata[query.subject[0]]
            if value is None:
                raise MQLError("Unknown property: %s" % query.subject[0])
            return MuzakQueryResult(query, [value], [])
        else:
            raise MQLSyntaxError("Invalid show query: %s" % query)

    def _update_query(self, query: MuzakQuery, limit: int = 0):
        results = self._select_query(query, limit)
        files = []
        for result in results.result_set:
            files.append(result["file_path"])
        self._storage_driver.update_files(files, query.subject)
        return MuzakQueryResult(query, [], results.result_set)

    def _delete_query(self, query: MuzakQuery, limit: int = 0):
        results = self._select_query(query, limit)
        files = []
        for result in results.result_set:
            files.append(result["file_path"])
        self._storage_driver.remove_files(files)
        return MuzakQueryResult(query, results.result_set, results.result_set)

    def _select_query(self, query: MuzakQuery, limit: int = 0):
        results = []
        it = 0
        for path, tag in self._storage_cache.items():
            if not query.any:
                if query.target.items() <= tag.items():
                    if query.subject is not None:
                        q_tag = {}
                        for s in query.subject:
                            q_tag[s] = tag.get(s, None)
                        result = {"file_path": path, "tag": q_tag}
                    else:
                        result = {"file_path": path, "tag": tag}
                    if result not in results:
                        results.append(result)
                    it += 1
                else:
                    for item, value in query.target.items():
                        if item not in tag and value is None:
                            if query.subject is not None:
                                q_tag = {}
                                for s in query.subject:
                                    q_tag[s] = tag.get(s, None)
                                result = {"file_path": path, "tag": q_tag}
                            else:
                                result = {"file_path": path, "tag": tag}
                            if result not in results:
                                results.append(result)
                                it += 1
            else:
                if len(query.target) > 0:
                    for item, value in query.target.items():
                        if item == "file_path":
                            if path in value:
                                if query.subject is not None:
                                    q_tag = {}
                                    for s in query.subject:
                                        q_tag[s] = tag.get(s, None)
                                    result = {"file_path": path, "tag": q_tag}
                                else:
                                    result = {"file_path": path, "tag": tag}
                                if result not in results:
                                    results.append(result)
                                    it += 1
                        elif item in tag:
                            if tag[item] in value:
                                if query.subject is not None:
                                    q_tag = {}
                                    for s in query.subject:
                                        q_tag[s] = tag.get(s, None)
                                    result = {"file_path": path, "tag": q_tag}
                                else:
                                    result = {"file_path": path, "tag": tag}
                                if result not in results:
                                    results.append(result)
                                    it += 1
                else:
                    q_tag = {}
                    for s in query.subject:
                        q_tag[s] = tag.get(s, None)
                    result = {"file_path": path, "tag": q_tag}
                    results.append(result)
                    it += 1
            if limit > 0:
                if it == limit:
                    break

        return MuzakQueryResult(query, results, [])

    def execute(self, query_str: str):
        """
        Query Muzak cache and return matching tracks
        :param query_str: String to use for track query. Format should be <tag>=<expected_value>[;<tag>=<expected_value> ...]
        :param limit: Limit result set
        """
        self.logger.debug("Executing query: %s" % query_str)
        query: MuzakQuery = MuzakQuery(query_str)
        self.logger.debug(repr(query))
        if query.command.lower() in self.methods:
            return self.methods[query.command.lower()](query, query.limit)
        else:
            raise MQLError("MQL Command [%s] does not exist ..." % query.command)