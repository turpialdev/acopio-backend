from datetime import datetime, timedelta, timezone

from bson import ObjectId
from django.contrib.auth.hashers import check_password, make_password
from pymongo.errors import DuplicateKeyError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from acopio.db import get_db
from api.auth import (
    buscar_codigo_activo,
    crear_codigo_raiz,
    require_codigo,
    require_responsable,
    token_codigo,
    token_moderador,
)
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
    CentroPublicoSerializer,
    CentroSerializer,
    ContactoEmergenciaSerializer,
    MovimientoSerializer,
    NecesidadSerializer,
    ReporteSerializer,
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


def _parse_oid(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


_VENTANA_EDICION_MINUTOS = 30


def _check_doc_centro(request, doc):
    """403 si el JWT no pertenece al mismo centro que el documento."""
    if request.auth_payload.get('centro_id') != str(doc['centro_id']):
        return Response({'detail': 'No tienes acceso a este centro.'}, status=403)
    return None


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'acopio-backend'})


# ---- auth ----

class AuthCodigoView(APIView):
    """POST /api/auth/codigo/ — canjea un código de gestión por un JWT."""

    def post(self, request):
        codigo = request.data.get('codigo', '').strip()
        if not codigo:
            return Response({'detail': 'El campo codigo es requerido.'}, status=400)

        doc = buscar_codigo_activo(codigo)
        if not doc:
            return Response({'detail': 'Código inválido o revocado.'}, status=401)

        return Response({
            'token': token_codigo(doc),
            'rol': doc['rol'],
            'centro_id': str(doc['centro_id']),
            'etiqueta': doc.get('etiqueta') or '',
        })


class AuthModeradorView(APIView):
    """POST /api/auth/moderador/ — login de moderador por email + contraseña."""

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        if not email or not password:
            return Response({'detail': 'email y password son requeridos.'}, status=400)

        doc = get_db()[MODERADORES].find_one({'email': email, 'activo': True})
        if not doc or not check_password(password, doc['password_hash']):
            return Response({'detail': 'Credenciales inválidas.'}, status=401)

        return Response({
            'token': token_moderador(doc),
            'moderador_id': str(doc['_id']),
            'nombre': doc.get('nombre') or '',
        })


# ---- centros de acopio ----

_URGENCIA_ORDEN = {'urgente': 3, 'media': 2, 'leve': 1}
_URGENCIA_LABEL = {3: 'urgente', 2: 'media', 1: 'leve', 0: None}


def _urgencias_maximas(centro_ids):
    """Devuelve un dict {str(centro_id): urgencia_maxima} para los centros dados."""
    maximas = {}
    for n in get_db()[NECESIDADES].find(
        {'centro_id': {'$in': centro_ids}},
        {'centro_id': 1, 'urgencia': 1},
    ):
        cid = str(n['centro_id'])
        maximas[cid] = max(maximas.get(cid, 0), _URGENCIA_ORDEN.get(n['urgencia'], 0))
    return maximas


class CentroListView(APIView):
    def get(self, request):
        # El directorio público nunca muestra centros ocultos (ADR 0004)
        query = {'estado_verificacion': {'$ne': 'oculto'}}
        for field in ('estado', 'municipio'):
            value = request.query_params.get(field)
            if value:
                query[field] = value
        texto = request.query_params.get('texto') or request.query_params.get('q')
        if texto:
            query['nombre'] = {'$regex': texto, '$options': 'i'}

        # Filtros que pasan por necesidades (categoria y/o urgencia)
        filtro_n = {}
        categoria = request.query_params.get('categoria')
        if categoria:
            oid = _parse_oid(categoria)
            if not oid:
                return Response({'detail': 'categoria ID inválido.'}, status=400)
            filtro_n['categoria_id'] = oid
        urgencia_param = request.query_params.get('urgencia')
        if urgencia_param:
            filtro_n['urgencia'] = urgencia_param
        if filtro_n:
            centro_ids = get_db()[NECESIDADES].distinct('centro_id', filtro_n)
            query['_id'] = {'$in': centro_ids}

        docs = list(get_db()[CENTROS_ACOPIO].find(query))
        maximas = _urgencias_maximas([d['_id'] for d in docs]) if docs else {}
        result = []
        for doc in docs:
            d = format_doc(doc)
            d['urgencia_maxima'] = _URGENCIA_LABEL[maximas.get(d['id'], 0)]
            result.append(d)
        return Response(CentroPublicoSerializer(result, many=True).data)

    def post(self, request):
        serializer = CentroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = dict(serializer.validated_data)
        doc['estado_verificacion'] = 'sin_verificar'
        doc['actualizado_en'] = _now()
        result = get_db()[CENTROS_ACOPIO].insert_one(doc)
        codigo_raiz = crear_codigo_raiz(result.inserted_id)
        created = format_doc(get_db()[CENTROS_ACOPIO].find_one({'_id': result.inserted_id}))
        return Response({**CentroSerializer(created).data, 'codigo_raiz': codigo_raiz}, status=201)


