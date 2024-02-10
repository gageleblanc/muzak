import requests
import taglib
import mutagen
from mutagen.id3 import ID3, APIC
from mutagen.flac import Picture, FLAC
import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy import SpotifyClientCredentials
import json
from pathlib import Path
from muzak.scanner import Scanner


def update_trackinfo(track: str, api: str = "deezer", **kwargs) -> dict:
    """
    Update the track information for the given track using the given API.
    """
    file_type = track.split(".")[-1]
    file_info = taglib.File(track)
    track_info = {}
    for k, v in file_info.tags.items():
        track_info[k.lower()] = v
    file_info.close()
    if api == "deezer":
        if "isrc" not in track_info:
            raise ValueError(f"File {track} does not have an ISRC")
        url = f"https://api.deezer.com/2.0/track/isrc:{track_info['isrc'][0]}"
        result = requests.get(url)
        new_info = {}
        if result.status_code == 200:
            data = result.json()
            if "error" in data:
                raise ValueError(f"Unable to find track {track_info['isrc'][0]}")
            new_info["title"] = data["title"]
            if "artist" in data:
                new_info["artist"] = data["artist"]["name"]
            elif "contributors" in data:
                for c in data["contributors"]:
                    if c["role"] == "Main":
                        new_info["artist"] = c["name"]
                        break
            if "album" in data:
                new_info["album"] = data["album"]["title"]
            new_info["date"] = data["release_date"]
            cover_data = requests.get(data["album"]["cover_xl"])
            if cover_data.status_code == 200:
                new_info["cover"] = cover_data.content
                new_info["cover_type"] = cover_data.headers["Content-Type"]
        else:
            raise ValueError(f"Unable to find track {track_info['isrc'][0]}")
    elif api == "spotify":
        if "SPOTIFY_CLIENT_ID" not in kwargs or "SPOTIFY_CLIENT_SECRET" not in kwargs:
            raise ValueError("Missing Spotify client ID and/or client secret")
        cred_cache_path = Path.home() / ".muzak" / "spotify_credentials.json"
        if not cred_cache_path.parent.exists():
            cred_cache_path.parent.mkdir(parents=True)

        client_credentials_manager = SpotifyClientCredentials(client_id=kwargs["SPOTIFY_CLIENT_ID"], client_secret=kwargs["SPOTIFY_CLIENT_SECRET"], cache_handler=CacheFileHandler(cache_path=cred_cache_path))
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        if "isrc" not in track_info:
            if "artist" not in track_info or "title" not in track_info:
                raise ValueError(f"File {track} does not have an ISRC, artist, or title")
            result = sp.search(q=f"track:{track_info['title'][0]} artist:{track_info['artist'][0]}", type="track")
            if result["tracks"]["total"] > 0:
                data = result["tracks"]["items"][0]
                track_info["isrc"] = [data["external_ids"]["isrc"]]
            else:
                raise ValueError(f"Unable to find track {track_info['title'][0]} by {track_info['artist'][0]}") 
        result = sp.search(q=f"isrc:{track_info['isrc'][0]}", type="track")
        new_info = {}
        if result["tracks"]["total"] > 0:
            data = result["tracks"]["items"][0]
            new_info["title"] = data["name"]
            new_info["artist"] = [data["artists"][0]["name"]]
            new_info["album_artist"] = data["artists"][0]["name"]
            new_info["album"] = data["album"]["name"]
            new_info["date"] = data["album"]["release_date"]
            new_info["isrc"] = data["external_ids"]["isrc"]
            cover_data = requests.get(data["album"]["images"][0]["url"])
            if cover_data.status_code == 200:
                new_info["cover"] = cover_data.content
                new_info["cover_type"] = cover_data.headers["Content-Type"]
        else:
            raise ValueError(f"Unable to find track {track_info['isrc'][0]}")
    else:
        raise ValueError(f"Unsupported API {api}")
    if "cover" in new_info:
        if file_type == "mp3":
            audio = ID3(track)
            audio.add(APIC(3, "image/jpeg", 3, "Front cover", new_info["cover"]))
            audio.save()
        elif file_type == "flac":
            audio = mutagen.File(track)
            image = Picture()
            image.type = 3
            image.mime = new_info["cover_type"]
            image.desc = "Front cover"
            image.data = new_info["cover"]
            audio.add_picture(image)
            audio.save()
        elif file_type == "ogg":
            audio = mutagen.File(track)
            audio.add_picture(new_info["cover"], "image/jpeg")
            audio.save()
        else:
            raise ValueError(f"Unsupported file type {file_type}")
    file_info = taglib.File(track)
    for k, v in new_info.items():
        file_info.tags[k.upper()] = v
    file_info.save()
    file_info.close()
    new_tags = Scanner.scan_file(track)
    return new_tags

def print_table(tbl_data: dict):
    """
    Print a horizontal table
    """
    longest_key = 0
    longest_value = 0
    for header, value in tbl_data.items():
        if len(header) > longest_key:
            longest_key = len(header)
        if isinstance(value, list):
            for i in value:
                if len(i) > longest_value:
                    longest_value = len(i)
        else:
            if len(str(value)) > longest_value:
                longest_value = len(str(value))
    
    print(f"+{'-' * (longest_key + 2)}+{'-' * (longest_value + 2)}+", flush=True)
    for header, value in tbl_data.items():
        if isinstance(value, list):
            first_value = value.pop(0)
            print(f"| {header.rjust(longest_key)} | {first_value.ljust(longest_value)} |", flush=True)
            for i in value:
                print(f"| {''.rjust(longest_key)} | {str(i).ljust(longest_value)} |", flush=True)
        else:
            print(f"| {header.rjust(longest_key)} | {str(value).ljust(longest_value)} |", flush=True)
        # print(f"+{'-' * (longest_key + 2)}+{'-' * (longest_value + 2)}+", flush=True)
    print(f"+{'-' * (longest_key + 2)}+{'-' * (longest_value + 2)}+", flush=True)
