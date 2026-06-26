import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from api.auth import generar_codigo, hashear_codigo


class HealthEndpointTests(SimpleTestCase):
    def test_health_returns_ok(self):
        response = self.client.get(reverse('api:health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'status': 'ok', 'service': 'acopio-backend'},
        )


class CodigoFormatoTests(SimpleTestCase):
    """Valida el formato CE/VL + 8 dígitos (sin tocar MongoDB)."""

    _PATRON = re.compile(r'^(CE|VL)\d{8}$')

    def _generar_sin_db(self, prefijo):
        # Simula que ningún código existe aún en la BD.
        with patch('api.auth.get_db') as mock_db:
            mock_db.return_value.__getitem__.return_value.find_one.return_value = None
            return generar_codigo(prefijo)

    def test_formato_centro(self):
        codigo = self._generar_sin_db('CE')
        self.assertRegex(codigo, self._PATRON, f"Formato incorrecto: {codigo}")
        self.assertTrue(codigo.startswith('CE'))

    def test_formato_voluntario(self):
        codigo = self._generar_sin_db('VL')
        self.assertRegex(codigo, self._PATRON, f"Formato incorrecto: {codigo}")
        self.assertTrue(codigo.startswith('VL'))

    def test_longitud_total(self):
        codigo = self._generar_sin_db('CE')
        self.assertEqual(len(codigo), 10)  # 2 letras + 8 dígitos

    def test_digitos_con_cero_a_la_izquierda(self):
        # secrets.randbelow puede dar 0 → debe ser "00000000", no "0"
        import secrets
        with patch('api.auth.get_db') as mock_db, \
             patch('secrets.randbelow', return_value=0):
            mock_db.return_value.__getitem__.return_value.find_one.return_value = None
            codigo = generar_codigo('CE')
        self.assertEqual(codigo, 'CE00000000')

    def test_hashear_codigo_determinista(self):
        h1 = hashear_codigo('CE12345678')
        h2 = hashear_codigo('CE12345678')
        self.assertEqual(h1, h2)

    def test_hashes_distintos_para_codigos_distintos(self):
        self.assertNotEqual(hashear_codigo('CE12345678'), hashear_codigo('VL12345678'))

    def test_reintenta_si_colision(self):
        # Primera llamada a find_one devuelve un doc (colisión), segunda devuelve None.
        with patch('api.auth.get_db') as mock_db:
            find_one = mock_db.return_value.__getitem__.return_value.find_one
            find_one.side_effect = [{'existe': True}, None]
            codigo = generar_codigo('CE')
        self.assertEqual(find_one.call_count, 2)
        self.assertRegex(codigo, self._PATRON)
