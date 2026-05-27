from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree

import requests
from django.conf import settings


ECB_DAILY_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_NAMESPACE = {"gesmes": "http://www.gesmes.org/xml/2002-08-01", "def": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}


class FxRateLookupError(RuntimeError):
    pass


@dataclass(frozen=True)
class FxQuote:
    base_currency: str
    quote_currency: str
    rate: Decimal
    fx_date: str
    source: str


class EuropeanCentralBankFxService:
    @classmethod
    def get_quote(cls, *, base_currency: str, quote_currency: str) -> FxQuote:
        base_currency = base_currency.upper()
        quote_currency = quote_currency.upper()

        if base_currency == quote_currency:
            return FxQuote(
                base_currency=base_currency,
                quote_currency=quote_currency,
                rate=Decimal("1"),
                fx_date=date.today().isoformat(),
                source="identity",
            )

        if base_currency == "USD" and quote_currency == "EUR":
            return cls._get_usd_to_eur_quote()

        raise FxRateLookupError(
            f"Unsupported currency conversion: {base_currency} to {quote_currency}."
        )

    @classmethod
    def _get_usd_to_eur_quote(cls) -> FxQuote:
        response = requests.get(
            ECB_DAILY_RATES_URL,
            timeout=int(getattr(settings, "INTERNAL_COSTS_FX_TIMEOUT_SECONDS", 10)),
        )
        response.raise_for_status()

        root = ElementTree.fromstring(response.content)
        time_cube = root.find(".//def:Cube/def:Cube", ECB_NAMESPACE)
        if time_cube is None:
            raise FxRateLookupError("ECB FX response did not include a rate date.")

        fx_date = time_cube.attrib.get("time")
        usd_cube = time_cube.find("def:Cube[@currency='USD']", ECB_NAMESPACE)
        if usd_cube is None:
            raise FxRateLookupError("ECB FX response did not include USD.")

        eur_to_usd = Decimal(str(usd_cube.attrib["rate"]))
        usd_to_eur = (Decimal("1") / eur_to_usd).quantize(Decimal("0.000001"), ROUND_HALF_UP)
        return FxQuote(
            base_currency="USD",
            quote_currency="EUR",
            rate=usd_to_eur,
            fx_date=fx_date or date.today().isoformat(),
            source="ecb",
        )
