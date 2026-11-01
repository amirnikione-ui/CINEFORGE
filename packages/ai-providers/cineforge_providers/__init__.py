"""cineforge_providers — capability interfaces + registry + fallback chains (ADR-0004/0005)."""
from .base import CallResult, Provider, ProviderError, call_chain
from .registry import Registry, get_registry

__all__ = ["Provider", "ProviderError", "CallResult", "call_chain", "Registry", "get_registry"]
