"""Ingest module: downloads data from CelesTrak and writes it to the catalog.

Public interface: ``IngestService`` for the worker, and ``get_data_status`` / ``DataStatus``
for the health endpoint.
"""

from sattrack.ingest.service import DataState, DataStatus, IngestService, get_data_status

__all__ = ["DataState", "DataStatus", "IngestService", "get_data_status"]
