from pathlib import Path
import shutil
import tempfile
from typing import List, Dict, Mapping
import taglib
import os

AUDIO_EXTENSIONS = [
    ".mp3",
    ".ogg",
    ".flac",
    ".m4a",
    ".wma",
    ".wav"
]

TAG_FIELDS = {
    "title": {
        "type": str,
        "keys": ["TITLE", "Title", "title"]
    },
    "artist": {
        "type": list,
        "keys": ["ARTIST", "Artist", "artist"]
    },
    "album": {
        "type": str,
        "keys": ["ALBUM", "Album", "album"]
    },
    "album_artist": {
        "type": str,
        "keys": ["ALBUMARTIST", "Albumartist", "albumartist"]
    },
    "track": {
        "type": int,
        "keys": ["TRACKNUMBER", "TRACK", "Track", "Tracknumber", "tracknumber", "track"]
    },
    "disc": {
        "type": int,
        "keys": ["DISCNUMBER", "DISC", "Discnumber", "Disc", "discnumber", "disc"]
    },
    "genre": {
        "type": list,
        "keys": ["GENRE", "Genre", "genre"]
    },
    "year": {
        "type": str,
        "keys": ["DATE", "YEAR", "Year", "Date", "year", "date"]
    },
    "duration": {
        "type": int,
        "keys": ["DURATION", "LENGTH", "Duration", "Length" "duration", "length"]
    },
    "isrc": {
        "type": str,
        "keys": ["ISRC", "Isrc", "isrc"]
    },
    "sample_rate": {
        "type": int,
        "keys": ["SAMPLERATE", "Samplerate", "samplerate"]
    },
    "bitrate": {
        "type": int,
        "keys": ["BITRATE", "Bitrate", "bitrate"]
    }
}


class Scanner:
    def __init__(self, path: str, subdirs: bool = True, audio_extensions: List[str] = AUDIO_EXTENSIONS):
        self.path = path
        self.subdirs = subdirs
        self.audio_extensions = audio_extensions

    def _find_files(self, path: str, exclude_files: list = None, exclude_dirs: list = None) -> List[str]:
        """
        Find files matching the given audio extensions in the given path.
        """
        files = []
        scan_path = Path(path)
        listing = os.listdir(path)
        for item in listing:
            item_path = scan_path.joinpath(item)
            if item_path.is_dir():
                if self.subdirs:
                    l = self._find_files(str(item_path), exclude_files=exclude_files, exclude_dirs=exclude_dirs)
                    files.extend(l)
            elif item_path.is_file():
                if item_path.suffix in self.audio_extensions:
                    if exclude_files:
                        if str(item_path.resolve()) in exclude_files:
                            continue
                    if exclude_dirs:
                        for d in exclude_dirs:
                            if str(item_path).startswith(d):
                                break
                        else:
                            files.append(str(item_path))
                    else:
                        files.append(str(item_path))
        return files
    
    @staticmethod
    def scan_file(path: str) -> Dict[str, str]:
        try:
            file_info = taglib.File(path)
        except UnicodeEncodeError as e:
            tmpfile_name = tempfile.mkstemp(suffix=Path(path).suffix)[1]
            shutil.copyfile(path, tmpfile_name)
            file_info = taglib.File(tmpfile_name)

        track_info = {}
        track_info["path"] = path
        for field, key_info in TAG_FIELDS.items():
            if field in track_info:
                continue
            for key in key_info["keys"]:
                if key in file_info.tags:
                    if isinstance(file_info.tags[key], list) and key_info["type"] == list:
                        _i = []
                        for i in file_info.tags[key]:
                            if i:
                                _i.append(i)
                        if len(_i) == 0:
                            _i = ["Unknown"]
                        track_info[field] = _i
                    else:
                        try:
                            track_info[field] = key_info["type"](file_info.tags[key][0])
                        except:
                            track_info[field] = "Unknown"
                    break
                else:
                    if key_info["type"] == list:
                        track_info[field] = ["Unknown"]
                    else:
                        track_info[field] = "Unknown"
        return track_info

    def scan(self, exclude_files: list = None, exclude_dirs: list = None) -> List[str]:
        """
        Scan the given path for music files.
        """
        return self._find_files(self.path, exclude_files=exclude_files, exclude_dirs=exclude_dirs)
    
    def scan_with_tags(self, exclude: list = None) -> List[dict]:
        """
        Scan the given path for music files, and return a list of taglib.File objects.
        """
        files = self.scan(exclude=exclude)
        tagged_files = []
        errors = []
        for f in files:
            try:
                track_info = Scanner.scan_file(f)
            except Exception as e:
                errors.append({
                    "path": f,
                    "error": e
                })
                continue
            tagged_files.append(track_info)
        return tagged_files, errors
