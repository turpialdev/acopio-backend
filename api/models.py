from acopio.db import get_db

# Colecciones (ver claude_context/ARQUITECTURA.md §3)
CENTROS_ACOPIO = 'centros_acopio'
CATALOGO = 'catalogo'
NECESIDADES = 'necesidades'
MOVIMIENTOS = 'movimientos'
CODIGOS_GESTION = 'codigos_gestion'
MODERADORES = 'moderadores'
REPORTES = 'reportes'

# Valores controlados
ESTADOS_VERIFICACION = ('sin_verificar', 'verificado', 'oculto')
CARGOS_RESPONSABLE = ('propietario', 'socio', 'director', 'gerente')
URGENCIAS = ('urgente', 'media', 'leve')
TIPOS_MOVIMIENTO = ('entrada', 'salida')
ROLES_CODIGO = ('responsable', 'voluntario')


def ensure_indexes():
    db = get_db()

    # Centros — filtros del Directorio público
    db[CENTROS_ACOPIO].create_index('nombre')
    db[CENTROS_ACOPIO].create_index('estado')
    db[CENTROS_ACOPIO].create_index('municipio')
    db[CENTROS_ACOPIO].create_index('estado_verificacion')

    # Catálogo de categorías; el subconjunto es_insumo es lo que mueve el inventario
    db[CATALOGO].create_index('nombre', unique=True)
    db[CATALOGO].create_index('es_insumo')
    db[CATALOGO].create_index('activa')

    # Necesidades — una por (centro, categoría)
    db[NECESIDADES].create_index(
        [('centro_id', 1), ('categoria_id', 1)], unique=True
    )
    db[NECESIDADES].create_index('centro_id')
    db[NECESIDADES].create_index('categoria_id')
    db[NECESIDADES].create_index('urgencia')

    # Movimientos — libro por centro y fecha (ADR 0007: sin saldo almacenado)
    db[MOVIMIENTOS].create_index([('centro_id', 1), ('registrado_en', -1)])
    db[MOVIMIENTOS].create_index('categoria_id')
    db[MOVIMIENTOS].create_index('tipo')
    db[MOVIMIENTOS].create_index('codigo_id')

    # Códigos de gestión — se guarda el hash, nunca el texto plano (ADR 0002)
    db[CODIGOS_GESTION].create_index('valor_hash', unique=True)
    db[CODIGOS_GESTION].create_index('centro_id')

    # Moderadores — cuentas reales
    db[MODERADORES].create_index('email', unique=True)

    # Reportes ciudadanos
    db[REPORTES].create_index('centro_id')
    db[REPORTES].create_index('resuelto')
