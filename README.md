# factoryapps-tax-tables

Tablas tributarias de Argentina (monotributo, Impuesto a las Ganancias 4ta categoría, aportes dependiente, autónomos) en formato JSON, actualizadas automáticamente desde **ARCA (ex AFIP)**.

Consumidas por las apps del portfolio de [Factory Apps](https://github.com/jarap?tab=repositories) (Android).

## Endpoint público

```
https://jarap.github.io/factoryapps-tax-tables/data/tax_tables.json
```

Servido por GitHub Pages (CDN global, gratis). Sin auth, CORS abierto.

## Schema

Ver [`data/tax_tables.json`](data/tax_tables.json). Campos clave:

| Bloque | Qué contiene | Frecuencia de actualización |
|---|---|---|
| `monotributo` | Las 11 categorías A-K con tope anual, cuotas mensuales (servicios vs venta), aportes SIPA, obra social, impuesto integrado | Automático (scraper semanal) |
| `ganancias_4ta_categoria` | MNI, deducción especial (×4.8), cónyuge, hijos, 9 tramos escala Art. 94 LIG | Manual semestral (enero y julio) |
| `aportes_dependiente` | SIPA 11%, Obra Social 3%, PAMI 3%, tope base imponible | Manual (ley) |
| `autonomos` | Categorías I-V, cuotas mensuales fijas | Manual (resolución ANSES) |

## Cómo funciona

1. Un [GitHub Action](.github/workflows/update.yml) corre **cada lunes 9:00 UTC**.
2. [`scraper/scrape_monotributo.py`](scraper/scrape_monotributo.py) lee `https://www.afip.gob.ar/monotributo/categorias.asp` y parsea la tabla.
3. Si hay cambios vs el JSON vigente, se commitean.
4. GitHub Pages sirve el JSON actualizado en <1 minuto del commit.

Si el scraper falla (ej. ARCA cambió el HTML), el workflow abre un **issue automático** con etiqueta `scraper-broken`.

## Correr local

```bash
pip install -r scraper/requirements.txt
python scraper/scrape_monotributo.py   # scrapea y tira JSON a stdout
python scraper/build_tax_tables.py     # scrapea y actualiza data/tax_tables.json
```

## Actualizar Ganancias / Autónomos manualmente

Cuando ARCA publique la nueva escala de Ganancias (enero o julio) o ANSES actualice cuotas autónomos:

1. Editar directamente `data/tax_tables.json` en la web de GitHub o local.
2. Actualizar `vigente_desde` y los valores.
3. Bump `updated_at`.
4. Commit.

El scraper semanal no toca esos campos.

## Para apps consumidoras

- **Cachear 24h localmente.** El JSON cambia pocas veces al año.
- **Fallback al JSON embebido al compilar** por si el cliente está offline o GitHub Pages cae.
- Mostrar al usuario la fecha `updated_at` para que sepa cuán fresco es el cálculo.

## Disclaimer

Los valores publicados son un **cálculo orientativo**. Para casos particulares (ganancias cedulares, regímenes especiales, moratorias, etc.) consultar un contador.

Los datos se obtienen de fuentes públicas de ARCA. Este repo no representa ni endosa a ningún organismo del Estado Nacional Argentino.
