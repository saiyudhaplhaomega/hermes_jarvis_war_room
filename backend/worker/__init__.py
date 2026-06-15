"""Celery worker for background task execution."""

from celery import Celery

app = Celery(
    'hermes_jarvis',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    include=['backend.worker.tasks']
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
