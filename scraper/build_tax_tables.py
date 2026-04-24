"""Orchestrator: corre los scrapers y actualiza data/tax_tables.json.

Estrategia:
- Para monotributo: scrapeo ARCA. Si falla, preservo el snapshot anterior.
- Para ganancias 4ta, aportes dependiente y autónomos: mantengo lo que ya
  estaba en el JSON (ARCA no tiene un HTML estructurado parseable para eso;
  se actualiza manualmente 2x/año).

El script fuerza exit 1 sólo si NO hay JSON anterior y no se puede generar uno
válido desde cero. Si hay snapshot anterior, lo conserva y loggea el error.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

# Importa el módulo hermano.
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import scrape_monotributo  # noqa: E402


ROOT = HERE.parent
DATA_FILE = ROOT / "data" / "tax_tables.json"


def load_existing() -> dict | None:
    if DATA_FILE.exists():
        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def main() -> int:
    existing = load_existing()
    if existing is None:
        print("ERROR: no existe data/tax_tables.json previo — generar manual primero.",
              file=sys.stderr)
        return 1

    updated = dict(existing)
    changed = False
    errors: list[str] = []

    # --- Monotributo ---
    try:
        mono = scrape_monotributo.scrape()
        if mono != existing.get("monotributo"):
            updated["monotributo"] = mono
            changed = True
            print(f"[monotributo] cambió. Vigente desde {mono['vigente_desde']}.")
        else:
            print("[monotributo] sin cambios.")
    except Exception as e:
        msg = f"[monotributo] scrape falló: {e}"
        print(msg, file=sys.stderr)
        errors.append(msg)

    # --- Ganancias, aportes, autónomos: preservar ---
    # Se actualizan manualmente. Cuando haya cambio de escala (semestral),
    # se edita el JSON a mano y el commit queda en la history.

    if changed:
        updated["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        updated["updated_by"] = os.environ.get(
            "GITHUB_WORKFLOW", "local") + "@" + os.environ.get("GITHUB_SHA", "local")[:7]
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"✓ {DATA_FILE} actualizado.")
    else:
        print("No hay cambios que commitear.")

    if errors:
        # Exit 2: hubo errores pero no vaciamos nada. El workflow puede abrir
        # issue en este caso.
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
