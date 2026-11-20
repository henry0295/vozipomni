"""
Limpia en django_celery_beat las tareas periódicas que apuntan a nombres de
tarea no registrados (restos de la antigua programación de config/celery.py,
que usaba nombres como 'apps.campaigns.tasks.process_pending_calls').

La programación válida vive en settings.CELERY_BEAT_SCHEDULE. Este comando:
- desactiva o borra las PeriodicTask cuyo `task` no está registrado,
- nunca toca `celery.backend_cleanup` ni tareas `celery.*`,
- con --dry-run solo informa.
Siempre sale con 0 (deploy.sh lo ejecuta sin bloquear).
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Elimina tareas periódicas con nombres de tarea no registrados'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo mostrar, no modificar')

    def handle(self, *args, **options):
        dry = options['dry_run']
        try:
            from config.celery import app
            from django_celery_beat.models import PeriodicTask
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"[Beat] No disponible: {e}"))
            return

        try:
            app.loader.import_default_modules()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"[Beat] No se pudieron importar las tareas: {e}"))
            return
        registered = set(app.tasks.keys())

        removed = 0
        for pt in PeriodicTask.objects.all():
            if pt.task.startswith('celery.') or pt.task in registered:
                continue
            self.stdout.write(f"[Beat] Tarea periódica '{pt.name}' -> '{pt.task}' no registrada"
                              + (" (dry-run)" if dry else ": eliminada"))
            if not dry:
                pt.delete()
            removed += 1

        self.stdout.write(self.style.SUCCESS(
            f"[Beat] {removed} tareas obsoletas {'detectadas' if dry else 'eliminadas'}; "
            f"{len(registered)} tareas registradas"
        ))
