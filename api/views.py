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
    check_centro,
    crear_codigo_raiz,
    generar_codigo,
    hashear_codigo,
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
        reporte['resuelto'] = False
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
        categoria_id = request.query_params.get('categoria_id')
        if categoria_id:
            oid = _parse_oid(categoria_id)
            if not oid:
                return Response({'detail': 'categoria_id inválido.'}, status=400)
            query['categoria_id'] = oid
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


# ---- Panel de gestión del centro (R3–R6, V2–V4) ----
# Todos requieren JWT de código de gestión.
# check_centro verifica que centro_id del token coincida con centro_pk de la URL.

_VENTANA_CORRECCION_SEGUNDOS = 3600  # voluntarios: 1 hora para corregir sus registros


def _build_ficha(centro_doc):
    db = get_db()
    needs = list(db[NECESIDADES].find({'centro_id': centro_doc['_id']}))
    cat_ids = [n['categoria_id'] for n in needs]
    cats = {c['_id']: c['nombre'] for c in db[CATALOGO].find({'_id': {'$in': cat_ids}})}
    necesidades_out = []
    for n in needs:
        nd = format_doc(n)
        nd['categoria_nombre'] = cats.get(n['categoria_id'], '')
        necesidades_out.append(nd)
    return {**CentroSerializer(format_doc(centro_doc)).data, 'necesidades': necesidades_out}


def _format_codigo(doc):
    d = format_doc(doc)
    d.pop('valor_hash', None)
    if d.get('creado_por'):
        d['creado_por'] = str(d['creado_por'])
    return d


