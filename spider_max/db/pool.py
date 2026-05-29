"""Spider Max — DB连接池与配置"""
from spider_max.db import DatabaseManager

db = DatabaseManager()


def get_db() -> DatabaseManager:
    return db
