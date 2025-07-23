from openai import OpenAI
import logging
import os

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv('OPENAI_KEY'))
