"""Search nearby places using Photon/OpenStreetMap without scraping Google."""
from __future__ import annotations

import hashlib
import logging
import unicodedata
from math import asin, cos, radians, sin, sqrt
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from store.models import Lugar

logger = logging.getLogger(__name__)

DEFAULT_PHOTON_URL = "https://photon.komoot.io"
PHOTON_USER_AGENT = "TuPlaza/1.0 (location search)"
NEARBY_TAGS = ("shop", "amenity", "healthcare")
MAX_SEARCH_DISTANCE_KM = 100.0
CACHE_SECONDS = 120


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_km = 6371.0088
    lat_delta = radians(lat2 - lat1)
    lng_delta = radians(lng2 - lng1)
    a = (
        sin(lat_delta / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(lng_delta / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(a))


def _photon_url() -> str:
    return str(
        getattr(settings, "PHOTON_API_URL", DEFAULT_PHOTON_URL) or DEFAULT_PHOTON_URL
    ).rstrip("/")


def _fetch(endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            endpoint,
            params=params,
            headers={
                "Accept-Language": "es",
                "User-Agent": PHOTON_USER_AGENT,
            },
            timeout=8,
        )
        if not response.ok:
            logger.warning("Photon respondió HTTP %s", response.status_code)
            return []
        payload = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("No se pudo consultar Photon/OpenStreetMap")
        return []

    features = payload.get("features") if isinstance(payload, dict) else None
    return features if isinstance(features, list) else []


def _address(properties: dict[str, Any]) -> str:
    street = " ".join(
        part
        for part in (properties.get("street"), properties.get("housenumber"))
        if part
    )
    locality = next(
        (
            properties.get(field)
            for field in ("district", "city", "county", "state")
            if properties.get(field)
        ),
        None,
    )
    if street and locality and street.casefold() != str(locality).casefold():
        return f"{street}, {locality}"
    return str(street or locality or properties.get("country") or "")


def _categoria(properties: dict[str, Any]) -> str:
    osm_key = properties.get("osm_key")
    osm_value = properties.get("osm_value")
    if osm_value == "hospital" or (
        osm_key == "healthcare" and osm_value == "hospital"
    ):
        return "hospital"
    if osm_key == "healthcare" and osm_value in {
        "clinic",
        "doctor",
        "doctors",
        "laboratory",
    }:
        return "clinica"
    if osm_value in {"mall", "department_store"}:
        return "centro_comercial"
    if osm_value in {"supermarket", "convenience", "grocery", "marketplace"}:
        return "mercado"
    if osm_key == "shop":
        return "local"
    if osm_key == "healthcare" and osm_value == "pharmacy":
        return "local"
    return "otro"


def _normalizar_texto(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.casefold().split())


def _lugares_catalogo(
    query: str,
    reference_lat: float,
    reference_lng: float,
) -> list[dict[str, Any]]:
    tokens = _normalizar_texto(query).split()
    if not tokens:
        return []

    suggestions = []
    for place in Lugar.objects.filter(activo=True):
        searchable = _normalizar_texto(
            " ".join((place.nombre, place.alias, place.direccion, place.categoria))
        )
        if not all(token in searchable for token in tokens):
            continue

        place_lat = float(place.lat)
        place_lng = float(place.lng)
        distance = _haversine_km(reference_lat, reference_lng, place_lat, place_lng)
        if distance > MAX_SEARCH_DISTANCE_KM:
            continue
        suggestions.append(
            {
                "id": f"catalog-{place.id}",
                "nombre": place.nombre,
                "categoria": place.categoria,
                "direccion": place.direccion,
                "lat": place_lat,
                "lng": place_lng,
                "distancia_km": round(distance, 3),
                "fuente": "tuplaza",
                "google_maps_uri": None,
            }
        )
    return suggestions


def _to_suggestion(
    feature: dict[str, Any],
    reference_lat: float,
    reference_lng: float,
) -> dict[str, Any] | None:
    properties = feature.get("properties") or {}
    coordinates = (feature.get("geometry") or {}).get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None

    name = properties.get("name") or properties.get("street")
    if not name:
        return None

    place_lng = float(coordinates[0])
    place_lat = float(coordinates[1])
    distance = _haversine_km(reference_lat, reference_lng, place_lat, place_lng)
    osm_id = properties.get("osm_id")
    osm_type = properties.get("osm_type")
    suggestion_id = (
        f"osm-{osm_type}-{osm_id}"
        if osm_type and osm_id
        else f"osm-{place_lat:.6f}-{place_lng:.6f}"
    )
    return {
        "id": suggestion_id,
        "nombre": str(name),
        "categoria": _categoria(properties),
        "direccion": _address(properties),
        "lat": place_lat,
        "lng": place_lng,
        "distancia_km": round(distance, 3),
        "fuente": "openstreetmap",
        "google_maps_uri": None,
    }


def _cache_key(query: str | None, lat: float, lng: float, limit: int) -> str:
    raw = f"{(query or '').strip().casefold()}|{lat:.3f}|{lng:.3f}|{limit}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    # La versión evita reutilizar respuestas vacías generadas por una
    # configuración anterior del proveedor.
    return f"tuplaza:osm-places-v2:{digest}"


def buscar_lugares_openstreetmap(
    query: str | None,
    lat: float,
    lng: float,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Returns Photon places near the reference point, sorted by distance."""
    limit = max(1, min(limit or 8, 20))
    cleaned_query = (query or "").strip()
    cache_key = _cache_key(cleaned_query, lat, lng, limit)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    base_url = _photon_url()
    if cleaned_query:
        features = _fetch(
            f"{base_url}/api",
            {
                "q": cleaned_query,
                "lat": lat,
                "lon": lng,
                "zoom": 14,
                "location_bias_scale": 0.1,
                "countrycode": "VE",
                "limit": limit * 2,
            },
        )
        catalog_suggestions = _lugares_catalogo(cleaned_query, lat, lng)
    else:
        features = []
        catalog_suggestions = []
        for tag in NEARBY_TAGS:
            features.extend(
                _fetch(
                    f"{base_url}/reverse",
                    {
                        "lat": lat,
                        "lon": lng,
                        "radius": 5,
                        "limit": limit,
                        "osm_tag": tag,
                    },
                )
            )

    suggestions = catalog_suggestions
    seen = set()
    for feature in features:
        suggestion = _to_suggestion(feature, lat, lng)
        if not suggestion or suggestion["distancia_km"] > MAX_SEARCH_DISTANCE_KM:
            continue
        if suggestion["id"] in seen:
            continue
        seen.add(suggestion["id"])
        suggestions.append(suggestion)

    result = sorted(
        suggestions,
        key=lambda suggestion: (suggestion["distancia_km"], suggestion["nombre"].casefold()),
    )[:limit]
    cache.set(cache_key, result, CACHE_SECONDS)
    return result
