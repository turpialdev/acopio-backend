from urllib.parse import quote_plus

from django.conf import settings
from pymongo import MongoClient

_client: MongoClient | None = None


def _encode_credentials(uri: str) -> str:
    """Percent-encode username/password in a MongoDB URI so a raw password
    (with chars like @ : / #) can be stored directly in MONGODB_URI."""
    scheme, sep, rest = uri.partition('://')
    if not sep or '@' not in rest:
        return uri
    userinfo, _, hostpart = rest.rpartition('@')
    username, has_pass, password = userinfo.partition(':')
    encoded = quote_plus(username)
    if has_pass:
        encoded += ':' + quote_plus(password)
    return f'{scheme}://{encoded}@{hostpart}'


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(_encode_credentials(settings.MONGODB_URI))
    return _client[settings.MONGODB_DB]
