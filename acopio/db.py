from django.conf import settings
from pymongo import MongoClient

_client: MongoClient | None = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGODB_URI)
    return _client[settings.MONGODB_DB]
