# encoding: utf-8
import pymysql
from model.dao import MongoDataModel
from util import db_pool
from util.tools import Log

logger = Log().getLog()


class BaseModel(object):
    def __init__(self):
        self.conn_r = db_pool.get_mysql("betblock_r")
        self.conn_w = db_pool.get_mysql("betblock_w")
        self.conn = None
        self.cursor = None
        self.dao = MongoDataModel()
        self.state = False
        self.lazy_commit = False

    def __del__(self):
        if self.conn:
            self.conn.close()

    def clean_conn(self):
        if self.conn_r:
            self.conn_r.close()
        if self.conn_w:
            self.conn_w.close()

    def commit(self):
        if self.lazy_commit:
            pass
        else:
            self.conn.commit()

    def rollback(self):
        if self.lazy_commit:
            pass
        else:
            self.conn.rollback()


def transaction(cursor='dict'):
    def _wrapper(f):
        def __wrapper(*args, **kwargs):
            obj = args[0]
            try:
                if obj.conn is None:
                    setattr(obj, 'conn', getattr(obj, 'conn_w'))
                elif id(obj.conn) == id(obj.conn_r):
                    setattr(obj, 'conn', getattr(obj, 'conn_w'))

                if cursor == 'list':
                    setattr(obj, 'cursor', obj.conn.cursor())
                else:
                    setattr(obj, 'cursor', obj.conn.cursor(pymysql.cursors.DictCursor))

                setattr(obj, 'lazy_commit', True)
                ret = f(*args, **kwargs)
                setattr(obj, 'lazy_commit', False)
                obj.commit()
                return ret
            except:
                setattr(obj, 'lazy_commit', False)
                obj.rollback()
        return __wrapper
    return _wrapper


def access(level, cursor='dict'):
    def _wrapper(f):
        def __wrapper(*args, **kwargs):
            obj = args[0]
            if level == 'r':
                if obj.conn is None:
                    setattr(obj, 'conn', getattr(obj, 'conn_r'))
            elif level == 'w':
                if obj.conn is None:
                    setattr(obj, 'conn', getattr(obj, 'conn_w'))
                elif id(obj.conn) == id(obj.conn_r):
                    setattr(obj, 'conn', getattr(obj, 'conn_w'))
            else:
                pass  # default attribute

            if cursor == 'list':
                setattr(obj, 'cursor', obj.conn.cursor())
            else:
                setattr(obj, 'cursor', obj.conn.cursor(pymysql.cursors.DictCursor))
            return f(*args, **kwargs)
        return __wrapper
    return _wrapper
