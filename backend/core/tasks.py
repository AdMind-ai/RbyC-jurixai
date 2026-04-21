# core/tasks.py
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def test_task(word):
    print(f"Executando funcao {word}!")
    return True
