from muzak import Muzak
from pathlib import Path
from clilib.config.config_loader import JSONConfigurationFile
import base64
import random
import string
import time
import json

def build_api_env():
    """
    Builds the API environment.
    """
    muzak = Muzak()
    api_home = Path(muzak.config['storage_directory']).joinpath(".muzak_api")
    api_data = api_home.joinpath("data")
    api_data.mkdir(parents=True, exist_ok=True)
    return api_home

class LinkCode:
    def __init__(self, config_file: str):
        config_path = Path(config_file)
        self.config = JSONConfigurationFile(str(config_path), schema={"links": {}}, auto_create={"links": {}})
    
    def create_link(self, expire: int):
        """
        Creates a link code.
        """
        link_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        while link_code in self.config["links"]:
            link_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        self.config["links"][link_code] = {
            "link_code": link_code,
            "expires": expire,
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
        self.load_playlists()

    def load_playlists(self):
        """
        Loads all playlists.
        """
        playlist_path = self.api_data.joinpath("playlists.json")
        self.playlists = JSONConfigurationFile(playlist_path, {}, auto_create={})

    def create_playlist(self, name, tracks = []):
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
