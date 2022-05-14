from pathlib import Path
from flask import Flask
from flask import request
from flask import Response
from muzak import Muzak
from muzak.drivers import MuzakQueryResult, MuzakStorageDriver
from clilib.util.logging import Logging
import os
import sys
import base64
import random

app = Flask(__name__)

logger = Logging("Muzak", "api").get_logger()
logger.info("Starting Muzak API")
muzak = Muzak()
storage_driver: MuzakStorageDriver = muzak.storage_driver(muzak.storage_dir, muzak.config)

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

@app.route("/api/v1/search", methods=["POST"])
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
    return {"results": result.result_set}

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

@app.route("/api/v1/shuffle/", methods=["GET"])
@app.route("/api/v1/shuffle/<shuffle_count>/", methods=["GET"])
def shuffle(shuffle_count = 10):
    """
    Shuffle random tracks from the entire collection of music
    """
    tracks = storage_driver.music.keys()
    shuffle_tracks = random.sample(tracks, shuffle_count)
    final_tracks = []
    for track in shuffle_tracks:
        final_tracks.append(base64.b64encode(track.encode()).decode())
    return {"tracks": final_tracks}

@app.route("/api/v1/stream/<track_id>/", methods=["GET"])
def mp3(track_id):
    """
    API endpoint for streaming mp3s.
    """
    # filename = request.json["file"]
    logger.info("Getting file for ID: %s" % track_id)
    filename = base64.b64decode(track_id).decode()
    logger.info("Filename: %s" % filename)
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
