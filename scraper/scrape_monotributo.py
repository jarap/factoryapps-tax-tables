"""Scrape tabla vigente de categorías del monotributo desde ARCA.

Fuente: https://www.afip.gob.ar/monotributo/categorias.asp

La tabla en esa URL tiene 12 columnas con orden posicional estable:

    [ 0] Letra categoría (A..K)
    [ 1] Ingresos brutos anuales (tope)
    [ 2] Superficie afectada (texto)
    [ 3] Energía eléctrica (texto)
    [ 4] Alquileres devengados anuales
    [ 5] Precio unitario máximo venta muebles
    [ 6] Impuesto integrado — Locaciones y servicios
    [ 7] Impuesto integrado — Venta de cosas muebles
    [ 8] Aporte SIPA
    [ 9] Aporte obra social
    [10] Total mensual — Locaciones y servicios
    [11] Total mensual — Venta de cosas muebles

El parser valida la consistencia sumando [6]+[8]+[9] == [10] y [7]+[8]+[9] == [11]
(con tolerancia). Si la suma no matchea, algo cambió y falla ruidosamente.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from decimal import Decimal

import requests
from bs4 import BeautifulSoup

URL = "https://www.afip.gob.ar/monotributo/categorias.asp"
CATEGORIAS = list("ABCDEFGHIJK")
EXPECTED_COLS = 12
TOLERANCE = 1.0  # pesos


@dataclass
class CategoriaMono:
    letra: str
    tope_anual: float
    sipa: float
    obra_social: float
    impuesto_servicios: float
    impuesto_venta: float
    cuota_total_servicios: float
    cuota_total_venta: float


def _parse_amount(text: str) -> float:
    if text is None:
        raise ValueError("empty amount")
    s = text.strip().replace("$", "").replace("\xa0", "").strip()
    s = s.replace(".", "").replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    if not s:
        raise ValueError(f"cannot parse amount: {text!r}")
    return float(Decimal(s))


def fetch_html(url: str = URL) -> str:
    r = requests.get(
        url, timeout=30, headers={"User-Agent": "factoryapps-tax-tables/1.0"}
    )
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text


def parse_vigencia(html: str) -> str:
    """Busca 'aplicación desde el DD/MM/YYYY' o variantes."""
    soup = BeautifulSoup(html, "lxml")
    patterns = [
        r"aplicaci[oó]n\s+desde\s+el?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        r"vigente[s]?\s+desde\s+el?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    ]
    for txt in soup.stripped_strings:
        for p in patterns:
            m = re.search(p, txt, re.IGNORECASE)
            if m:
                dmy = m.group(1).replace("-", "/")
                d, mo, y = dmy.split("/")
                return f"{y}-{int(mo):02d}-{int(d):02d}"
    raise RuntimeError("no se encontró fecha de vigencia en la página de ARCA")


def parse_categorias(html: str) -> list[CategoriaMono]:
    soup = BeautifulSoup(html, "lxml")
    # Tabla principal del monotributo: table.table-striped dentro de contVigentes.
    container = soup.find(id="contVigentes") or soup
    tbl = container.find("table", class_="table-striped")
    if tbl is None:
        raise RuntimeError("no se encontró la tabla de categorías en ARCA")

    found: dict[str, list[str]] = {}
    for tr in tbl.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        first = cells[0].get_text(strip=True).upper()
        if first in CATEGORIAS and len(cells) == EXPECTED_COLS:
            found[first] = [c.get_text(" ", strip=True) for c in cells]

    missing = [c for c in CATEGORIAS if c not in found]
    if missing:
        raise RuntimeError(f"faltan categorías en la tabla de ARCA: {missing}")

    out: list[CategoriaMono] = []
    for letra in CATEGORIAS:
        row = found[letra]
        try:
            tope = _parse_amount(row[1])
            imp_s = _parse_amount(row[6])
            imp_v = _parse_amount(row[7])
            sipa = _parse_amount(row[8])
            os_ = _parse_amount(row[9])
            tot_s = _parse_amount(row[10])
            tot_v = _parse_amount(row[11])
        except Exception as e:
            raise RuntimeError(f"cat {letra}: parse error {e} en row {row}")

        # Validación de consistencia: total = impuesto + sipa + obra social
        if abs((imp_s + sipa + os_) - tot_s) > TOLERANCE:
            raise RuntimeError(
                f"cat {letra}: total servicios no cuadra: "
                f"{imp_s}+{sipa}+{os_}={imp_s+sipa+os_} vs {tot_s}"
            )
        if abs((imp_v + sipa + os_) - tot_v) > TOLERANCE:
            raise RuntimeError(
                f"cat {letra}: total venta no cuadra: "
                f"{imp_v}+{sipa}+{os_}={imp_v+sipa+os_} vs {tot_v}"
            )

        out.append(CategoriaMono(
            letra=letra,
            tope_anual=tope,
            sipa=sipa,
            obra_social=os_,
            impuesto_servicios=imp_s,
            impuesto_venta=imp_v,
            cuota_total_servicios=tot_s,
            cuota_total_venta=tot_v,
        ))
    return out


def scrape() -> dict:
    html = fetch_html()
    vigente_desde = parse_vigencia(html)
    categorias = parse_categorias(html)
    return {
        "vigente_desde": vigente_desde,
        "source": URL,
        "categorias": [asdict(c) for c in categorias],
    }


def main():
    try:
        data = scrape()
    except Exception as e:
        print(f"ERROR scraping monotributo: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
