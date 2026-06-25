import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from django.conf import settings
from rest_framework.response import Response

from acopio.db import get_db
from api.models import CODIGOS_GESTION


# ---- Utilidades de código ----

def generar_codigo() -> str:
    """Código opaco y aleatorio; seguro para dictar por voz o SMS."""
    return secrets.token_urlsafe(32)


def hashear_codigo(valor: str) -> str:
    """SHA-256 del código. Los códigos son strings aleatorios de alta entropía."""
    return hashlib.sha256(valor.encode()).hexdigest()


def buscar_codigo_activo(valor: str) -> dict | None:
    """Devuelve el documento del código si existe y no está revocado."""
    return get_db()[CODIGOS_GESTION].find_one({
        'valor_hash': hashear_codigo(valor),
        'revocado_en': None,
    })


def crear_codigo_raiz(centro_id) -> str:
    """Genera y persiste el código raíz al registrar un centro. Devuelve el texto plano una sola vez."""
    codigo = generar_codigo()
    get_db()[CODIGOS_GESTION].insert_one({
        'centro_id': centro_id,
        'valor_hash': hashear_codigo(codigo),
        'rol': 'responsable',
        'etiqueta': 'Responsable',
        'creado_por': None,
        'revocado_en': None,
    })
    return codigo


# ---- JWT ----

def _encode(payload: dict) -> str:
    data = {
        **payload,
        'exp': datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRATION_DAYS),
    }
    return jwt.encode(data, settings.JWT_SECRET, algorithm='HS256')


def _decode(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=['HS256'])
    except jwt.PyJWTError:
        return None


def _bearer_token(request) -> str | None:
    auth = request.headers.get('Authorization', '')
    return auth[7:] if auth.startswith('Bearer ') else None


def token_codigo(doc: dict) -> str:
    return _encode({
        'tipo': 'codigo',
        'centro_id': str(doc['centro_id']),
        'rol': doc['rol'],
        'codigo_id': str(doc['_id']),
        'etiqueta': doc.get('etiqueta') or '',
    })


def token_moderador(doc: dict) -> str:
    return _encode({
        'tipo': 'moderador',
        'moderador_id': str(doc['_id']),
        'nombre': doc.get('nombre') or '',
    })


# ---- Extracción de payload (uso interno) ----

def _get_codigo_payload(request):
    """Retorna el payload del JWT o un Response de error."""
    token = _bearer_token(request)
    if not token:
        return Response({'detail': 'Token requerido.'}, status=401)
    payload = _decode(token)
    if not payload or payload.get('tipo') != 'codigo':
        return Response({'detail': 'Token inválido.'}, status=401)
    return payload


def _get_moderador_payload(request):
    token = _bearer_token(request)
    if not token:
        return Response({'detail': 'Token requerido.'}, status=401)
    payload = _decode(token)
    if not payload or payload.get('tipo') != 'moderador':
        return Response({'detail': 'Token inválido.'}, status=401)
    return payload


# ---- Decoradores para métodos de APIView ----

def require_codigo(fn):
    """Cualquier código de gestión válido. Inyecta request.auth_payload."""
    @wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        result = _get_codigo_payload(request)
        if isinstance(result, Response):
            return result
        request.auth_payload = result
        return fn(self, request, *args, **kwargs)
    return wrapper


def require_responsable(fn):
    """Código de gestión con rol=responsable."""
    @wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        result = _get_codigo_payload(request)
        if isinstance(result, Response):
            return result
        if result.get('rol') != 'responsable':
            return Response({'detail': 'Se requiere rol responsable.'}, status=403)
        request.auth_payload = result
        return fn(self, request, *args, **kwargs)
    return wrapper


def require_moderador(fn):
    """Cuenta de moderador."""
    @wraps(fn)
    def wrapper(self, request, *args, **kwargs):
        result = _get_moderador_payload(request)
        if isinstance(result, Response):
            return result
        request.auth_payload = result
        return fn(self, request, *args, **kwargs)
    return wrapper


def check_centro(request, pk: str) -> Response | None:
    """Verifica que el centro_id del JWT coincida con el pk de la URL. Retorna 403 si no."""
    if request.auth_payload.get('centro_id') != pk:
        return Response({'detail': 'No tienes acceso a este centro.'}, status=403)
    return None
