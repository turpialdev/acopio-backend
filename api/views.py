from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from acopio.db import get_db
from api.models import (
    CATALOGO,
    CENTROS_ACOPIO,
    CODIGOS_GESTION,
    MOVIMIENTOS,
    NECESIDADES,
)
from api.serializers import (
    CategoriaSerializer,
    CentroSerializer,
    MovimientoSerializer,
    NecesidadSerializer,
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


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'acopio-backend'})


# ---- centros de acopio ----

class CentroListView(APIView):
    def get(self, request):
        query = {}
        for field in ('estado', 'municipio', 'estado_verificacion'):
            value = request.query_params.get(field)
            if value:
                query[field] = value
        q = request.query_params.get('q')
        if q:
            query['nombre'] = {'$regex': q, '$options': 'i'}
        docs = [format_doc(d) for d in get_db()[CENTROS_ACOPIO].find(query)]
        return Response(CentroSerializer(docs, many=True).data)

    def post(self, request):
        serializer = CentroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = dict(serializer.validated_data)
        doc['actualizado_en'] = _now()
        result = get_db()[CENTROS_ACOPIO].insert_one(doc)
        created = format_doc(get_db()[CENTROS_ACOPIO].find_one({'_id': result.inserted_id}))
        return Response(CentroSerializer(created).data, status=201)


class CentroDetailView(APIView):
    def get(self, request, pk):
        doc, err = _get_doc(CENTROS_ACOPIO, pk)
        if err:
            return err
        return Response(CentroSerializer(format_doc(doc)).data)

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
    def get(self, request):
        query = {}
        centro_id = request.query_params.get('centro_id')
        if centro_id:
            oid = _parse_oid(centro_id)
            if oid is None:
                return Response({'detail': 'centro_id inválido.'}, status=400)
            query['centro_id'] = oid
        tipo = request.query_params.get('tipo')
        if tipo:
            query['tipo'] = tipo
        cursor = get_db()[MOVIMIENTOS].find(query).sort('registrado_en', -1)
        docs = [format_doc(d) for d in cursor]
        return Response(MovimientoSerializer(docs, many=True).data)

    def post(self, request):
        serializer = MovimientoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = dict(serializer.validated_data)
        doc['registrado_en'] = _now()
        result = get_db()[MOVIMIENTOS].insert_one(doc)
        created = format_doc(get_db()[MOVIMIENTOS].find_one({'_id': result.inserted_id}))
        return Response(MovimientoSerializer(created).data, status=201)


class MovimientoDetailView(APIView):
    def get(self, request, pk):
        doc, err = _get_doc(MOVIMIENTOS, pk)
        if err:
            return err
        return Response(MovimientoSerializer(format_doc(doc)).data)

    def patch(self, request, pk):
        doc, err = _get_doc(MOVIMIENTOS, pk)
        if err:
            return err
        # centro_id y categoria_id son inmutables tras el registro
        data = {
            k: v for k, v in request.data.items()
            if k not in ('centro_id', 'categoria_id')
        }
        serializer = MovimientoSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        get_db()[MOVIMIENTOS].update_one(
            {'_id': doc['_id']}, {'$set': dict(serializer.validated_data)}
        )
        updated = format_doc(get_db()[MOVIMIENTOS].find_one({'_id': doc['_id']}))
        return Response(MovimientoSerializer(updated).data)

    def delete(self, request, pk):
        doc, err = _get_doc(MOVIMIENTOS, pk)
        if err:
            return err
        get_db()[MOVIMIENTOS].delete_one({'_id': doc['_id']})
        return Response(status=204)
