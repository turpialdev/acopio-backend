from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        import sys
        # ensure_indexes() needs a live MongoDB connection. Skip it for commands
        # that run without a database — tests and build-time steps like
        # collectstatic — so `docker build` doesn't require Mongo to be reachable.
        no_db_commands = {'test', 'collectstatic', 'makemigrations', 'migrate', 'check'}
        if not no_db_commands.intersection(sys.argv):
            from api.models import ensure_indexes
            ensure_indexes()
