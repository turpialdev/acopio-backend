from datetime import datetime, timezone

from bson import ObjectId
from django.contrib.auth.hashers import make_password
from pymongo.errors import DuplicateKeyError
from rest_framework.response import Response
from rest_framework.views import APIView

from acopio.db import get_db
from api.auth import crear_codigo_raiz, require_moderador
from api.models import (
    CATALOGO,
    CENTROS_ACOPIO,
    CODIGOS_GESTION,
    CONTACTOS_EMERGENCIA,
    MODERADORES,
    MOVIMIENTOS,
    NECESIDADES,
    REPORTES,
)
from api.serializers import (
    CategoriaSerializer,
    CentroSerializer,
    ContactoEmergenciaSerializer,
    format_doc,
)


def _now():
    return datetime.now(timezone.utc)


def _get_doc(collection, pk):
    try:
        oid = ObjectId(pk)
    except Exception:
        return None, Response({'detail': 'ID inválido.'}, status=400)
    doc = get_db()[collection].find_one({'_id': oid})
    if not doc:
        return None, Response({'detail': 'No encontrado.'}, status=404)
    return doc, None


def _format_moderador(doc):
    d = format_doc(doc)
    d.pop('password_hash', None)
    return d


# ---- M1: Cola de trabajo ----

class ColaView(APIView):
    """GET /api/mod/cola/"""

    @require_moderador
    def get(self, request):
        db = get_db()
        centros = [
            format_doc(d) for d in db[CENTROS_ACOPIO]
            .find({'estado_verificacion': 'sin_verificar'})
            .sort('actualizado_en', -1)
        ]
        reportes = [
            format_doc(d) for d in db[REPORTES]
            .find({'resuelto': False})
            .sort('creado_en', -1)
        ]
        return Response({
            'centros_sin_verificar': centros,
            'reportes_pendientes': reportes,
        })


# ---- M7: Centros (vista completa, incluyendo ocultos) ----

class ModCentroListView(APIView):
    """GET /api/mod/centros/ — lista todos; POST — crea verificado"""

    @require_moderador
    def get(self, request):
        query = {}
        for field in ('estado', 'municipio', 'estado_verificacion'):
            v = request.query_params.get(field)
            if v:
                query[field] = v
        q = request.query_params.get('q')
        if q:
            query['nombre'] = {'$regex': q, '$options': 'i'}
        docs = [format_doc(d) for d in get_db()[CENTROS_ACOPIO].find(query).sort('actualizado_en', -1)]
        return Response(CentroSerializer(docs, many=True).data)

    @require_moderador
    def post(self, request):
        serializer = CentroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = dict(serializer.validated_data)
        doc['estado_verificacion'] = 'verificado'
        doc['actualizado_en'] = _now()
        result = get_db()[CENTROS_ACOPIO].insert_one(doc)
        codigo_raiz = crear_codigo_raiz(result.inserted_id)
        created = format_doc(get_db()[CENTROS_ACOPIO].find_one({'_id': result.inserted_id}))
        return Response({**CentroSerializer(created).data, 'codigo_raiz': codigo_raiz}, status=201)


