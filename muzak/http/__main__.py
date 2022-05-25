from pathlib import Path
from flask import Flask
from flask import request
from flask import Response
from muzak import Muzak
from muzak.drivers import MuzakQueryResult, MuzakStorageDriver
from clilib.util.logging import Logging
from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.dict import SearchableDict
from muzak.http.util import Playlists, LinkCode
from PIL import Image
import mutagen
import os
import sys
import base64
import random
import operator

app = Flask(__name__)

logger = Logging("Muzak", "api").get_logger()
logger.info("Starting Muzak API")
muzak = Muzak()
api_home = Path(muzak.storage_dir).joinpath(".muzak_api")
api_config_path = api_home.joinpath("config.json")
api_config = JSONConfigurationFile(str(api_config_path), {"auth_enabled": bool}, auto_create={"auth_enabled": False})
LinkManager = LinkCode(str(api_home.joinpath("links.json")))
PlaylistManager = Playlists()
storage_driver: MuzakStorageDriver = muzak.storage_driver(muzak.storage_dir, muzak.config)
recently_played_tracks = []
track_statistics = {}

if api_config["auth_enabled"]:
    @app.before_request
    def auth_required():
        if "MuzakLink" not in request.headers:
            return Response("Authentication required", 401)
        link_code = request.headers["MuzakLink"]
        if not LinkManager.check_link(link_code):
            return Response("Authentication failed", 401)


@app.route("/api/v1/update/cache/", methods=["GET"])
def update_cache():
    logger.info("Updating cache")
    muzak = Muzak()
    storage_driver: MuzakStorageDriver = muzak.storage_driver(muzak.storage_dir, muzak.config)
    return {"status": "ok"}

@app.route("/api/v1/query", methods=["POST"])
def query():
    """
    API endpoint for querying the database.
    """
    query = request.json["query"]
    result = muzak.query(query)
    return {"results": result.result_set}

@app.route("/api/v1/search/", methods=["POST"])
def search():
    """
    API endpoint for searching the database.
    """
    query = request.json["query"]
    if "limit" in request.json:
        limit = request.json["limit"]
    else:
        limit = 0
    result = muzak.search(query, limit)
    final = []
    added = []
    for res in result.result_set:
        _id = base64.b64encode(res["file_path"].encode()).decode()
        if _id not in added:
            added.append(_id)
            final_res = {
                "id": _id,
                "title": res["tag"]["title"],
                "artist": res["tag"]["artist"],
                "album": res["tag"]["album"],
            }
            final.append(final_res)
    return {"results": final}

@app.route("/api/v1/labels", methods=["GET"])
def labels():
    """
    API Endpoint for getting all labels.
    """
    result: MuzakQueryResult = storage_driver.mql.execute("show labels")
    return {"labels": result.result_set[0]}

@app.route("/api/v1/tracks/", methods=["GET"])
def tracks():
    """
    API Endpoint for getting all tracks.
    """
    all_tracks = storage_driver.music.keys()
    return {"tracks": list(all_tracks)}

@app.route("/api/v1/track/info/<track_id>/", methods=["GET"])
def track_info(track_id):
    """
    API Endpoint for getting track info.
    """
    logger.info("Getting file for ID: %s" % track_id)
    filename = base64.b64decode(track_id).decode()
    logger.info("Filename: %s" % filename)
    if filename in storage_driver.music:
        tag = storage_driver.music[filename]
        return {"tag": tag}
    else:
        return Response(status=404)

@app.route("/api/v1/track/info/", methods=["POST"])
def tracks_info():
    """
    API Endpoint for getting multiple track infos
    """
    tracks = request.json["tracks"]
    final = {}
    for track_id in tracks:
        logger.info("Getting file for ID: %s" % track_id)
        filename = base64.b64decode(track_id).decode()
        logger.info("Filename: %s" % filename)
        if filename in storage_driver.music:
            final[track_id] = storage_driver.music[filename]
        else:
            final[track_id] = None
    return final

@app.route("/api/v1/track/cover/<track_id>/", methods=["GET"])
def cover(track_id):
    """
    API Endpoint for getting track cover.
    """
    logger.info("Getting cover for ID: %s" % track_id)
    filename = base64.b64decode(track_id).decode()
    logger.info("Filename: %s" % filename)
    if filename in storage_driver.music:
        mf = mutagen.File(filename)
        if "APIC:cover" in mf:
            cover = mf["APIC:cover"].data
            # cover_b64 = base64.b64encode(cover).decode()
            res = Response(cover, mimetype="image/jpeg")
            res.cache_control.max_age = 3000
            return res
        else:
            res = Response(status=404)
            res.cache_control.max_age = 3000
            return res
    else:
        res = Response(status=404)
        res.cache_control.max_age = 3000
        return res

@app.route("/api/v1/shuffle/", methods=["GET"])
@app.route("/api/v1/shuffle/<shuffle_count>/", methods=["GET"])
def shuffle(shuffle_count = 10):
    """
    Shuffle random tracks from the entire collection of music
    """
    shuffle_count = int(shuffle_count)
    tracks = storage_driver.music.keys()
    shuffle_tracks = random.sample(tracks, shuffle_count)
    final_tracks = []
    for track in shuffle_tracks:
        final_tracks.append(base64.b64encode(track.encode()).decode())
    return {"tracks": final_tracks}

@app.route("/api/v1/recently_played/", methods=["GET"])
def recently_played():
    """
    Get a list of recently played tracks
    """
    return {"tracks": recently_played_tracks}

