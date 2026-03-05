import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('iaas')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Синхронизация статусов VM каждые 60 секунд
    'sync-vm-statuses': {
        'task': 'apps.virtual_machines.tasks.sync_vm_statuses',
        'schedule': 60.0,
    },
    # Обновление ресурсов гипервизоров каждые 5 минут
    'sync-hypervisor-resources': {
        'task': 'apps.hypervisors.tasks.sync_hypervisor_resources',
        'schedule': 300.0,
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
