"""Cálculo del costo de delivery a partir de la distancia y la tarifa vigente."""

import math
from decimal import Decimal, ROUND_HALF_UP


def haversine_metros(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Distancia en línea recta, como fallback cuando Mapbox no responde."""
    radio_tierra_m = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return int(radio_tierra_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def calcular_costo_delivery(distancia_metros: int) -> Decimal:
    from store.models import TarifaDelivery

    tarifa = TarifaDelivery.vigente()
    km = Decimal(distancia_metros) / Decimal(1000)
    costo = tarifa.tarifa_base + tarifa.tarifa_por_km * km
    costo = max(costo, tarifa.costo_minimo)
    return costo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
