import hashlib
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand

from acopio.db import get_db
from api.models import (
    CATALOGO,
    CENTROS_ACOPIO,
    CODIGOS_GESTION,
    MODERADORES,
    MOVIMIENTOS,
    NECESIDADES,
)

SEEDED_COLLECTIONS = (
    CATALOGO,
    CENTROS_ACOPIO,
    NECESIDADES,
    MOVIMIENTOS,
    CODIGOS_GESTION,
    MODERADORES,
)


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode()).hexdigest()


def _ago(**kwargs) -> datetime:
    return datetime.now(timezone.utc) - timedelta(**kwargs)


class Command(BaseCommand):
    help = (
        'Llena la base de datos con datos de prueba (centros, catálogo, '
        'necesidades, movimientos, códigos y moderadores). Borra esas '
        'colecciones antes de insertar; usar solo en bases de prueba.'
    )

    def handle(self, *args, **options):
        db = get_db()

        for name in SEEDED_COLLECTIONS:
            db[name].delete_many({})

        # --- Catálogo de categorías ---
        catalogo_docs = [
            {'nombre': 'Agua potable', 'es_insumo': True, 'activa': True},
            {'nombre': 'Alimentos no perecederos', 'es_insumo': True, 'activa': True},
            {'nombre': 'Medicamentos básicos', 'es_insumo': True, 'activa': True},
            {'nombre': 'Insumos médicos', 'es_insumo': True, 'activa': True},
            {'nombre': 'Ropa y cobijas', 'es_insumo': True, 'activa': True},
            {'nombre': 'Productos de higiene', 'es_insumo': True, 'activa': True},
            {'nombre': 'Voluntarios de rescate', 'es_insumo': False, 'activa': True},
            {'nombre': 'Transporte', 'es_insumo': False, 'activa': True},
        ]
        db[CATALOGO].insert_many(catalogo_docs)
        cat = {d['nombre']: d['_id'] for d in catalogo_docs}

        # --- Centros de acopio ---
        # Centros reales tomados del documento "CENTRO DE ACOPIO - PadelApoya".
        centros_docs = [
            {
                'nombre': 'Colegio Cristo Rey Altamira',
                'estado': 'Miranda',
                'municipio': 'Chacao',
                'direccion': ('Colegio Cristo Rey Altamira. 7ma Avenida, '
                              'entre 6ta y 7ma Transversal, Caracas'),
                'contacto': None,
                'ubicacion_url': 'https://maps.app.goo.gl/WwtukMpkrjwn1tP2A',
                'lat': None,
                'lng': None,
                'vialidad': 'Recepción desde las 10:30 am',
                'estado_verificacion': 'verificado',
                'nombre_responsable': None,
                'telefono_responsable': None,
                'cargo_responsable': None,
                'actualizado_en': _ago(hours=3),
            },
            {
                'nombre': 'Capital Sports Santa Fe',
                'estado': 'Miranda',
                'municipio': 'Baruta',
                'direccion': ('Avenida Rafael Rangel, local Capital Sports Padel '
                              'Center, Santa Fe, Caracas'),
                'contacto': '0414-3206559',
                'ubicacion_url': None,
                'lat': None,
                'lng': None,
                'vialidad': None,
                'estado_verificacion': 'verificado',
                'nombre_responsable': 'Jorge Peraza',
                'telefono_responsable': '0414-3206559',
                'cargo_responsable': 'socio',
                'actualizado_en': _ago(hours=8),
            },
            {
                'nombre': 'Cántaros Sports',
                'estado': 'Miranda',
                'municipio': 'El Hatillo',
                'direccion': ('Av. El Portal, La Lagunita Country Club, frente a '
                              'iglesia de Santa Ana, Polideportivo La Lagunita'),
                'contacto': '+58 414-3665585',
                'ubicacion_url': None,
                'lat': None,
                'lng': None,
                'vialidad': ('Coordinar con la Alcaldía del Hatillo la recolección '
                             'de las donaciones'),
                'estado_verificacion': 'verificado',
                'nombre_responsable': 'Felix Polonio',
                'telefono_responsable': '+58 414-3665585',
                'cargo_responsable': 'socio',
                'actualizado_en': _ago(days=1),
            },
            {
                'nombre': 'Seven Club',
                'estado': 'Miranda',
                'municipio': 'El Hatillo',
                'direccion': 'Av. principal El Hatillo, km 1, Municipio El Hatillo',
                'contacto': '0412-1793687',
                'ubicacion_url': None,
                'lat': None,
                'lng': None,
                'vialidad': None,
                'estado_verificacion': 'verificado',
                'nombre_responsable': 'Carlos Salas',
                'telefono_responsable': '0412-1793687',
                'cargo_responsable': 'gerente',
                'actualizado_en': _ago(hours=12),
            },
        ]
        db[CENTROS_ACOPIO].insert_many(centros_docs)
        centro = {d['nombre']: d['_id'] for d in centros_docs}

        # --- Necesidades (líneas de ficha) ---
        # Necesidades ilustrativas (el documento no especifica inventario).
        necesidades_docs = [
            {'centro': 'Colegio Cristo Rey Altamira', 'categoria': 'Agua potable',
             'urgencia': 'urgente', 'detalle': 'Botellones de 5L preferiblemente'},
            {'centro': 'Colegio Cristo Rey Altamira', 'categoria': 'Medicamentos básicos',
             'urgencia': 'urgente', 'detalle': 'Analgésicos y antibióticos'},
            {'centro': 'Colegio Cristo Rey Altamira', 'categoria': 'Alimentos no perecederos',
             'urgencia': 'media', 'detalle': None},
            {'centro': 'Capital Sports Santa Fe', 'categoria': 'Ropa y cobijas',
             'urgencia': 'media', 'detalle': 'Cobijas para adultos y niños'},
            {'centro': 'Capital Sports Santa Fe', 'categoria': 'Productos de higiene',
             'urgencia': 'leve', 'detalle': None},
            {'centro': 'Cántaros Sports', 'categoria': 'Agua potable',
             'urgencia': 'urgente', 'detalle': 'Sin servicio de agua en la zona'},
            {'centro': 'Cántaros Sports', 'categoria': 'Voluntarios de rescate',
             'urgencia': 'urgente', 'detalle': 'Personas con experiencia en remoción'},
            {'centro': 'Cántaros Sports', 'categoria': 'Insumos médicos',
             'urgencia': 'media', 'detalle': 'Gasas, guantes, vendas'},
            {'centro': 'Seven Club', 'categoria': 'Alimentos no perecederos',
             'urgencia': 'media', 'detalle': None},
            {'centro': 'Seven Club', 'categoria': 'Transporte',
             'urgencia': 'leve', 'detalle': 'Camiones para trasladar donaciones'},
        ]
        db[NECESIDADES].insert_many([
            {
                'centro_id': centro[d['centro']],
                'categoria_id': cat[d['categoria']],
                'urgencia': d['urgencia'],
                'detalle': d['detalle'],
            }
            for d in necesidades_docs
        ])

        # --- Movimientos (libro de entradas/salidas; solo es_insumo) ---
        # Movimientos ilustrativos sobre categorías que son insumo.
        movimientos_docs = [
            {'centro': 'Colegio Cristo Rey Altamira', 'categoria': 'Agua potable', 'tipo': 'entrada',
             'cantidad': 200, 'unidad': 'botellas', 'contraparte': 'Donante anónimo',
             'nota': 'Entrega en la mañana', 'registrado_en': _ago(hours=6)},
            {'centro': 'Colegio Cristo Rey Altamira', 'categoria': 'Agua potable', 'tipo': 'salida',
             'cantidad': 150, 'unidad': 'botellas', 'contraparte': 'Protección Civil',
             'nota': None, 'registrado_en': _ago(hours=2)},
            {'centro': 'Colegio Cristo Rey Altamira', 'categoria': 'Medicamentos básicos', 'tipo': 'entrada',
             'cantidad': 50, 'unidad': 'cajas', 'contraparte': 'Farmacia La Cruz',
             'nota': 'Vencimiento 2027', 'registrado_en': _ago(hours=5)},
            {'centro': 'Cántaros Sports', 'categoria': 'Agua potable', 'tipo': 'entrada',
             'cantidad': None, 'unidad': None, 'contraparte': 'Vecinos del sector',
             'nota': 'Cantidad sin contar', 'registrado_en': _ago(hours=10)},
            {'centro': 'Cántaros Sports', 'categoria': 'Insumos médicos', 'tipo': 'salida',
             'cantidad': 30, 'unidad': 'kits', 'contraparte': 'Bomberos',
             'nota': None, 'registrado_en': _ago(hours=4)},
            {'centro': 'Seven Club', 'categoria': 'Alimentos no perecederos',
             'tipo': 'entrada', 'cantidad': 80, 'unidad': 'bolsas',
             'contraparte': 'Comercio local', 'nota': None, 'registrado_en': _ago(days=1)},
        ]
        db[MOVIMIENTOS].insert_many([
            {
                'centro_id': centro[d['centro']],
                'categoria_id': cat[d['categoria']],
                'tipo': d['tipo'],
                'cantidad': d['cantidad'],
                'unidad': d['unidad'],
                'contraparte': d['contraparte'],
                'nota': d['nota'],
                'registrado_por': 'Responsable',
                'registrado_en': d['registrado_en'],
            }
            for d in movimientos_docs
        ])

        # --- Códigos de gestión (se guarda el hash; ver ADR 0002) ---
        codigos_plain = [
            {'centro': 'Capital Sports Santa Fe', 'valor': 'SANTAFE-RAIZ-2026',
             'rol': 'responsable', 'etiqueta': 'Jorge – raíz', 'creado_por': None},
            {'centro': 'Capital Sports Santa Fe', 'valor': 'SANTAFE-VOL-PUERTA',
             'rol': 'voluntario', 'etiqueta': 'Voluntario – puerta',
             'creado_por': 'SANTAFE-RAIZ-2026'},
            {'centro': 'Cántaros Sports', 'valor': 'CANTAROS-RAIZ-2026',
             'rol': 'responsable', 'etiqueta': 'Felix – raíz', 'creado_por': None},
        ]
        db[CODIGOS_GESTION].insert_many([
            {
                'centro_id': centro[d['centro']],
                'valor_hash': _hash(d['valor']),
                'rol': d['rol'],
                'etiqueta': d['etiqueta'],
                'creado_por': _hash(d['creado_por']) if d['creado_por'] else None,
                'revocado_en': None,
            }
            for d in codigos_plain
        ])

        # --- Moderadores ---
        db[MODERADORES].insert_one({
            'nombre': 'Moderador Demo',
            'email': 'moderador@acopio.ve',
        })

        # --- Resumen ---
        self.stdout.write(self.style.SUCCESS('Datos de prueba insertados:'))
        for name in SEEDED_COLLECTIONS:
            self.stdout.write(f'  {name}: {db[name].count_documents({})}')

        self.stdout.write('')
        self.stdout.write('Códigos de gestión (texto plano, solo para pruebas):')
        for d in codigos_plain:
            self.stdout.write(f"  [{d['rol']}] {d['centro']}: {d['valor']}")
