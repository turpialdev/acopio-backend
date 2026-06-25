from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        import sys
        if 'test' not in sys.argv:
            from api.models import ensure_indexes
            ensure_indexes()
