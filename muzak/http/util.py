from muzak import Muzak
from pathlib import Path
from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.logging import Logging
import base64
import random
import string
import time
import json

from muzak.drivers import MuzakStorageDriver

def build_api_env():
    """
    Builds the API environment.
    """
    muzak = Muzak()
    api_home = Path(muzak.config['storage_directory']).joinpath(".muzak_api")
    api_data = api_home.joinpath("data")
    api_data.mkdir(parents=True, exist_ok=True)
    return api_home

class ApiCache:
    """
    Cache for ceartain API Requests which take longer, like searches
    """
    def __init__(self):
        self.search = {
            "artists": {},
            "albums": {},
            "tracks": {},
        }

class CoverCache:
    """
    Cover cache.
    """
    def __init__(self, api_home):
        self.api_home = Path(api_home)
        self.cache_home = api_home.joinpath("cache")
        self.track_cache = self.cache_home.joinpath("track")
        self.artist_cache = self.cache_home.joinpath("artist")
        self.cache_home.mkdir(parents=True, exist_ok=True)

    def set_cover_by_id(self, track_id, cover_data, force: bool = False):
        """
        Sets the cover by ID.
        """
        self.track_cache.mkdir(parents=True, exist_ok=True)
        final = self.track_cache.joinpath(track_id)
        if final.exists():
            if force:
                final.write_bytes(cover_data)
        else:
            final.write_bytes(cover_data)

    def set_cover_by_artist(self, artist, cover_data, force: bool = False):
        """
        Sets the cover by artist.
        """
        self.artist_cache.joinpath(artist).mkdir(parents=True, exist_ok=True)
        final = self.artist_cache.joinpath(artist).joinpath("cover.jpg")
        if final.exists():
            if force:
                final.write_bytes(cover_data)
        else:
            final.write_bytes(cover_data)

    def set_cover_by_album(self, artist, album, cover_data, force: bool = False):
        """
        Sets the cover by album.
        """
        self.artist_cache.joinpath(artist).joinpath(album).mkdir(parents=True, exist_ok=True)
        final = self.artist_cache.joinpath(artist).joinpath(album).joinpath("cover.jpg")
        if final.exists():
            if force:
                final.write_bytes(cover_data)
        else:
            final.write_bytes(cover_data)

    def get_cover_by_id(self, track_id):
        """
        Gets the cover by ID.
        """
        cover_path = self.track_cache.joinpath(track_id)
        if cover_path.exists():
            with cover_path.open("rb") as f:
                return f.read()
        return None

    def get_cover_by_artist(self, artist):
        """
        Gets the cover by artist.
        """
        cover_path = self.artist_cache.joinpath(artist).joinpath("cover.jpg")
        if cover_path.exists():
            with cover_path.open("rb") as f:
                return f.read()
        return None

    def get_cover_by_album(self, artist, album):
        """
        Gets the cover by album.
        """
        cover_path = self.artist_cache.joinpath(artist).joinpath(album).joinpath("cover.jpg")
        if cover_path.exists():
            with cover_path.open("rb") as f:
                return f.read()
        return None

class LinkCode:
    def __init__(self, config_file: str):
        config_path = Path(config_file)
        self.config = JSONConfigurationFile(str(config_path), schema={"links": {}}, auto_create={"links": {}})
    
    def create_link(self, expire: int = None, description: str = None):
        """
        Creates a link code.
        """
        link_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        while link_code in self.config["links"]:
            link_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        self.config["links"][link_code] = {
            "link_code": link_code,
            "expires": expire,
            "description": description
        }
        self.config.write()
        return link_code

    def remove_link(self, link_code):
        """
        Removes a link.
        """
        if link_code not in self.config["links"]:
            return False
        del self.config["links"][link_code]
        self.config.write()
        return True

    def check_link(self, link_code):
        """
        Gets a link.
        """
        if link_code not in self.config["links"]:
            return False
        link_def = self.config["links"][link_code]
        if link_def["expires"] is not None:
            if link_def["expires"] < int(time.time()):
                self.remove_link(link_code)
                return False
        return True


