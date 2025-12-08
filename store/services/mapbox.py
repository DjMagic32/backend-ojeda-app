"""
Helpers to call Mapbox Directions API.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

import requests

DEFAULT_PROFILE = "driving-traffic"
BASE_URL = "https://api.mapbox.com/directions/v5/mapbox/{profile}/{coords}"


class MapboxConfigurationError(Exception):
    """Raised when no Mapbox token is configured."""


def _get_token() -> str:
    token = (
        os.getenv("MAPBOX_ACCESS_TOKEN")
        or os.getenv("MAPBOX_TOKEN")
    )
    if not token:
        raise MapboxConfigurationError(
            "Debes definir MAPBOX_TOKEN o MAPBOX_ACCESS_TOKEN en variables de entorno."
        )
    return token


def fetch_directions(
    start: Tuple[float, float],
    end: Tuple[float, float],
    profile: str = DEFAULT_PROFILE,
) -> Dict[str, Any]:
    """
    Obtiene ruta, distancia y duración entre dos puntos (lng, lat).
    Devuelve el objeto JSON de Mapbox.
    """
    access_token = _get_token()
    coords = f"{start[0]},{start[1]};{end[0]},{end[1]}"
    url = BASE_URL.format(profile=profile, coords=coords)

    params = {
        "alternatives": "false",
        "geometries": "geojson",
        "overview": "full",
        "steps": "false",
        "access_token": access_token,
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def extract_route_summary(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Aísla distancia, duración y geometría de la primera ruta si existe.
    """
    routes = data.get("routes") if isinstance(data, dict) else None
    if not routes:
        return None

    first = routes[0]
    return {
        "distance_m": int(first.get("distance") or 0),
        "duration_s": int(first.get("duration") or 0),
        "geometry": first.get("geometry"),
    }
