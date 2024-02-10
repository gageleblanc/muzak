import os
from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.logging import Logging
from muzak.db.models import Track
# from muzak.db import connect, close
from muzak.scanner import TAG_FIELDS, Scanner
from pathlib import Path
from muzak import db
import shutil
import re

from muzak.tools import update_trackinfo


class Library:
    def __init__(self, path: str, create: bool = False, debug: bool = False):
        self.path = Path(path)
        if create:
            self.path.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            raise FileNotFoundError(f"Library path {self.path} does not exist")
        # self.db_path = self.path / "muzak.db"
        self.library_name = self.path.stem
        self.db_path = os.getenv("MUZAK_DATA_DIR", "/var/lib/muzak/libraries")
        self.db_path = Path(self.db_path) / f"{self.library_name}.db"
        db.DB_PATH = self.db_path
        self.library_config = JSONConfigurationFile(self.path / "muzak.json", schema={
            "filename_format": str,
            "network_share": bool
        }, auto_create={
            "filename_format": "{album_artist}/{album}/{title} [{isrc}]",
            "network_share": False
        })
        # if self.library_config["network_share"]:
        #     home_path = Path.home()
        #     if not (home_path / ".muzak").exists():
        #         (home_path / ".muzak").mkdir(parents=True, exist_ok=True)
        #     local_db_path = home_path.joinpath(".muzak", "%s.db" % self.library_name)
        #     if db.DB_PATH.exists():
        #         if not local_db_path.exists():
        #             shutil.copyfile(db.DB_PATH, local_db_path)
        #         else:
        #             network_db_mtime = os.path.getmtime(db.DB_PATH)
        #             local_db_mtime = os.path.getmtime(local_db_path)
        #             if network_db_mtime > local_db_mtime:
        #                 shutil.copyfile(db.DB_PATH, local_db_path)
        #     db.DB_PATH = local_db_path
        self.logger = Logging("Library", str(self.path.stem), debug=debug).get_logger()
        # self.db = create_or_open(self.db_path)

    def _remove_empty_dirs(self, path: str):
        """
        Remove empty directories from the given path.
        """
        if not os.path.isdir(path):
            return
        files = os.listdir(path)
        for f in files:
            full_path = os.path.join(path, f)
            if os.path.isdir(full_path):
                self._remove_empty_dirs(full_path)
        
        files = os.listdir(path)
        if len(files) == 0:
            self.logger.info("Removing empty directory: [%s]" % path)
            os.rmdir(path)

    def _sanitize_trackinfo(self, track: str):
        for k, v in TAG_FIELDS.items():
            if k in track:
                if isinstance(track[k], list):
                    _v = []
                    for i in track[k]:
                        _i = re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "", i)
                        _v.append(re.sub(r"\s+", " ", _i))
                    track[k] = _v
                elif isinstance(track[k], str):
                    _v = re.sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "", track[k])
                    _v = re.sub(r"\s+", " ", _v)
                    track[k] = _v
                elif isinstance(track[k], int):
                    track[k] = int(track[k])
        if track["album_artist"] == "Unknown":
            if len(track["artist"]) > 0:
                track["album_artist"] = track["artist"][0]
        return track
        
    def _build_filename(self, track: dict):
        extension = Path(track["path"]).suffix
        filename = self.library_config["filename_format"].format(**track)
        filename = re.sub(r"\s+", " ", filename)
        filename = filename.strip()
        filename = filename + extension
        return filename

    def artists(self):
        return Track.artists()
    
    def albums(self, artist: str = None):
        return Track.albums(artist=artist)

    def get(self, **kwargs):
        if len(kwargs) == 0:
            return Track.all()
        return Track(**kwargs)

    def add_track(self, track: str, move: bool = False, **kwargs):
        # try:
        #     track_info = Scanner.scan_file(track)
        # except OSError:
        #     self.logger.warning(f"Unable to scan [{track}]")
        #     return None
        track_info = Scanner.scan_file(track)
        for k, v in kwargs.items():
            if k in track_info:
                if k in TAG_FIELDS and isinstance(v, TAG_FIELDS[k]["type"]):
                    track_info[k] = v
        sanitized = self._sanitize_trackinfo(track_info)
        track_info["title"] = sanitized["title"]
        track_filename = self._build_filename(sanitized)
        track_path = self.path / track_filename
        if track_path.exists():
            try:
                exist = Track(path=str(track_path))
            except Exception:
                pass
            else:
                self.logger.warning(f"Scanner found duplicate track [{track}] -> [{track_path}]")
                if move:
                    Path(track).unlink()
                return exist
        else:
            if not track_path.parent.exists():
                track_path.parent.mkdir(parents=True, exist_ok=True)
            if move:
                self.logger.info(f"Moving track [{track}] -> [{track_path}]")
                shutil.copyfile(track, track_path)
                Path(track).unlink()
            else:
                self.logger.info(f"Copying track [{track}] -> [{track_path}]")
                shutil.copyfile(track, track_path)
        self.logger.info(f"Adding track [{track_path}] to database ...")
        track_info["path"] = str(track_path)
        return Track.new(**track_info)

    def add_tracks(self, files: list, move: bool = False):
        """
        Adds the given files to the library database.
        """
        errors = []
        for track in files:
            # self.add_track(track, move=move)
            try:
                self.add_track(track, move=move)
            except Exception as e:
                self.logger.warning(f"Failed to add {track}: {e}")
                errors.append(track)
                pass
        return errors

    def prune(self):
        """
        Prune the library database of tracks that no longer exist.
        """
        existing = [i["path"] for i in Track.all()]
        for track in existing:
            if not Path(track).exists():
                Track(path=track).delete()
                self.logger.info(f"Pruned [{track}]")
        self._remove_empty_dirs(self.path)

    def scan(self):
        """
        Re-scans the library to update the database.
        """
        self.logger.info(f"Scanning [{self.path}]")
        existing = [i["path"] for i in Track.all()]
        scanner = Scanner(self.path)
        files = scanner.scan(exclude_files=existing)
        # print(existing)
        self.logger.info(f"Found {len(files)} new files")
        errors = self.add_tracks(files, move=True)
        self.logger.info("Pruning library ...")
        self.prune()
        return errors

    def refresh(self, track_id: int):
        """
        Refresh the track information for the given track.
        """
        try:
            track_id = int(track_id)
            track = Track(id=track_id)
        except ValueError:
            track = Track(path=track_id)
        track_path = track["path"]
        self.logger.info("Refreshing track [{track_path}]".format(
            track_path=track_path
        ))
        track.delete()
        return self.add_track(track_path, move=True)

    def match_missing(self, api: str = "deezer", **kwargs):
        """
        Attempt to automatically update missing information from the given API.
        """
        no_isrcs = Track.no_isrc()
        self.logger.info(f"Found {len(no_isrcs)} tracks missing ISRCs")
        for track in no_isrcs:
            try:
                self.query_trackinfo(track["id"], api=api, **kwargs)
            except ValueError as e:
                self.logger.warning(f"Failed to update {track['path']}: {e}")
                pass

    def query_trackinfo(self, track_id: int, api: str = "deezer", **kwargs):
        """
        Attempt to update trackinfo from Deezer API via ISRC.
        """
        try:
            track_id = int(track_id)
            track = Track(id=track_id)
        except ValueError:
            track = Track(path=track_id)
        track_path = track["path"]
        old_path = track_path
        self.logger.info("Attempting to pull track info for [{track_path}]".format(
            track_path=track_path
        ))
        new_info = update_trackinfo(track_path, api=api, **kwargs)
        sanitized = self._sanitize_trackinfo(new_info)
        new_info["title"] = sanitized["title"]
        track_filename = self._build_filename(sanitized)
        track_path = self.path / track_filename
        # if not track_path.exists():
        #     self.logger.info("Moving track [{file_path}] -> [{track_path}]".format(
        #         file_path=old_path,
        #         track_path=track_path
        #     ))
        #     if not track_path.parent.exists():
        #         track_path.parent.mkdir(parents=True, exist_ok=True)
        #     shutil.move(track["path"], track_path)
        if str(track_path) != str(old_path):
            self.logger.info("Moving track [{file_path}] -> [{track_path}]".format(
                file_path=old_path,
                track_path=track_path
            ))
            if not track_path.parent.exists():
                track_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(track["path"], track_path)
        new_info["path"] = str(track_path)
        try:
            track = Track(path=str(track_path))
            self.logger.info("Existing record found for new track path: [{track_path}], updating database ...".format(
                track_path=track_path
            ))
            del new_info["path"]
            track.update(**new_info)
            return track
        except Exception:
            pass
        track.delete()
        track = Track.new(**new_info)
        return track

    def search(self, query: str):
        """
        Search the library for the given query.
        """
        return Track.search(query)
