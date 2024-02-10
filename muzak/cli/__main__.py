import json
from pathlib import Path
from muzak.db.models import Track
from muzak.library import Library
from muzak.scanner import Scanner
from clilib.config.config_loader import YAMLConfigurationFile
from clilib.builders.app import EasyCLI
from muzak.tools import print_table


class MuzakCli:
    """
    Muzak command line interface.
    """
    # debug = False
    # config = None
    def __init__(self, debug: bool = False):
        """
        :param debug: Whether to enable debug logging.
        """
        self.debug = debug
        self.config_path = Path.home() / ".config" / ".muzak.json"
        self.config = YAMLConfigurationFile(self.config_path, schema={
            "libraries": list,
            "library": str,
        }, auto_create={
            "libraries": [],
            "library": "",
        })
        setattr(MuzakCli, "debug", debug)
        setattr(MuzakCli, "config", self.config)

    def scan(self, path: str, exclude_subdirs: bool = False, exclude: list = None):
        """
        Scan the given path for music files.
        :param path: The path to scan.
        :param exclude_subdirs: Whether to exclude subdirectories.
        :param exclude: A list of files to exclude.
        """
        # print(exclude)
        scanner = Scanner(path, subdirs=not exclude_subdirs)
        files = scanner.scan() #(exclude=exclude)
        for f in files:
            print(f)

    def inspect(self, path: str):
        """
        Inspect the given file.
        :param path: The path to the file.
        """
        # print table of tags
        file_info = Scanner.scan_file(path)
        longest_key = 0
        for k, v in file_info.items():
            if len(k) > longest_key:
                longest_key = len(k)
        for k, v in file_info.items():
            print(f"{k.ljust(longest_key)}: {v}")

    class Config:
        """
        Manage muzak config
        """
        def __init__(self):
            """
            """
            pass

        def add_library(self, path: str):
            """
            Add a library to the config.
            :param path: The path to the library.
            """
            path = Path(path)
            if path.exists():
                if path.is_dir():
                    MuzakCli.config["libraries"].append(str(path))
                    if not MuzakCli.config["library"]:
                        MuzakCli.config["library"] = str(path)
                    MuzakCli.config.write()
                else:
                    print(f"Path [{path}] is not a directory")
            else:
                print(f"Path [{path}] does not exist")
            print("Added library")

        def set(self, key: str, value: str):
            """
            Set the given key to the given value.
            :param key: The key to set.
            :param value: The value to set the key to.
            """
            MuzakCli.config[key] = value
            MuzakCli.config.write()

        def get(self, key: str):
            """
            Get the value of the given key.
            :param key: The key to get.
            """
            if key in MuzakCli.config:
                print(MuzakCli.config[key])
            else:
                print(f"Invalid key [{key}]")

    class Library:
        """
        Library management.
        """
        def __init__(self):
            """
            :param library: The library to manage.
            """
            if not MuzakCli.config["library"]:
                print("No library configured")
                exit(1)
            self.library = Library(MuzakCli.config["library"], debug=MuzakCli.debug)
            self.logger = self.library.logger

        def _add_folder(self, path: str, move: bool = False, exclude_subdirs: bool = False, exclude: list = None):
            scanner = Scanner(path, subdirs=not exclude_subdirs)
            files = scanner.scan(exclude_dirs=exclude)
            return self.library.add_tracks(files, move=move)

        def add(self, path: str, move: bool = False, exclude_subdirs: bool = False, exclude: list = None):
            """
            Add the given path to the library.
            :param path: The path to add.
            :param move: Whether to move the file to the library.
            """
            path = Path(path)
            if path.is_dir():
                self.logger.info(f"Scanning [{path}] for music files ...")
                errors = self._add_folder(path, move=move, exclude_subdirs=exclude_subdirs, exclude=exclude)
                if len(errors) > 0:
                    print("Failed to add the following files:")
                    for e in errors:
                        print(f" - {e}")
            elif path.is_file():
                self.logger.info(f"Adding [{path}]")
                self.library.add_track(str(path), move=move)

        def details(self, output: str = "table", skip_isrc: bool = False):
            """
            Print details about the given library.
            """
            tbl_data = {
                "Library": str(self.library.path),
                "Tracks": len(self.library.get()),
                "Artists": len(self.library.artists()),
                "Albums": len(self.library.albums()),
            }
            if not skip_isrc:
                no_isrc = Track.no_isrc()
                pathlist = [str(i["path"]) for i in no_isrc]
                tbl_data["Tracks w/o ISRC (%d)" % len(pathlist)] = pathlist
            if output == "table":
                print_table(tbl_data)
            elif output == "json":
                if not skip_isrc:
                    del tbl_data["Tracks w/o ISRC (%d)" % len(pathlist)]
                    tbl_data["no_isrc"] = pathlist
                print(json.dumps(tbl_data), flush=True)
            else:
                print("Unsupported output format")

        def inspect(self, track: str):
            """
            Inspect the given track.
            :param track: The track to inspect. Can be a path or ID.
            """
            try:
                track = int(track)
                track = Track(id=track)
            except ValueError:
                track = Track(path=track)
            # track = Track(path=track)
            print_table(dict(track._data))

        def set_tag(self, track_id: int, tag: str, value: str):
            """
            Set the given tag to the given value for the given track.
            :param track_id: The track ID.
            :param tag: The tag to set.
            :param value: The value to set the tag to.
            """
            if tag.lower() not in Track._fields:
                print(f"Invalid tag [{tag}]")
                exit(1)
            if tag.lower() in ("id", "path"):
                print(f"Cannot set tag [{tag}]")
                exit(1)
            track = Track(id=track_id)
            track[tag] = value

        def scan(self):
            """
            Scan the library for new files.
            """
            errors = self.library.scan()
            if len(errors) > 0:
                print("Failed to add the following files:")
                for e in errors:
                    print(f" - {e}")
        
        def prune(self):
            """
            Prune the library of tracks that no longer exist.
            """
            self.library.prune()

        def search(self, query: str, ids: bool = False):
            """
            Search the library for the given query.
            :param query: The query to search for.
            :param ids: Whether to print IDs with paths.
            """
            tracks = self.library.search(query)
            track_results = {}
            for track in tracks:
                if ids:
                    print(f"{track['id']} {track['path']}")
                else:
                    print(track["path"])

        def refresh(self, track: str):
            """
            Refresh the track information for the given track.
            :param track: The track to refresh. Can be a path or ID.
            """
            track = self.library.refresh(track)
            print_table(dict(track._data))

        def match_missing(self, api: str = "deezer"):
            """
            Attempt to automatically update missing information from the given API.
            """
            try:
                if api == "spotify":
                    self.library.match_missing(api=api, SPOTIFY_CLIENT_ID=MuzakCli.config["SPOTIFY_CLIENT_ID"], SPOTIFY_CLIENT_SECRET=MuzakCli.config["SPOTIFY_CLIENT_SECRET"])
                else:
                    self.library.match_missing(api=api)
            except ValueError as e:
                print("Error: %s" % str(e))
                exit(1)

        def identify_track(self, track_id: int, api: str = "deezer"):
            """
            Attempt to update trackinfo from Deezer API via ISRC.
            :alias identify:
            :param track_id: The track ID or path.
            """
            try:
                if api == "spotify":
                    track = self.library.query_trackinfo(track_id, api=api, SPOTIFY_CLIENT_ID=MuzakCli.config["SPOTIFY_CLIENT_ID"], SPOTIFY_CLIENT_SECRET=MuzakCli.config["SPOTIFY_CLIENT_SECRET"])
                else:
                    track = self.library.query_trackinfo(track_id, api=api)
            except ValueError as e:
                print("Error: %s" % str(e))
                exit(1)
            print("Updated track info:")
            print_table(dict(track._data))

def cli():
    """
    Muzak command line interface.
    """
    EasyCLI(MuzakCli)

if __name__ == "__main__":
    cli()