@app.route("/api/v1/popular/", methods=["GET"])
@app.route("/api/v1/popular/<limit>/", methods=["GET"])
def popular(limit = 10):
    """
    Get a list of popular tracks
    """
    limit = int(limit)
    most_popular = dict(sorted(track_statistics.items(), key=operator.itemgetter(1), reverse=True)[:limit])
    return {"tracks": list(most_popular.keys())}

@app.route("/api/v1/stream/<track_id>/", methods=["GET"])
def mp3(track_id):
    """
    API endpoint for streaming mp3s.
    """
    # filename = request.json["file"]
    logger.info("Getting file for ID: %s" % track_id)
    filename = base64.b64decode(track_id).decode()
    logger.info("Filename: %s" % filename)
    if track_id in track_statistics:
        track_statistics[track_id] += 1
    else:
        track_statistics[track_id] = 1

    if track_id not in recently_played_tracks:
        recently_played_tracks.append(track_id)
        if len(recently_played_tracks) > 10:
            recently_played_tracks.pop(0)
    if not filename.startswith(muzak.config["storage_directory"]) or filename not in storage_driver.music:
        return Response(status=403)
    if not Path(filename).is_file():
        return Response(status=404)
    def generate():
        with open(filename, "rb") as f:
            data = f.read(1024)
            while data:
                yield data
                data = f.read(1024)
    return Response(generate(), mimetype="audio/mp3")

##########################
###  Artist Endpoints  ###
##########################

@app.route("/api/v1/artists/", methods=["GET"])
def artists():
    """
    API Endpoint for getting all artists.
    """
    return {"artists": list(storage_driver.metadata["releases"].keys())}

@app.route("/api/v1/artists/<artist>/albums/", methods=["GET"])
def artist(artist):
    """
    API Endpoint for getting all albums for a specific artist.
    """
    if artist in storage_driver.metadata["releases"]:
        return {"albums": storage_driver.metadata["releases"][artist]}

@app.route("/api/v1/artists/<artist>/albums/<album>/tracks/", methods=["GET"])
def album_tracks(artist, album):
    """
    API Endpoint for getting all tracks from an album for a specific artist.
    """
    # result: MuzakQueryResult = storage_driver.mql.execute("select [file_path] where {artist=%s,album=%s} limit 1" % (artist, album))
    tracks = {}
    for path, info in storage_driver.music.items():
        if "artist" not in info.keys() or "album" not in info.keys():
            continue
        if info["artist"].lower() == artist.lower() and info["album"].lower() == album.lower():
            _id = base64.b64encode(path.encode()).decode()
            track_info = info
            track_info["id"] = _id
            tracks[_id] = track_info
    return {"tracks": tracks}

@app.route("/api/v1/artists/<artist>/<album>/cover/", methods=["GET"])
def album_coverart(artist, album):
    """
    API Endpoint for getting cover art for an artist's album.
    """
    # result: MuzakQueryResult = storage_driver.mql.execute("select [file_path] where {artist=%s,album=%s} limit 1" % (artist, album))
    # file_path = result.result_set[0]["file_path"]
    file_path = None
    for path, info in storage_driver.music.items():
        if "artist" not in info or "album" not in info:
            continue
        if info["artist"].lower() == artist.lower() and info["album"].lower() == album.lower():
            file_path = path
            break
    if file_path is None:
        return Response(status=404)
    mf = mutagen.File(file_path)
    if "APIC:cover" in mf:
        cover = mf["APIC:cover"].data
        # cover_b64 = base64.b64encode(cover).decode()
        res = Response(cover, mimetype="image/jpeg")
        res.cache_control.max_age = 3000
        return res
    else:
        return Response(status=404)

@app.route("/api/v1/artists/<artist>/cover/", methods=["GET"])
def artist_coverart(artist):
    """
    API Endpoint for getting cover art for an artist.
    """
    file_path = None
    for path, info in storage_driver.music.items():
        if "artist" not in info:
            continue
        if info["artist"].lower() == artist.lower():
            file_path = path
            break
    if file_path is None:
        return Response(status=404)
    mf = mutagen.File(file_path)
    if "APIC:cover" in mf:
        cover = mf["APIC:cover"].data
        # cover_b64 = base64.b64encode(cover).decode()
        res = Response(cover, mimetype="image/jpeg")
        res.cache_control.max_age = 3000
        return res
    else:
        return Response(status=404)

##########################
### Playlist Endpoints ###
##########################

@app.route("/api/v1/create/playlist/", methods=["POST"])
def create_playlist():
    """
    API endpoint for creating a playlist.
    """
    name = request.json["name"]
    tracks = request.json["tracks"]
    playlist = PlaylistManager.create_playlist(name, tracks)
    return {"playlist": playlist}

@app.route("/api/v1/playlists/", methods=["GET"])
def playlists():
    """
    API endpoint for getting all playlists.
    """
    playlists = PlaylistManager.playlists["."]
    return {"playlists": playlists}

@app.route("/api/v1/playlist/<playlist_id>/", methods=["GET"])
def playlist(playlist_id):
    """
    API endpoint for getting a playlist.
    """
    playlist = PlaylistManager.get_playlist(playlist_id)
    return {"playlists": playlist}

@app.route("/api/v1/playlist/add/", methods=["POST"])
def add_to_playlist():
    """
    API endpoint for adding tracks to a playlist.
    """
    playlist_id = request.json["playlist"]
    tracks = request.json["tracks"]
    PlaylistManager.add_tracks(playlist_id, tracks)
    return {"status": "ok"}

@app.route("/api/v1/playlist/remove/", methods=["POST"])
def remove_from_playlist():
    """
    API endpoint for removing tracks from a playlist.
    """
    playlist_id = request.json["playlist"]
    tracks = request.json["tracks"]
    PlaylistManager.remove_track(playlist_id, tracks)
    return {"status": "ok"}
