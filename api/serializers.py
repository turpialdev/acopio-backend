from bson import ObjectId
from rest_framework import serializers

from acopio.db import get_db
from api.models import (
    CARGOS_RESPONSABLE,
    CATALOGO,
    CENTROS_ACOPIO,
    ESTADOS_VERIFICACION,
    MOTIVOS_REPORTE,
    TIPOS_MOVIMIENTO,
    URGENCIAS,
)


def format_doc(doc: dict) -> dict:
    doc = dict(doc)
    doc['id'] = str(doc.pop('_id'))
    for key, val in list(doc.items()):
        if isinstance(val, ObjectId):
            doc[key] = str(val)
    return doc


def _validate_ref(collection: str, value: str, label: str):
    try:
        oid = ObjectId(value)
    except Exception:
        raise serializers.ValidationError('ID inválido.')
    doc = get_db()[collection].find_one({'_id': oid})
    if not doc:
        raise serializers.ValidationError(f'{label} no encontrado.')
    return oid, doc


def _optional_text(max_length):
    return serializers.CharField(
        max_length=max_length,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )


class CentroSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    nombre = serializers.CharField(max_length=200)
    estado = serializers.CharField(max_length=100)
    municipio = serializers.CharField(max_length=100)
    direccion = serializers.CharField(max_length=500)
    contacto = _optional_text(100)
    ubicacion_url = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    lat = serializers.FloatField(required=False, allow_null=True, default=None)
    lng = serializers.FloatField(required=False, allow_null=True, default=None)
    vialidad = _optional_text(300)
    horario = _optional_text(300)
    estado_verificacion = serializers.ChoiceField(
        choices=ESTADOS_VERIFICACION, default='sin_verificar'
    )
    # Datos internos del responsable (no se exponen en el Directorio)
    nombre_responsable = _optional_text(200)
    telefono_responsable = _optional_text(50)
    cargo_responsable = serializers.ChoiceField(
        choices=CARGOS_RESPONSABLE, required=False, allow_null=True, default=None
    )
    actualizado_en = serializers.DateTimeField(read_only=True)


class CategoriaSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    nombre = serializers.CharField(max_length=200)
    es_insumo = serializers.BooleanField(default=False)
    activa = serializers.BooleanField(default=True)


class NecesidadSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    centro_id = serializers.CharField()
    categoria_id = serializers.CharField()
    urgencia = serializers.ChoiceField(choices=URGENCIAS)
    detalle = _optional_text(500)

    def validate_centro_id(self, value):
        oid, _ = _validate_ref(CENTROS_ACOPIO, value, 'Centro')
        return oid

    def validate_categoria_id(self, value):
        oid, _ = _validate_ref(CATALOGO, value, 'Categoría')
        return oid


class CentroPublicoSerializer(serializers.Serializer):
    """Campos visibles en el Directorio público."""
    id = serializers.CharField(read_only=True)
    nombre = serializers.CharField(max_length=200)
    estado = serializers.CharField(max_length=100)
    municipio = serializers.CharField(max_length=100)
    direccion = serializers.CharField(max_length=500)
    contacto = _optional_text(100)
    ubicacion_url = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    lat = serializers.FloatField(required=False, allow_null=True, default=None)
    lng = serializers.FloatField(required=False, allow_null=True, default=None)
    vialidad = _optional_text(300)
    horario = _optional_text(300)
    estado_verificacion = serializers.ChoiceField(
        choices=ESTADOS_VERIFICACION, read_only=True
    )
    actualizado_en = serializers.DateTimeField(read_only=True)
    urgencia_maxima = serializers.CharField(allow_null=True, read_only=True, default=None)
    necesidades = serializers.ListField(
        child=serializers.DictField(), read_only=True, default=list
    )
    nombre_responsable = _optional_text(200)
    telefono_responsable = _optional_text(50)
    cargo_responsable = serializers.ChoiceField(
        choices=CARGOS_RESPONSABLE, required=False, allow_null=True, default=None
    )


class ReporteSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    centro_id = serializers.CharField(read_only=True)
    motivo = serializers.ChoiceField(
        choices=MOTIVOS_REPORTE, required=False, allow_null=True, default=None
    )
    detalle = _optional_text(1000)
    reportado_en = serializers.DateTimeField(read_only=True)
    estado = serializers.ChoiceField(choices=('pendiente', 'resuelto'), read_only=True)


class ContactoEmergenciaSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    nombre = serializers.CharField(max_length=200)
    tipo = serializers.CharField(max_length=100)
    zona = serializers.CharField(max_length=200)
    telefonos = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=1,
    )
    whatsapp_url = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, default=None
    )


class MovimientoSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    centro_id = serializers.CharField()
    categoria_id = serializers.CharField()
    tipo = serializers.ChoiceField(choices=TIPOS_MOVIMIENTO)
    cantidad = serializers.FloatField(
        required=False, allow_null=True, default=None, min_value=0
    )
    unidad = _optional_text(50)
    contraparte = _optional_text(200)
    nota = _optional_text(500)
    registrado_por = serializers.CharField(read_only=True)
    registrado_en = serializers.DateTimeField(read_only=True)

    def validate_centro_id(self, value):
        oid, _ = _validate_ref(CENTROS_ACOPIO, value, 'Centro')
        return oid

    def validate_categoria_id(self, value):
        oid, doc = _validate_ref(CATALOGO, value, 'Categoría')
        if not doc.get('es_insumo'):
            raise serializers.ValidationError(
                'El inventario solo mueve categorías marcadas como insumo.'
            )
        return oid
