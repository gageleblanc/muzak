from pathlib import Path
import sqlite3
import json

LIBRARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY,
    title TEXT,
    artist TEXT,
    album TEXT,
    album_artist TEXT,
    track INTEGER,
    disc INTEGER,
    genre TEXT,
    year TEXT,
    duration INTEGER,
    sample_rate INTEGER,
    bitrate INTEGER,
    isrc TEXT,
    path TEXT
);

"""

def create_or_open(path: str):
    if not Path(path).exists():
        db = LibraryDB(path)
        db.create()
        return db
    else:
        return LibraryDB(path)


class LibraryDB:
    def __init__(self, path: str):
        self.path = Path(path)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()

    def create(self):
        """
        Initialize the database.
        """
        self.cursor.execute(LIBRARY_SCHEMA)
        self.db.commit()

    def add(self, track: dict):
        """
        Add a track to the database.
        """
        if isinstance(track, dict):
            track = [track]
        for t in track:
            for k, v in t.items():
                if isinstance(v, list):
                    t[k] = json.dumps(v)
            self.cursor.execute(
                "INSERT INTO tracks (title, artist, album, album_artist, track, disc, genre, year, duration, sample_rate, bitrate, path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    t["title"],
                    t["artist"],
                    t["album"],
                    t["album_artist"],
                    t["track"],
                    t["disc"],
                    t["genre"],
                    t["year"],
                    t["duration"],
                    t["sample_rate"],
                    t["bitrate"],
                    t["path"],
                ),
            )
        self.db.commit()
        return self.get(id=self.cursor.lastrowid)[0]

    def get(self, **kwargs):
        """
        Get tracks from the database matching the given criteria. If no criteria are given, return all tracks.
        """
        query = "SELECT * FROM tracks"
        if len(kwargs) > 0:
            query += " WHERE "
            qps = []
            values = []
            for key, value in kwargs.items():
                if isinstance(value, int):
                    qps.append(f"{key} = ?")
                else:
                    qps.append(f"{key} = '?'")
                values.append(value)
            query += " AND ".join(qps)
            self.cursor.execute(query, tuple(values))
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def update(self, track: dict) -> None:
        """
        Update a track in the database with the given information.
        """
        self.cursor.execute(
            "UPDATE tracks SET title = ?, artist = ?, album = ?, album_artist = ?, track = ?, disc = ?, genre = ?, year = ?, duration = ?, sample_rate = ?, bitrate = ?, path = ? WHERE id = ?",
            (
                track["title"],
                track["artist"],
                track["album"],
                track["album_artist"],
                track["track"],
                track["disc"],
                track["genre"],
                track["year"],
                track["duration"],
                track["sample_rate"],
                track["bitrate"],
                track["path"],
                track["id"]
            )
        )
        self.db.commit()
    
    def delete(self, **kwargs) -> None:
        """
        Delete tracks from the database matching the given criteria. If no criteria are given, raise a ValueError.
        """
        if kwargs:
            query = "DELETE FROM tracks WHERE "
            qps = []
            values = []
            for key, value in kwargs.items():
                qps.append(f"{key} = '?'")
                values.append(value)
            query += " AND ".join(qps)
            self.cursor.execute(query, tuple(values))
        else:
            raise ValueError("No arguments given to delete")

    def artists(self):
        """
        Return all artists in the database.
        """
        self.cursor.execute("SELECT DISTINCT album_artist FROM tracks")
        return [i["album_artist"] for i in self.cursor.fetchall()]
    
    def albums(self, artist: str = None):
        """
        Return all albums in the database.
        """
        if artist:
            self.cursor.execute("SELECT DISTINCT album FROM tracks WHERE album_artist = ?", (artist,))
        else:
            self.cursor.execute("SELECT DISTINCT album_artist, album FROM tracks")
        return [(i["album_artist"], i["album"]) for i in self.cursor.fetchall()]
