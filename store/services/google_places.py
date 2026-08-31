"""Search places through Google Places API (New).

The response is intentionally kept in memory. Google place data should not be
copied into the local catalog automatically; the catalog is reserved for
places curated by TuPlaza.
"""
from __future__ import annotations

import logging
from math import asin, cos, radians, sin, sqrt
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places"
GOOGLE_PLACES_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.primaryType,places.types,places.googleMapsUri"
)
NEARBY_PLACE_TYPES = [
    "hospital",
    "clinic",
    "pharmacy",
    "shopping_mall",
    "department_store",
    "supermarket",
    "grocery_store",
    "convenience_store",
    "restaurant",
    "cafe",
    "bakery",
    "gas_station",
    "bank",
]


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


def _categoria(place: dict[str, Any]) -> str:
    types = set(place.get("types") or [])
    primary_type = place.get("primaryType")
    if primary_type:
        types.add(primary_type)

    if "hospital" in types:
        return "hospital"
    if types.intersection({"clinic", "doctor", "medical_lab"}):
        return "clinica"
    if types.intersection({"shopping_mall", "department_store"}):
        return "centro_comercial"
    if types.intersection({"supermarket", "grocery_store", "convenience_store"}):
        return "mercado"
    if types.intersection({"store", "clothing_store", "hardware_store"}):
        return "local"
    return "otro"


def _request_google(endpoint: str, body: dict[str, Any], api_key: str) -> list[dict[str, Any]]:
    try:
        response = requests.post(
            endpoint,
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": GOOGLE_PLACES_FIELD_MASK,
            },
            timeout=8,
        )
        if not response.ok:
            logger.warning("Google Places respondió HTTP %s", response.status_code)
            return []
        payload = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("No se pudo consultar Google Places")
        return []

    places = payload.get("places") if isinstance(payload, dict) else None
    return places if isinstance(places, list) else []


def buscar_lugares_google(
    query: str | None,
    lat: float,
    lng: float,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Returns Google places near the reference point, sorted by distance."""
    api_key = str(getattr(settings, "GOOGLE_PLACES_API_KEY", "") or "").strip()
    if not api_key:
        logger.warning("GOOGLE_PLACES_API_KEY no está configurada")
        return []

    limit = max(1, min(limit or 8, 20))
    cleaned_query = (query or "").strip()
    center = {"latitude": lat, "longitude": lng}
    if cleaned_query:
        endpoint = f"{GOOGLE_PLACES_URL}:searchText"
        body = {
            "textQuery": cleaned_query,
            "pageSize": limit,
            "languageCode": "es",
            "regionCode": "VE",
            "locationBias": {
                "circle": {
                    "center": center,
                    "radius": 5000.0,
                }
            },
        }
    else:
        endpoint = f"{GOOGLE_PLACES_URL}:searchNearby"
        body = {
            "includedPrimaryTypes": NEARBY_PLACE_TYPES,
            "maxResultCount": limit,
            "languageCode": "es",
            "regionCode": "VE",
            "rankPreference": "DISTANCE",
            "locationRestriction": {
                "circle": {
                    "center": center,
                    "radius": 5000.0,
                }
            },
        }

    places = _request_google(endpoint, body, api_key)
    suggestions = []
    for place in places:
        location = place.get("location") or {}
        place_lat = location.get("latitude")
        place_lng = location.get("longitude")
        display_name = place.get("displayName") or {}
        if place_lat is None or place_lng is None or not display_name.get("text"):
            continue

        distance = _haversine_km(lat, lng, float(place_lat), float(place_lng))
        suggestions.append(
            {
                "id": str(place.get("id") or place.get("name") or display_name["text"]),
                "nombre": display_name["text"],
                "categoria": _categoria(place),
                "direccion": place.get("formattedAddress") or "",
                "lat": float(place_lat),
                "lng": float(place_lng),
                "distancia_km": round(distance, 3),
                "fuente": "google",
                "google_maps_uri": place.get("googleMapsUri"),
            }
        )

    return sorted(
        suggestions,
        key=lambda suggestion: (suggestion["distancia_km"], suggestion["nombre"].casefold()),
    )[:limit]
