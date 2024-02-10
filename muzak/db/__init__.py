from datetime import datetime
import sqlite3
import json
import os


# DB_PATH = None
# INIT_SCHEMA = """
# CREATE TABLE IF NOT EXISTS tracks (
#     id INTEGER PRIMARY KEY,
#     title TEXT,
#     artist TEXT,
#     album TEXT,
#     album_artist TEXT,
#     track INTEGER,
#     disc INTEGER,
#     genre TEXT,
#     year TEXT,
#     duration INTEGER,
#     sample_rate INTEGER,
#     bitrate INTEGER,
#     isrc TEXT,
#     path TEXT UNIQUE
# );
# """

# def connect():
#     if DB_PATH is None:
#         raise Exception("No database path set")
#     # if not os.path.exists(DB_PATH):
#     #     db = sqlite3.connect(DB_PATH)
#     #     cursor = db.cursor()
#     #     cursor.execute(INIT_SCHEMA)
#     #     db.commit()
#     #     cursor.close()
#     #     db.close()
#     db = sqlite3.connect(DB_PATH, isolation_level=None)
#     db.row_factory = sqlite3.Row
#     return db, db.cursor()

# def close(conn, cursor):
#     cursor.close()
#     conn.close()

DB_PATH = None

def connect():
    if DB_PATH is None:
        raise Exception("No database path set")

    db = sqlite3.connect(DB_PATH, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db, db.cursor()

def close(conn, cursor):
    cursor.close()
    conn.close()

def table_exists(table):
    conn, cursor = connect()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    row = cursor.fetchone()
    close(conn, cursor)
    return row is not None

class NoSuchRowError(Exception):
    pass

class Model:
    _table = None
    _fields = None
    _uniques = None
    _json_fields = None
    _dt_fields = None
    # _cached = False

    def __init__(self, from_dict=None, **kwargs):
        self._data = {}
        if from_dict is not None:
            if isinstance(from_dict, sqlite3.Row):
                from_dict = dict(from_dict)
            for field in self._fields:
                if field in from_dict:
                    if self._json_fields and field in self._json_fields and isinstance(from_dict[field], str):
                        self._data[field] = json.loads(from_dict[field])
                    elif self._json_fields and field in self._json_fields and isinstance(from_dict[field], bytes):
                        self._data[field] = json.loads(from_dict[field].decode("utf-8"))
                    else:
                        self._data[field] = from_dict[field]
        else:
            sql = "SELECT " + ", ".join(self._fields) + " FROM " + self._table + " WHERE "
            _ands = []
            _vals = []
            for field in self._uniques:
                if field in kwargs:
                    _ands.append(field + " = ?")
                    _vals.append(kwargs[field])
            sql += " AND ".join(_ands)
            conn, cursor = connect()
            try:
                cursor.execute(sql, tuple(_vals))
            except sqlite3.OperationalError as e:
                if "no such table" in str(e):
                    # Attempt to automatically create the table if we have enough information
                    if isinstance(self._fields, dict):
                        self._autocreate()
                        cursor.execute(sql, tuple(_vals))
                    else:
                        raise e
                else:
                    raise e
            row = cursor.fetchone()
            # row = dict(row)
            # close(conn, cursor)
            if row is None:
                raise NoSuchRowError("No such row: WHERE %s" % " AND ".join(_ands))
            row = dict(row)
            if self._json_fields is not None:
                for field in self._json_fields:
                    if field in row:
                        row[field] = json.loads(row[field])
            self._data = row

    def __getitem__(self, name):
        if name in self._fields:
            return self._data[name]
        raise AttributeError("No such attribute: %s" % name)

    def __setitem__(self, name, value):
        if name in self._fields:
            if name not in self._uniques:
                self._data[name] = value
                if self._json_fields is not None:
                    if name in self._json_fields:
                        value = json.dumps(value)
                if self._dt_fields is not None:
                    if name in self._dt_fields:
                        if isinstance(value, datetime):
                            value = value.isoformat()
                conn, cursor = connect()
                if "updated_at" in self._fields:
                    sql = "UPDATE " + self._table + " SET " + name + " = ?, updated_at = NOW() WHERE "
                else:
                    sql = "UPDATE " + self._table + " SET " + name + " = ? WHERE "
                _ands = []
                _vals = [value]
                for field in self._uniques:
                    _ands.append(field + " = ?")
                    _vals.append(self._data[field])
                sql += " AND ".join(_ands)
                cursor.execute(sql, tuple(_vals))
                close(conn, cursor)

    def __delitem__(self, name):
        raise Exception("Cannot delete attributes from Model objects")

    def __contains__(self, name):
        return name in self._fields

    def __repr__(self):
        return "<Model %s>" % self._table

    def __str__(self):
        return "<Model %s>" % self._table

    def __dir__(self):
        return self._fields

    @classmethod
    def _autocreate(cls):
        conn, cursor = connect()
        if isinstance(cls._fields, dict):
            _fields = []
            for field, info in cls._fields.items():
                if "type" not in info:
                    raise Exception("Missing type for field %s" % field)
                primary_key = info.get("primary_key", False)
                auto_increment = info.get("auto_increment", False)
                unique = info.get("unique", False)
                not_null = info.get("not_null", False)
                _field = field + " " + info["type"]
                if primary_key:
                    _field += " PRIMARY KEY"
                if auto_increment:
                    _field += " AUTOINCREMENT"
                if unique:
                    _field += " UNIQUE"
                if not_null:
                    _field += " NOT NULL"
                _fields.append(_field)
            cursor.execute("CREATE TABLE " + cls._table + " (" + ", ".join(_fields) + ")")

    # def _query(self, sql, *args):
    #     conn, cursor = connect()
    #     try:
    #         cursor.execute(sql, args)
    #     except sqlite3.OperationalError as e:
    #         if "no such table" in str(e):
    #             # Attempt to automatically create the table if we have enough information
    #             if isinstance(self._fields, dict):
    #                 self._autocreate()
    #                 cursor.execute(sql, args)
    #             else:
    #                 raise e
    #         else:
    #             raise e
    #     rows = cursor.fetchall()
    #     close(conn, cursor)
    #     return rows

    def delete(self):
        sql = "DELETE FROM " + self._table + " WHERE "
        _ands = []
        _vals = []
        for field in self._uniques:
            if field in self._data:
                _ands.append(field + " = ?")
                _vals.append(self._data[field])
            else:
                raise AttributeError("No such attribute: %s" % field)
        sql += " AND ".join(_ands)
        conn, cursor = connect()
        cursor.execute(sql, tuple(_vals))
        close(conn, cursor)

    def update(self, **kwargs):
        sql = "UPDATE " + self._table + " SET "
        _ands = []
        _vals = []
        for field in kwargs:
            if field in self._fields:
                _ands.append(field + " = ?")
                if field in self._json_fields:
                    _vals.append(json.dumps(kwargs[field]))
                else:
                    _vals.append(kwargs[field])
            else:
                raise AttributeError("No such attribute: %s" % field)
        sql += ", ".join(_ands)
        sql += " WHERE "
        _ands = []
        for field in self._uniques:
            if field in self._data:
                _ands.append(field + " = ?")
                _vals.append(self._data[field])
            else:
                raise AttributeError("No such attribute: %s" % field)
        sql += " AND ".join(_ands)
        conn, cursor = connect()
        cursor.execute(sql, tuple(_vals))
        close(conn, cursor)
        for field in kwargs:
            if field in self._fields:
                self._data[field] = kwargs[field]

    @classmethod
    def execute(cls, sql, *args):
        """
        
        """
        conn, cursor = connect()
        try:
            cursor.execute(sql, args)
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                # Attempt to automatically create the table if we have enough information
                if isinstance(cls._fields, dict):
                    cls._autocreate()
                    cursor.execute(sql, args)
                else:
                    raise e
            else:
                raise e
        rows = cursor.fetchall()
        close(conn, cursor)
        return rows

    @classmethod
    def where(cls, cond, *args):
        sql = "SELECT * FROM " + cls._table + " WHERE " + cond
        rows = cls.execute(sql, *args)
        return [cls(from_dict=row) for row in rows]

    @classmethod
    def count(cls, **kwargs):
        sql = "SELECT COUNT(*) FROM " + cls._table
        if len(kwargs) > 0:
            sql += " WHERE "
        else:
            conn, cursor = connect()
            cursor.execute(sql)
            row = cursor.fetchone()
            close(conn, cursor)
            return list(row.values())[0]
        _ands = []
        _vals = []
        for field in kwargs:
            _ands.append(field + " = %s")
            _vals.append(kwargs[field])
        sql += " AND ".join(_ands)
        # conn, cursor = connect()
        row = cls.execute(sql, tuple(_vals))[0]
        # row = cursor.fetchone()
        # close(conn, cursor)
        return list(row.values())[0]

    @classmethod
    def exists(cls, **kwargs):
        sql = "SELECT COUNT(*) FROM " + cls._table + " WHERE "
        _ands = []
        _vals = []
        for field in cls._uniques:
            if field in kwargs:
                _ands.append(field + " = %s")
                _vals.append(kwargs[field])
        sql += " AND ".join(_ands)
        # conn, cursor = connect()
        # cursor.execute(sql, tuple(_vals))
        # row = cursor.fetchone()
        # close(conn, cursor)
        row = cls.execute(sql, tuple(_vals))[0]
        return list(row.values())[0] > 0

    @classmethod
    def all(cls):
        # conn, cursor = connect()
        # cursor.execute("SELECT * FROM " + cls._table)
        # rows = cursor.fetchall()
        # close(conn, cursor)
        rows = cls.execute("SELECT * FROM " + cls._table)
        return [cls(from_dict=row) for row in rows]

    @classmethod
    def new(cls, **kwargs):
        sql = "INSERT INTO " + cls._table + " (" + ", ".join(cls._fields) + ") VALUES (" + ", ".join(["?"] * len(cls._fields)) + ")"
        vals = []
        for field in cls._fields:
            if field in kwargs:
                if isinstance(kwargs[field], list):
                    vals.append(json.dumps(kwargs[field]))
                elif isinstance(kwargs[field], dict):
                    vals.append(json.dumps(kwargs[field]))
                else:
                    vals.append(kwargs[field])
            elif field == "created_at":
                vals.append(datetime.now())
            elif field == "updated_at":
                vals.append(datetime.now())
            else:
                vals.append(None)
        conn, cursor = connect()
        try:
            cursor.execute(sql, tuple(vals))
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                # Attempt to automatically create the table if we have enough information
                if isinstance(cls._fields, dict):
                    cls._autocreate()
                    cursor.execute(sql, tuple(vals))
                else:
                    raise e
            else:
                raise e
        row_id = cursor.lastrowid
        # cursor.execute(sql, tuple(vals))
        # row_id = cursor.lastrowid
        if "id" in cls._fields:
            kwargs["id"] = row_id
        if "created_at" in cls._fields:
            kwargs["created_at"] = datetime.now().isoformat()
        if "updated_at" in cls._fields:
            kwargs["updated_at"] = datetime.now().isoformat()
        close(conn, cursor)
        return cls(from_dict=kwargs)

class SchemaModel(Model):
    _table = "schema_history"
    _fields = {
        "id": {
            "type": "INTEGER",
            "primary_key": True,
            "auto_increment": True
        },
        "table_name": {
            "type": "TEXT"
        },
        "schema": {
            "type": "TEXT"
        }
    }
    _uniques = [
        "id"
    ]
    _json_fields = [
        "schema"
    ]

class OldModel:
    _table = None
    _fields = None
    _uniques = None
    _json_fields = None
    _dt_fields = None
    # _cached = False

    def __init__(self, from_dict=None, **kwargs):
        self._data = {}
        if from_dict is not None:
            if isinstance(from_dict, sqlite3.Row):
                from_dict = dict(from_dict)
            for field in self._fields:
                if field in from_dict:
                    if self._json_fields and field in self._json_fields and isinstance(from_dict[field], str):
                        self._data[field] = json.loads(from_dict[field])
                    elif self._json_fields and field in self._json_fields and isinstance(from_dict[field], bytes):
                        self._data[field] = json.loads(from_dict[field].decode("utf-8"))
                    else:
                        self._data[field] = from_dict[field]
        else:
            sql = "SELECT " + ", ".join(self._fields) + " FROM " + self._table + " WHERE "
            _ands = []
            _vals = []
            for field in self._uniques:
                if field in kwargs:
                    _ands.append(field + " = ?")
                    _vals.append(kwargs[field])
            sql += " AND ".join(_ands)
            conn, cursor = connect()
            cursor.execute(sql, tuple(_vals))
            row = cursor.fetchone()
            row = dict(row)
            # close(conn, cursor)
            if row is None:
                raise Exception("No such row: WHERE %s" % " AND ".join(_ands))
            if self._json_fields is not None:
                for field in self._json_fields:
                    if field in row:
                        row[field] = json.loads(row[field])
            self._data = row

    def __getitem__(self, name):
        if name in self._fields:
            return self._data[name]
        raise AttributeError("No such attribute: %s" % name)

    def __setitem__(self, name, value):
        if name in self._fields:
            if name not in self._uniques:
                self._data[name] = value
                if self._json_fields is not None:
                    if name in self._json_fields:
                        value = json.dumps(value)
                if self._dt_fields is not None:
                    if name in self._dt_fields:
                        if isinstance(value, datetime):
                            value = value.isoformat()
                conn, cursor = connect()
                if "updated_at" in self._fields:
                    sql = "UPDATE " + self._table + " SET " + name + " = ?, updated_at = NOW() WHERE "
                else:
                    sql = "UPDATE " + self._table + " SET " + name + " = ? WHERE "
                _ands = []
                _vals = [value]
                for field in self._uniques:
                    _ands.append(field + " = ?")
                    _vals.append(self._data[field])
                sql += " AND ".join(_ands)
                cursor.execute(sql, tuple(_vals))
                close(conn, cursor)

    def __delitem__(self, name):
        raise Exception("Cannot delete attributes from Model objects")

    def __contains__(self, name):
        return name in self._fields

    def __repr__(self):
        return "<Model %s>" % self._table

    def __str__(self):
        return "<Model %s>" % self._table

    def __dir__(self):
        return self._fields

    def delete(self):
        sql = "DELETE FROM " + self._table + " WHERE "
        _ands = []
        _vals = []
        for field in self._uniques:
            if field in self._data:
                _ands.append(field + " = ?")
                _vals.append(self._data[field])
            else:
                raise AttributeError("No such attribute: %s" % field)
        sql += " AND ".join(_ands)
        conn, cursor = connect()
        cursor.execute(sql, tuple(_vals))
        close(conn, cursor)

    def update(self, **kwargs):
        sql = "UPDATE " + self._table + " SET "
        _ands = []
        _vals = []
        for field in kwargs:
            if field in self._fields:
                _ands.append(field + " = ?")
                if field in self._json_fields:
                    _vals.append(json.dumps(kwargs[field]))
                else:
                    _vals.append(kwargs[field])
            else:
                raise AttributeError("No such attribute: %s" % field)
        sql += ", ".join(_ands)
        sql += " WHERE "
        _ands = []
        for field in self._uniques:
            if field in self._data:
                _ands.append(field + " = ?")
                _vals.append(self._data[field])
            else:
                raise AttributeError("No such attribute: %s" % field)
        sql += " AND ".join(_ands)
        conn, cursor = connect()
        cursor.execute(sql, tuple(_vals))
        close(conn, cursor)
        for field in kwargs:
            if field in self._fields:
                self._data[field] = kwargs[field]

    @classmethod
    def count(cls, **kwargs):
        sql = "SELECT COUNT(*) FROM " + cls._table
        if len(kwargs) > 0:
            sql += " WHERE "
        else:
            conn, cursor = connect()
            cursor.execute(sql)
            row = cursor.fetchone()
            close(conn, cursor)
            return list(row.values())[0]
        _ands = []
        _vals = []
        for field in kwargs:
            _ands.append(field + " = %s")
            _vals.append(kwargs[field])
        sql += " AND ".join(_ands)
        conn, cursor = connect()
        cursor.execute(sql, tuple(_vals))
        row = cursor.fetchone()
        close(conn, cursor)
        return list(row.values())[0]

    @classmethod
    def exists(cls, **kwargs):
        sql = "SELECT COUNT(*) FROM " + cls._table + " WHERE "
        _ands = []
        _vals = []
        for field in cls._uniques:
            if field in kwargs:
                _ands.append(field + " = %s")
                _vals.append(kwargs[field])
        sql += " AND ".join(_ands)
        conn, cursor = connect()
        cursor.execute(sql, tuple(_vals))
        row = cursor.fetchone()
        close(conn, cursor)
        return list(row.values())[0] > 0

    @classmethod
    def all(cls):
        conn, cursor = connect()
        cursor.execute("SELECT * FROM " + cls._table)
        rows = cursor.fetchall()
        close(conn, cursor)
        return [cls(from_dict=row) for row in rows]

    @classmethod
    def new(cls, **kwargs):
        sql = "INSERT INTO " + cls._table + " (" + ", ".join(cls._fields) + ") VALUES (" + ", ".join(["?"] * len(cls._fields)) + ")"
        vals = []
        for field in cls._fields:
            if field in kwargs:
                if isinstance(kwargs[field], list):
                    vals.append(json.dumps(kwargs[field]))
                elif isinstance(kwargs[field], dict):
                    vals.append(json.dumps(kwargs[field]))
                else:
                    vals.append(kwargs[field])
            elif field == "created_at":
                vals.append(datetime.now())
            elif field == "updated_at":
                vals.append(datetime.now())
            else:
                vals.append(None)
        conn, cursor = connect()
        cursor.execute(sql, tuple(vals))
        row_id = cursor.lastrowid
        if "id" in cls._fields:
            kwargs["id"] = row_id
        if "created_at" in cls._fields:
            kwargs["created_at"] = datetime.now().isoformat()
        if "updated_at" in cls._fields:
            kwargs["updated_at"] = datetime.now().isoformat()
        close(conn, cursor)
        return cls(from_dict=kwargs)