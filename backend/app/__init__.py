"""CINEFORGE backend package. Importing `backend.app` puts CINEFORGE packages on sys.path."""
from backend.app import config as config  # re-export

config  # noqa: B018 — path bootstrap happens in config import