class ModCentroDetailView(APIView):
    """GET/PATCH /api/mod/centros/{id}/"""

    @require_moderador
    def get(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        return Response(CentroSerializer(format_doc(doc)).data)

    @require_moderador
    def patch(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        serializer = CentroSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update = dict(serializer.validated_data)
        update['actualizado_en'] = _now()
        get_db()[CENTROS_ACOPIO].update_one({'_id': doc['_id']}, {'$set': update})
        updated = format_doc(get_db()[CENTROS_ACOPIO].find_one({'_id': doc['_id']}))
        return Response(CentroSerializer(updated).data)


# ---- M2: Verificar / ocultar ----

class ModVerificarView(APIView):
    """POST /api/mod/centros/{id}/verificar/"""

    @require_moderador
    def post(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        get_db()[CENTROS_ACOPIO].update_one(
            {'_id': doc['_id']},
            {'$set': {'estado_verificacion': 'verificado', 'actualizado_en': _now()}},
        )
        updated = format_doc(get_db()[CENTROS_ACOPIO].find_one({'_id': doc['_id']}))
        return Response(CentroSerializer(updated).data)


class ModOcultarView(APIView):
    """POST /api/mod/centros/{id}/ocultar/"""

    @require_moderador
    def post(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        get_db()[CENTROS_ACOPIO].update_one(
            {'_id': doc['_id']},
            {'$set': {'estado_verificacion': 'oculto', 'actualizado_en': _now()}},
        )
        updated = format_doc(get_db()[CENTROS_ACOPIO].find_one({'_id': doc['_id']}))
        return Response(CentroSerializer(updated).data)


# ---- M4: Reemitir código raíz ----

class ModReemitirCodigoView(APIView):
    """POST /api/mod/centros/{id}/reemitir-codigo/"""

    @require_moderador
    def post(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        get_db()[CODIGOS_GESTION].update_many(
            {'centro_id': doc['_id'], 'rol': 'responsable', 'revocado_en': None},
            {'$set': {'revocado_en': _now()}},
        )
        nuevo = crear_codigo_raiz(doc['_id'])
        return Response({'codigo_raiz': nuevo})


# ---- M3: Fusionar duplicados ----

class ModFusionarView(APIView):
    """POST /api/mod/centros/fusionar/"""

    @require_moderador
    def post(self, request):
        centro_a_id = (request.data.get('centro_a') or '').strip()
        centro_b_id = (request.data.get('centro_b') or '').strip()
        conservar_id = (request.data.get('conservar') or '').strip()

        if not all([centro_a_id, centro_b_id, conservar_id]):
            return Response({'detail': 'centro_a, centro_b y conservar son requeridos.'}, status=400)

        centro_a, err = _get_doc(CENTROS_ACOPIO, centro_a_id)
        if err:
            return err
        centro_b, err = _get_doc(CENTROS_ACOPIO, centro_b_id)
        if err:
            return err

        ids_validos = {str(centro_a['_id']), str(centro_b['_id'])}
        if conservar_id not in ids_validos:
            return Response({'detail': 'conservar debe ser el id de centro_a o centro_b.'}, status=400)

        conservar_oid = ObjectId(conservar_id)
        descartar_oid = centro_b['_id'] if conservar_id == str(centro_a['_id']) else centro_a['_id']

        db = get_db()
        # Reasignar movimientos y códigos al centro conservado
        db[MOVIMIENTOS].update_many({'centro_id': descartar_oid}, {'$set': {'centro_id': conservar_oid}})
        db[CODIGOS_GESTION].update_many({'centro_id': descartar_oid}, {'$set': {'centro_id': conservar_oid}})
        # Necesidades: migrar solo las categorías que el conservado no tenga ya
        cats_existentes = {n['categoria_id'] for n in db[NECESIDADES].find({'centro_id': conservar_oid})}
        for n in db[NECESIDADES].find({'centro_id': descartar_oid}):
            if n['categoria_id'] not in cats_existentes:
                db[NECESIDADES].update_one({'_id': n['_id']}, {'$set': {'centro_id': conservar_oid}})
        db[NECESIDADES].delete_many({'centro_id': descartar_oid})
        # Ocultar el descartado
        db[CENTROS_ACOPIO].update_one(
            {'_id': descartar_oid},
            {'$set': {'estado_verificacion': 'oculto', 'actualizado_en': _now()}},
        )

        conservado = format_doc(db[CENTROS_ACOPIO].find_one({'_id': conservar_oid}))
        return Response({
            'conservado': CentroSerializer(conservado).data,
            'descartado_id': str(descartar_oid),
        })


# ---- Reportes ciudadanos ----

class ModReporteListView(APIView):
    """GET /api/mod/reportes/"""

    @require_moderador
    def get(self, request):
        query = {}
        estado = request.query_params.get('estado')
        if estado == 'resuelto':
            query['resuelto'] = True
        elif estado == 'pendiente':
            query['resuelto'] = False
        docs = [format_doc(d) for d in get_db()[REPORTES].find(query).sort('creado_en', -1)]
        return Response(docs)


class ModReporteResolverView(APIView):
    """POST /api/mod/reportes/{id}/resolver/"""

    @require_moderador
    def post(self, request, pk):
        doc, err = _get_doc(REPORTES, pk)
        if err:
            return err
        get_db()[REPORTES].update_one(
            {'_id': doc['_id']},
            {'$set': {
                'resuelto': True,
                'resuelto_en': _now(),
                'resuelto_por': request.auth_payload.get('moderador_id'),
            }},
        )
        return Response(format_doc(get_db()[REPORTES].find_one({'_id': doc['_id']})))


# ---- M5: Catálogo (vista completa, incluyendo inactivas) ----

class ModCatalogoListView(APIView):
    """GET/POST /api/mod/catalogo/"""

    @require_moderador
    def get(self, request):
        docs = [format_doc(d) for d in get_db()[CATALOGO].find()]
        return Response(CategoriaSerializer(docs, many=True).data)

    @require_moderador
    def post(self, request):
        serializer = CategoriaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = get_db()[CATALOGO].insert_one(dict(serializer.validated_data))
        except DuplicateKeyError:
            return Response({'nombre': ['Ya existe una categoría con ese nombre.']}, status=400)
        doc = format_doc(get_db()[CATALOGO].find_one({'_id': result.inserted_id}))
        return Response(CategoriaSerializer(doc).data, status=201)


class ModCatalogoDetailView(APIView):
    """PATCH /api/mod/catalogo/{id}/"""

    @require_moderador
    def patch(self, request, pk):
        doc, err = _get_doc(CATALOGO, pk)
        if err:
            return err
        serializer = CategoriaSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            get_db()[CATALOGO].update_one({'_id': doc['_id']}, {'$set': dict(serializer.validated_data)})
        except DuplicateKeyError:
            return Response({'nombre': ['Ya existe una categoría con ese nombre.']}, status=400)
        updated = format_doc(get_db()[CATALOGO].find_one({'_id': doc['_id']}))
        return Response(CategoriaSerializer(updated).data)


# ---- M6: Cuentas de moderador ----

class ModeradorListView(APIView):
    """GET/POST /api/mod/moderadores/"""

    @require_moderador
    def get(self, request):
        docs = [_format_moderador(d) for d in get_db()[MODERADORES].find()]
        return Response(docs)

    @require_moderador
    def post(self, request):
        nombre = (request.data.get('nombre') or '').strip()
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''
        if not nombre or not email or not password:
            return Response({'detail': 'nombre, email y password son requeridos.'}, status=400)
        if get_db()[MODERADORES].find_one({'email': email}):
            return Response({'detail': 'Ya existe un moderador con ese email.'}, status=400)
        result = get_db()[MODERADORES].insert_one({
            'nombre': nombre,
            'email': email,
            'password_hash': make_password(password),
            'activo': True,
            'creado_en': _now(),
        })
        return Response(_format_moderador(get_db()[MODERADORES].find_one({'_id': result.inserted_id})), status=201)


class ModeradorDetailView(APIView):
    """DELETE /api/mod/moderadores/{id}/"""

    @require_moderador
    def delete(self, request, pk):
        doc, err = _get_doc(MODERADORES, pk)
        if err:
            return err
        if str(doc['_id']) == request.auth_payload.get('moderador_id'):
            return Response({'detail': 'No puedes desactivar tu propia cuenta.'}, status=400)
        get_db()[MODERADORES].update_one({'_id': doc['_id']}, {'$set': {'activo': False}})
        return Response(status=204)


# ---- P5: Contactos de emergencia ----

class ModContactoEmergenciaListView(APIView):
    """GET/POST /api/mod/contactos-emergencia/"""

    @require_moderador
    def get(self, request):
        query = {}
        zona = request.query_params.get('zona')
        if zona:
            query['zona'] = {'$regex': zona, '$options': 'i'}
        tipo = request.query_params.get('tipo')
        if tipo:
            query['tipo'] = tipo
        docs = [
            format_doc(d)
            for d in get_db()[CONTACTOS_EMERGENCIA].find(query).sort('nombre', 1)
        ]
        return Response(ContactoEmergenciaSerializer(docs, many=True).data)

    @require_moderador
    def post(self, request):
        serializer = ContactoEmergenciaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = get_db()[CONTACTOS_EMERGENCIA].insert_one(dict(serializer.validated_data))
        doc = format_doc(get_db()[CONTACTOS_EMERGENCIA].find_one({'_id': result.inserted_id}))
        return Response(ContactoEmergenciaSerializer(doc).data, status=201)


class ModContactoEmergenciaDetailView(APIView):
    """PATCH/DELETE /api/mod/contactos-emergencia/{id}/"""

    @require_moderador
    def patch(self, request, pk):
        doc, err = _get_doc(CONTACTOS_EMERGENCIA, pk)
        if err:
            return err
        serializer = ContactoEmergenciaSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        get_db()[CONTACTOS_EMERGENCIA].update_one(
            {'_id': doc['_id']}, {'$set': dict(serializer.validated_data)}
        )
        updated = format_doc(get_db()[CONTACTOS_EMERGENCIA].find_one({'_id': doc['_id']}))
        return Response(ContactoEmergenciaSerializer(updated).data)

    @require_moderador
    def delete(self, request, pk):
        doc, err = _get_doc(CONTACTOS_EMERGENCIA, pk)
        if err:
            return err
        get_db()[CONTACTOS_EMERGENCIA].delete_one({'_id': doc['_id']})
        return Response(status=204)


# ---- M8: Métricas (deseable) ----

class MetricasView(APIView):
    """GET /api/mod/metricas/"""

    @require_moderador
    def get(self, request):
        db = get_db()
        return Response({
            'centros': {
                'total': db[CENTROS_ACOPIO].count_documents({'estado_verificacion': {'$ne': 'oculto'}}),
                'verificados': db[CENTROS_ACOPIO].count_documents({'estado_verificacion': 'verificado'}),
                'sin_verificar': db[CENTROS_ACOPIO].count_documents({'estado_verificacion': 'sin_verificar'}),
                'ocultos': db[CENTROS_ACOPIO].count_documents({'estado_verificacion': 'oculto'}),
            },
            'necesidades_urgentes': db[NECESIDADES].count_documents({'urgencia': 'urgente'}),
            'movimientos_total': db[MOVIMIENTOS].count_documents({}),
        })
