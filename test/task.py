import os
import unittest

import django

from core.tasks import maven_spider


class MyTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lingzhi_engine.settings")
        os.environ.setdefault("debug", "true")
        django.setup()
        super().__init__(methodName)

    def test_something(self):
        self.assertEqual(True, False)

    def test_celery_beat(self):
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        schedule, created = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.HOURS, )

        import json
        heartbeat_task = PeriodicTask.objects.filter(name='engine.heartbeat').first()
        if heartbeat_task:
            heartbeat_task.task = 'core.tasks.heartbeat'
            heartbeat_task.interval = schedule
            heartbeat_task.save()
        else:
            PeriodicTask.objects.create(
                interval=schedule,
                name='engine.heartbeat',
                task='core.tasks.heartbeat',
                args=json.dumps([]),
            )

        schedule, created = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.MINUTES, )
        update_agent_task = PeriodicTask.objects.filter(name='engine.update_agent_status').first()
        if update_agent_task:
            update_agent_task.task = 'core.tasks.update_agent_status'
            update_agent_task.interval = schedule
            update_agent_task.save()
        else:
            PeriodicTask.objects.create(
                interval=schedule,
                name='engine.update_agent_status',
                task='core.tasks.update_agent_status',
                args=json.dumps([]),
            )

        schedule, created = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.DAYS, )
        update_sca_task = PeriodicTask.objects.filter(name='engine.update_sca').first()
        if update_sca_task:
            update_sca_task.task = 'core.tasks.update_sca'
            update_sca_task.interval = schedule
            update_sca_task.save()
        else:
            PeriodicTask.objects.create(
                interval=schedule,
                name='engine.update_sca',
                task='core.tasks.update_sca',
                args=json.dumps([]),
            )

    def test_agent_status_update(self):
        from core.tasks import update_agent_status
        update_agent_status()

    def test_maven_spider(self):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lingzhi_engine.settings")
        os.environ.setdefault("debug", "true")
        django.setup()
        print(os.environ)
        maven_spider()


if __name__ == '__main__':
    unittest.main()
