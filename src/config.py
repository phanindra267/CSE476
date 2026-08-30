"""
Configuration — environment variable loading.

For this educational project, no external APIs are required.
All tools use deterministic local data.
"""

import os

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "local")
MODEL_NAME = os.getenv("MODEL_NAME", "deterministic")
API_KEY = os.getenv("API_KEY", "")