class CentroDetailView(APIView):
    def get(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        # P2: centros ocultos no se exponen en el Directorio
        if doc.get('estado_verificacion') == 'oculto':
            return Response({'detail': 'No encontrado.'}, status=404)
        db = get_db()
        necesidades_raw = list(db[NECESIDADES].find({'centro_id': doc['_id']}))
        cat_ids = list({n['categoria_id'] for n in necesidades_raw})
        cats = {c['_id']: c for c in db[CATALOGO].find({'_id': {'$in': cat_ids}})}
        max_val = 0
        necesidades = []
        for n in necesidades_raw:
            cat = cats.get(n['categoria_id'], {})
            necesidades.append({
                'id': str(n['_id']),
                'categoria_id': str(n['categoria_id']),
                'categoria_nombre': cat.get('nombre', ''),
                'urgencia': n['urgencia'],
                'detalle': n.get('detalle'),
            })
            max_val = max(max_val, _URGENCIA_ORDEN.get(n['urgencia'], 0))
        d = format_doc(doc)
        d['urgencia_maxima'] = _URGENCIA_LABEL[max_val]
        d['necesidades'] = necesidades
        return Response(CentroPublicoSerializer(d).data)

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

    def delete(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        db = get_db()
        db[NECESIDADES].delete_many({'centro_id': doc['_id']})
        db[MOVIMIENTOS].delete_many({'centro_id': doc['_id']})
        db[CODIGOS_GESTION].delete_many({'centro_id': doc['_id']})
        db[CENTROS_ACOPIO].delete_one({'_id': doc['_id']})
        return Response(status=204)


class CentroReportarView(APIView):
    """POST /api/centros/{pk}/reportar/ — P4: reporte ciudadano a cola de moderación."""

    def post(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        serializer = ReporteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reporte = dict(serializer.validated_data)
        reporte['centro_id'] = doc['_id']
        reporte['estado'] = 'pendiente'
        reporte['reportado_en'] = _now()
        get_db()[REPORTES].insert_one(reporte)
        return Response({'detail': 'Reporte recibido. El equipo de moderación lo revisará.'}, status=201)


# ---- catálogo de categorías ----

class CategoriaListView(APIView):
    def get(self, request):
        query = {}
        es_insumo = request.query_params.get('es_insumo')
        if es_insumo is not None:
            query['es_insumo'] = es_insumo.lower() in ('1', 'true', 'yes')
        activa = request.query_params.get('activa')
        if activa is not None:
            query['activa'] = activa.lower() in ('1', 'true', 'yes')
        docs = [format_doc(d) for d in get_db()[CATALOGO].find(query)]
        return Response(CategoriaSerializer(docs, many=True).data)

    def post(self, request):
        serializer = CategoriaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = get_db()[CATALOGO].insert_one(dict(serializer.validated_data))
        except DuplicateKeyError:
            return Response({'nombre': ['Ya existe una categoría con ese nombre.']}, status=400)
        doc = format_doc(get_db()[CATALOGO].find_one({'_id': result.inserted_id}))
        return Response(CategoriaSerializer(doc).data, status=201)


class CategoriaDetailView(APIView):
    def get(self, request, pk):
        doc, err = _get_doc(CATALOGO, pk)
        if err:
            return err
        return Response(CategoriaSerializer(format_doc(doc)).data)

    def patch(self, request, pk):
        doc, err = _get_doc(CATALOGO, pk)
        if err:
            return err
        serializer = CategoriaSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            get_db()[CATALOGO].update_one(
                {'_id': doc['_id']}, {'$set': dict(serializer.validated_data)}
            )
        except DuplicateKeyError:
            return Response({'nombre': ['Ya existe una categoría con ese nombre.']}, status=400)
        updated = format_doc(get_db()[CATALOGO].find_one({'_id': doc['_id']}))
        return Response(CategoriaSerializer(updated).data)

    def delete(self, request, pk):
        doc, err = _get_doc(CATALOGO, pk)
        if err:
            return err
        db = get_db()
        db[NECESIDADES].delete_many({'categoria_id': doc['_id']})
        db[MOVIMIENTOS].delete_many({'categoria_id': doc['_id']})
        db[CATALOGO].delete_one({'_id': doc['_id']})
        return Response(status=204)


# ---- necesidades (líneas de la ficha) ----

class NecesidadListView(APIView):
    def get(self, request):
        query = {}
        centro_id = request.query_params.get('centro_id')
        if centro_id:
            oid = _parse_oid(centro_id)
            if oid is None:
                return Response({'detail': 'centro_id inválido.'}, status=400)
            query['centro_id'] = oid
        urgencia = request.query_params.get('urgencia')
        if urgencia:
            query['urgencia'] = urgencia
        docs = [format_doc(d) for d in get_db()[NECESIDADES].find(query)]
        return Response(NecesidadSerializer(docs, many=True).data)

    def post(self, request):
        serializer = NecesidadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = get_db()[NECESIDADES].insert_one(dict(serializer.validated_data))
        except DuplicateKeyError:
            return Response(
                {'detail': 'El centro ya tiene una necesidad para esa categoría.'},
                status=400,
            )
        doc = format_doc(get_db()[NECESIDADES].find_one({'_id': result.inserted_id}))
        return Response(NecesidadSerializer(doc).data, status=201)


class NecesidadDetailView(APIView):
    def get(self, request, pk):
        doc, err = _get_doc(NECESIDADES, pk)
        if err:
            return err
        return Response(NecesidadSerializer(format_doc(doc)).data)

    def patch(self, request, pk):
        doc, err = _get_doc(NECESIDADES, pk)
        if err:
            return err
        serializer = NecesidadSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        get_db()[NECESIDADES].update_one(
            {'_id': doc['_id']}, {'$set': dict(serializer.validated_data)}
        )
        updated = format_doc(get_db()[NECESIDADES].find_one({'_id': doc['_id']}))
        return Response(NecesidadSerializer(updated).data)

    def delete(self, request, pk):
        doc, err = _get_doc(NECESIDADES, pk)
        if err:
            return err
        get_db()[NECESIDADES].delete_one({'_id': doc['_id']})
        return Response(status=204)


# ---- movimientos (inventario: libro de entradas/salidas) ----

class MovimientoListView(APIView):
    @require_codigo
    def get(self, request):
        # Siempre filtra por el centro del JWT — un voluntario no puede ver otros centros (V4)
        centro_oid = _parse_oid(request.auth_payload['centro_id'])
        query = {'centro_id': centro_oid}
        tipo = request.query_params.get('tipo')
        if tipo:
            query['tipo'] = tipo
        cursor = get_db()[MOVIMIENTOS].find(query).sort('registrado_en', -1)
        docs = [format_doc(d) for d in cursor]
        return Response(MovimientoSerializer(docs, many=True).data)

    @require_codigo
    def post(self, request):
        # centro_id viene del JWT, no del cuerpo (V2: voluntario registra en su centro)
        payload = request.auth_payload
        data = {k: v for k, v in request.data.items() if k != 'centro_id'}
        data['centro_id'] = payload['centro_id']
        serializer = MovimientoSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        doc = dict(serializer.validated_data)
        doc['registrado_por'] = payload.get('etiqueta') or ''
        doc['codigo_id'] = ObjectId(payload['codigo_id'])
        doc['registrado_en'] = _now()
        result = get_db()[MOVIMIENTOS].insert_one(doc)
        created = format_doc(get_db()[MOVIMIENTOS].find_one({'_id': result.inserted_id}))
        return Response(MovimientoSerializer(created).data, status=201)


class MovimientoDetailView(APIView):
    @require_codigo
    def get(self, request, pk):
        doc, err = _get_doc(MOVIMIENTOS, pk)
        if err:
            return err
        err = _check_doc_centro(request, doc)
        if err:
            return err
        return Response(MovimientoSerializer(format_doc(doc)).data)

    @require_codigo
    def patch(self, request, pk):
        doc, err = _get_doc(MOVIMIENTOS, pk)
        if err:
            return err
        err = _check_doc_centro(request, doc)
        if err:
            return err
        payload = request.auth_payload
        if payload.get('rol') == 'voluntario':
            codigo_oid = _parse_oid(payload.get('codigo_id', ''))
            if doc.get('codigo_id') != codigo_oid:
                return Response(
                    {'detail': 'Solo puedes corregir tus propios registros.'}, status=403
                )
            ventana = _now() - timedelta(minutes=_VENTANA_EDICION_MINUTOS)
            if doc['registrado_en'].replace(tzinfo=timezone.utc) < ventana:
                return Response(
                    {'detail': f'Solo puedes corregir registros de los últimos {_VENTANA_EDICION_MINUTOS} minutos.'},
                    status=403,
                )
        # centro_id y categoria_id son inmutables tras el registro
        data = {k: v for k, v in request.data.items() if k not in ('centro_id', 'categoria_id')}
        serializer = MovimientoSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        get_db()[MOVIMIENTOS].update_one(
            {'_id': doc['_id']}, {'$set': dict(serializer.validated_data)}
        )
        updated = format_doc(get_db()[MOVIMIENTOS].find_one({'_id': doc['_id']}))
        return Response(MovimientoSerializer(updated).data)

    @require_responsable
    def delete(self, request, pk):
        doc, err = _get_doc(MOVIMIENTOS, pk)
        if err:
            return err
        err = _check_doc_centro(request, doc)
        if err:
            return err
        get_db()[MOVIMIENTOS].delete_one({'_id': doc['_id']})
        return Response(status=204)


# ---- contactos de emergencia (P5) ----

class ContactoEmergenciaListView(APIView):
    """GET /api/contactos-emergencia/ — directorio público, sin auth."""

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


# ---- sugerencias de inventario (R8) ----

class SugerenciasView(APIView):
    """GET /api/centros/{pk}/sugerencias/ — señales del inventario para el responsable.

    Por cada categoría donde hoy salió más de lo que entró, devuelve una sugerencia
    para revisar la urgencia en la ficha. El sistema sugiere; el humano publica (ADR 0005).
    """

    @require_codigo
    def get(self, request, pk):
        if request.auth_payload.get('centro_id') != pk:
            return Response({'detail': 'No tienes acceso a este centro.'}, status=403)

        centro_oid = _parse_oid(pk)
        if not centro_oid:
            return Response({'detail': 'ID inválido.'}, status=400)

        hoy = _now().replace(hour=0, minute=0, second=0, microsecond=0)
        cursor = get_db()[MOVIMIENTOS].find({
            'centro_id': centro_oid,
            'registrado_en': {'$gte': hoy},
        })

        totales = {}
        for mov in cursor:
            cid = mov['categoria_id']
            if cid not in totales:
                totales[cid] = {'entradas': 0.0, 'salidas': 0.0}
            cant = mov.get('cantidad') or 0.0
            if mov['tipo'] == 'entrada':
                totales[cid]['entradas'] += cant
            else:
                totales[cid]['salidas'] += cant

        if not totales:
            return Response({'sugerencias': []})

        cat_ids = list(totales.keys())
        cats = {c['_id']: c for c in get_db()[CATALOGO].find({'_id': {'$in': cat_ids}})}
        necesidades = {
            n['categoria_id']: n
            for n in get_db()[NECESIDADES].find({
                'centro_id': centro_oid,
                'categoria_id': {'$in': cat_ids},
            })
        }

        sugerencias = []
        for cid, t in totales.items():
            if t['salidas'] > t['entradas']:
                cat = cats.get(cid, {})
                nec = necesidades.get(cid)
                nombre_cat = cat.get('nombre', 'insumo')
                sugerencias.append({
                    'categoria_id': str(cid),
                    'categoria_nombre': nombre_cat,
                    'entradas_hoy': t['entradas'],
                    'salidas_hoy': t['salidas'],
                    'urgencia_actual': nec['urgencia'] if nec else None,
                    'mensaje': (
                        f"Hoy salió más {nombre_cat} del que entró. "
                        "Considera revisar la urgencia en la ficha."
                    ),
                })

        return Response({'sugerencias': sugerencias})