class Playlists:
    """
    Class for managing playlists.
    """
    def __init__(self):
        self.playlists: JSONConfigurationFile = None
        self.playlist_names = []
        self.api_home = build_api_env()
        self.api_data = self.api_home.joinpath("data")
        self.logger = Logging("Muzak", "PlaylistManager").get_logger()
        self.load_playlists()

    def load_playlists(self):
        """
        Loads all playlists.
        """
        playlist_path = self.api_data.joinpath("playlists.json")
        self.playlists = JSONConfigurationFile(playlist_path, {}, auto_create={})

    def create_smart_playlist(self, playlist_name: str, rules: dict, storage_driver: MuzakStorageDriver):
        """
        Creates a smart playlist.
        """
        encoded_name = base64.b64encode(playlist_name.encode()).decode()
        final = []
        for path, tag in storage_driver.music.items():
            for label, value in rules.items():
                if label in tag:
                    if value.lower() in tag[label].lower():
                        _id = base64.b64encode(path.encode()).decode()
                        if _id not in final:
                            self.logger.info("Adding {} to smart playlist {}".format(_id, playlist_name))
                            final.append(_id)
        if encoded_name not in self.playlists:
            self.playlists[encoded_name] = {
                "tracks": final,
                "name": playlist_name,
                "description": "",
                "metadata": {
                    "smart": True,
                    "rules": rules
                }
            }
            self.playlists.write()
            return self.playlists[encoded_name]
        else:
            return None

    def update_smart_playlist(self, playlist_name: str, storage_driver: MuzakStorageDriver):
        """
        Updates a smart playlist.
        """
        encoded_name = base64.b64encode(playlist_name.encode()).decode()
        if encoded_name in self.playlists:
            if "smart" in self.playlists[encoded_name]["metadata"]:
                if "rules" in self.playlists[encoded_name]["metadata"]:
                    rules = self.playlists[encoded_name]["metadata"]["rules"]
                    if self.playlists[encoded_name]["metadata"]["smart"]:
                        final = []
                        for path, tag in storage_driver.music.items():
                            for label, value in rules.items():
                                if label in tag:
                                    if value.lower() in tag[label].lower():
                                        _id = base64.b64encode(path.encode()).decode()
                                        if _id not in final:
                                            final.append(_id)
                            self.playlists[encoded_name]["tracks"] = final
                            self.playlists.write()
                            return self.playlists[encoded_name]
        return None

    def create_playlist(self, name, tracks = [], metadata = {}):
        """
        Creates a new playlist.
        """
        encoded_name = base64.b64encode(name.encode()).decode()
        if encoded_name in self.playlists:
            playlist = self.playlists[encoded_name]
            playlist["tracks"].extend(tracks)
        else:
            self.playlists[encoded_name] = {
                "tracks": [],
                "name": name,
                "description": "",
                "metadata": metadata
            }
        self.playlists.write()
        return encoded_name

    def delete_playlist(self, playlist_id):
        """
        Deletes a playlist.
        """
        if playlist_id not in self.playlists:
            return False
        del self.playlists[playlist_id]
        self.playlists.write()
        return True

    def add_tracks(self, playlist_id, tracks):
        """
        Adds tracks to a playlist.
        """
        if playlist_id not in self.playlists:
            return False
        for track in tracks:
            if track not in self.playlists[playlist_id]["tracks"]:
                self.playlists[playlist_id]["tracks"].append(track)
        self.playlists.write()
        return True

    def add_track(self, playlist_id, track_id):
        """
        Adds a track to a playlist.
        """
        if playlist_id not in self.playlists:
            return False
        if track_id not in self.playlists[playlist_id]["tracks"]:
            self.playlists[playlist_id]["tracks"].append(track_id)
            self.playlists.write()
        return True

    def remove_track(self, playlist_id, track_id):
        """
        Removes a track from a playlist.
        """
        if playlist_id not in self.playlists:
            return False
        if isinstance(track_id, list):
            for track in track_id:
                self.playlists[playlist_id]["tracks"].remove(track)
        else:
            self.playlists[playlist_id]["tracks"].remove(track_id)
        self.playlists.write()
        return True

    def get_playlist(self, playlist_id):
        """
        Gets a playlist.
        """
        if playlist_id not in self.playlists:
            return False
        return self.playlists[playlist_id]
