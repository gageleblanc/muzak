from muzak.db import Model, connect, close
import taglib

class Track(Model):
    _table = "tracks"
    _fields = {
        "id": {
            "type": "INTEGER",
            "primary_key": True,
            "auto_increment": True
        },
        "title": {
            "type": "TEXT"
        },
        "artist": {
            "type": "TEXT"
        },
        "album": {
            "type": "TEXT"
        },
        "album_artist": {
            "type": "TEXT"
        },
        "track": {
            "type": "INTEGER"
        },
        "disc": {
            "type": "INTEGER"
        },
        "genre": {
            "type": "TEXT"
        },
        "year": {
            "type": "INTEGER"
        },
        "duration": {
            "type": "INTEGER"
        },
        "sample_rate": {
            "type": "INTEGER"
        },
        "bitrate": {
            "type": "INTEGER"
        },
        "isrc": {
            "type": "TEXT"
        },
        "path": {
            "type": "TEXT",
            "unique": True
        }
    }
    _uniques = [
        "id",
        "path"
    ]
    _json_fields = [
        "artist",
        "genre"
    ]
    _dt_fields = None

    def __str__(self):
        return f"<Track {self['path']}>"
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        file_info = taglib.File(self["path"])
        if isinstance(value, list):
            file_info.tags[key.upper()] = value
        else:
            file_info.tags[key.upper()] = [value]
        file_info.save()

    @classmethod
    def search(cls, query: str):
        """
        Search for tracks matching the given query.
        """
        conn, cursor = connect()
        cursor.execute("SELECT * FROM tracks WHERE title LIKE ? OR artist LIKE ? OR album LIKE ? OR album_artist LIKE ?", (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        return [cls(from_dict=dict(row)) for row in rows]

    @classmethod
    def artists(cls):
        """
        Get all artists.
        """
        conn, cursor = connect()
        cursor.execute("SELECT DISTINCT album_artist FROM tracks")
        rows = cursor.fetchall()
        return [row['album_artist'] for row in rows]
    
    @classmethod
    def albums(cls, artist: str = None):
        """
        Get all albums.
        """
        conn, cursor = connect()
        if artist is not None:
            cursor.execute("SELECT DISTINCT album_artist, album FROM tracks WHERE artist = ?", (artist,))
        else:
            cursor.execute("SELECT DISTINCT album_artist, album FROM tracks")
        rows = cursor.fetchall()
        return [(row['album_artist'], row['album']) for row in rows]

    @classmethod
    def by_artist(cls, artist: str):
        """
        Get all tracks by the given artist.
        """
        conn, cursor = connect()
        cursor.execute("SELECT * FROM tracks WHERE artist = ?", (artist,))
        rows = cursor.fetchall()
        return [cls(from_dict=dict(row)) for row in rows]
    
    @classmethod
    def by_album(cls, album: str, album_artist: str = None):
        """
        Get all tracks on the given album.
        """
        conn, cursor = connect()
        if album_artist is not None:
            cursor.execute("SELECT * FROM tracks WHERE album = ? AND album_artist = ?", (album, album_artist))
        else:
            cursor.execute("SELECT * FROM tracks WHERE album = ?", (album,))
        rows = cursor.fetchall()
        return [cls(from_dict=dict(row)) for row in rows]
    
    @classmethod
    def no_isrc(cls):
        """
        Get all tracks without an ISRC.
        """
        conn, cursor = connect()
        cursor.execute("SELECT * FROM tracks WHERE isrc = 'Unknown'")
        rows = cursor.fetchall()
        return [cls(from_dict=dict(row)) for row in rows]