class FichaView(APIView):
    """GET/PATCH /api/centros/{id}/ficha/ — R3"""

    @require_codigo
    def get(self, request, centro_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        doc, err = _get_doc(CENTROS_ACOPIO, centro_pk)
        if err:
            return err
        return Response(_build_ficha(doc))

    @require_responsable
    def patch(self, request, centro_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        doc, err = _get_doc(CENTROS_ACOPIO, centro_pk)
        if err:
            return err
        data = {k: v for k, v in request.data.items() if k not in ('necesidades', 'estado_verificacion')}
        necesidades_data = request.data.get('necesidades')
        if data:
            serializer = CentroSerializer(data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            update = dict(serializer.validated_data)
            update['actualizado_en'] = _now()
            get_db()[CENTROS_ACOPIO].update_one({'_id': doc['_id']}, {'$set': update})
        else:
            get_db()[CENTROS_ACOPIO].update_one({'_id': doc['_id']}, {'$set': {'actualizado_en': _now()}})
        if necesidades_data is not None:
            db = get_db()
            db[NECESIDADES].delete_many({'centro_id': doc['_id']})
            for item in necesidades_data:
                item_data = {**item, 'centro_id': str(doc['_id'])}
                s = NecesidadSerializer(data=item_data)
                s.is_valid(raise_exception=True)
                db[NECESIDADES].insert_one(dict(s.validated_data))
        updated = get_db()[CENTROS_ACOPIO].find_one({'_id': doc['_id']})
        return Response(_build_ficha(updated))


class GestionMovimientoListView(APIView):
    """GET/POST /api/centros/{id}/movimientos/ — R4, R5, V2, V4"""

    @require_codigo
    def get(self, request, centro_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        doc, err = _get_doc(CENTROS_ACOPIO, centro_pk)
        if err:
            return err
        query = {'centro_id': doc['_id']}
        if request.query_params.get('tipo'):
            query['tipo'] = request.query_params['tipo']
        if request.query_params.get('categoria_id'):
            oid = _parse_oid(request.query_params['categoria_id'])
            if oid:
                query['categoria_id'] = oid
        cursor = get_db()[MOVIMIENTOS].find(query).sort('registrado_en', -1)
        return Response(MovimientoSerializer([format_doc(d) for d in cursor], many=True).data)

    @require_codigo
    def post(self, request, centro_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        doc, err = _get_doc(CENTROS_ACOPIO, centro_pk)
        if err:
            return err
        data = {**request.data, 'centro_id': centro_pk}
        serializer = MovimientoSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        mov = dict(serializer.validated_data)
        mov['registrado_en'] = _now()
        mov['registrado_por'] = request.auth_payload.get('etiqueta') or ''
        mov['codigo_id'] = ObjectId(request.auth_payload['codigo_id'])
        result = get_db()[MOVIMIENTOS].insert_one(mov)
        created = format_doc(get_db()[MOVIMIENTOS].find_one({'_id': result.inserted_id}))
        return Response(MovimientoSerializer(created).data, status=201)


class GestionMovimientoDetailView(APIView):
    """PATCH/DELETE /api/centros/{id}/movimientos/{mov_id}/ — R5, V3"""

    def _get_mov_autorizado(self, request, centro_pk, mov_pk):
        mov, err = _get_doc(MOVIMIENTOS, mov_pk)
        if err:
            return None, err
        if str(mov['centro_id']) != centro_pk:
            return None, Response({'detail': 'No encontrado.'}, status=404)
        if request.auth_payload.get('rol') == 'voluntario':
            if str(mov.get('codigo_id', '')) != request.auth_payload['codigo_id']:
                return None, Response({'detail': 'Solo puedes modificar tus propios registros.'}, status=403)
            antiguedad = (_now() - mov['registrado_en'].replace(tzinfo=timezone.utc)).total_seconds()
            if antiguedad > _VENTANA_CORRECCION_SEGUNDOS:
                return None, Response({'detail': 'Solo puedes modificar registros de la última hora.'}, status=403)
        return mov, None

    @require_codigo
    def patch(self, request, centro_pk, mov_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        mov, err = self._get_mov_autorizado(request, centro_pk, mov_pk)
        if err:
            return err
        data = {k: v for k, v in request.data.items() if k not in ('centro_id', 'categoria_id', 'tipo')}
        serializer = MovimientoSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        get_db()[MOVIMIENTOS].update_one({'_id': mov['_id']}, {'$set': dict(serializer.validated_data)})
        updated = format_doc(get_db()[MOVIMIENTOS].find_one({'_id': mov['_id']}))
        return Response(MovimientoSerializer(updated).data)

    @require_codigo
    def delete(self, request, centro_pk, mov_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        mov, err = self._get_mov_autorizado(request, centro_pk, mov_pk)
        if err:
            return err
        get_db()[MOVIMIENTOS].delete_one({'_id': mov['_id']})
        return Response(status=204)


class TotalesView(APIView):
    """GET /api/centros/{id}/totales/ — totales derivados por categoría (ADR 0007)"""

    @require_codigo
    def get(self, request, centro_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        doc, err = _get_doc(CENTROS_ACOPIO, centro_pk)
        if err:
            return err
        movimientos = list(get_db()[MOVIMIENTOS].find({'centro_id': doc['_id']}))
        acumulado = {}
        for mov in movimientos:
            cid = str(mov['categoria_id'])
            if cid not in acumulado:
                acumulado[cid] = {'categoria_id': cid, 'entradas': 0, 'salidas': 0}
            if mov.get('cantidad') is not None:
                if mov['tipo'] == 'entrada':
                    acumulado[cid]['entradas'] += mov['cantidad']
                else:
                    acumulado[cid]['salidas'] += mov['cantidad']
        if acumulado:
            cat_oids = [ObjectId(cid) for cid in acumulado]
            cats = {str(c['_id']): c['nombre'] for c in get_db()[CATALOGO].find({'_id': {'$in': cat_oids}})}
            for cid, t in acumulado.items():
                t['categoria_nombre'] = cats.get(cid, '')
        return Response({
            'nota': 'Totales registrados — no representan existencias reales (ADR 0007)',
            'categorias': list(acumulado.values()),
        })


class CodigoListView(APIView):
    """GET/POST /api/centros/{id}/codigos/ — R6"""

    @require_responsable
    def get(self, request, centro_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        doc, err = _get_doc(CENTROS_ACOPIO, centro_pk)
        if err:
            return err
        codigos = get_db()[CODIGOS_GESTION].find({'centro_id': doc['_id'], 'rol': 'voluntario'})
        return Response([_format_codigo(c) for c in codigos])

    @require_responsable
    def post(self, request, centro_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        doc, err = _get_doc(CENTROS_ACOPIO, centro_pk)
        if err:
            return err
        etiqueta = (request.data.get('etiqueta') or '').strip()
        if not etiqueta:
            return Response({'detail': 'La etiqueta es requerida.'}, status=400)
        codigo = generar_codigo()
        result = get_db()[CODIGOS_GESTION].insert_one({
            'centro_id': doc['_id'],
            'valor_hash': hashear_codigo(codigo),
            'rol': 'voluntario',
            'etiqueta': etiqueta,
            'creado_por': ObjectId(request.auth_payload['codigo_id']),
            'revocado_en': None,
        })
        new_doc = get_db()[CODIGOS_GESTION].find_one({'_id': result.inserted_id})
        return Response({**_format_codigo(new_doc), 'codigo': codigo}, status=201)


class CodigoDetailView(APIView):
    """DELETE /api/centros/{id}/codigos/{cod_id}/ — R6"""

    @require_responsable
    def delete(self, request, centro_pk, cod_pk):
        err = check_centro(request, centro_pk)
        if err:
            return err
        cod, err = _get_doc(CODIGOS_GESTION, cod_pk)
        if err:
            return err
        if str(cod['centro_id']) != centro_pk:
            return Response({'detail': 'No encontrado.'}, status=404)
        if cod['rol'] != 'voluntario':
            return Response({'detail': 'No se puede revocar el código raíz desde aquí.'}, status=403)
        if cod['revocado_en'] is not None:
            return Response({'detail': 'El código ya está revocado.'}, status=400)
        get_db()[CODIGOS_GESTION].update_one({'_id': cod['_id']}, {'$set': {'revocado_en': _now()}})
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
