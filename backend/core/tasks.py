# core/tasks.py
import logging
import os
from celery import shared_task


@shared_task
def test_task(word):
    print(f"Executando função {word}!")
    return True
