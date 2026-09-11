"""Small Neo4j repository base used by the authentication slice."""

from __future__ import annotations

from urllib.parse import unquote, urlsplit, urlunsplit

from django.conf import settings
from neo4j import GraphDatabase


class Neo4jRepository:
    """Create a driver without leaking credentials into application code."""

    def __init__(self) -> None:
        uri, auth = self._driver_arguments()
        driver_options = {
            "connection_timeout": settings.NEO4J_CONNECTION_TIMEOUT,
            "connection_acquisition_timeout": settings.NEO4J_CONNECTION_TIMEOUT,
        }
        if auth is None:
            self.driver = GraphDatabase.driver(uri, **driver_options)
        else:
            self.driver = GraphDatabase.driver(uri, auth=auth, **driver_options)

    @staticmethod
    def _driver_arguments() -> tuple[str, tuple[str, str] | None]:
        parsed = urlsplit(settings.NEO4J_URI)
        if parsed.username is None:
            auth = None
            uri = settings.NEO4J_URI
            if settings.NEO4J_USERNAME or settings.NEO4J_PASSWORD:
                auth = (settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            return uri, auth

        host = parsed.hostname or ""
        if parsed.port:
            host = f"{host}:{parsed.port}"
        uri = urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))
        return uri, (unquote(parsed.username), unquote(parsed.password or ""))

    def close(self) -> None:
        self.driver.close()

    def __enter__(self) -> "Neo4jRepository":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
