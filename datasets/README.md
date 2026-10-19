# Datos

## Fuente

**transfermarkt-datasets** (David Cariboo) — https://github.com/dcaribou/transfermarkt-datasets
También publicado en Kaggle: https://www.kaggle.com/datasets/davidcariboo/player-scores

- Licencia: **CC0 1.0** (dominio público). Se puede usar y redistribuir sin restricciones.
- Descarga: archivos CSV públicos (`https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/<tabla>.csv.gz`).
  No requiere clave de API ni scraping.
- Estado: según el repositorio, las actualizaciones están pausadas; los datos llegan al **6 de julio de 2026**.

### Tablas que usa Football IQ

| Tabla | Para qué |
|---|---|
| `competitions` | Ligas domésticas (31 de primera división) |
| `clubs` | Nombre, estadio |
| `players` | Perfil: nacimiento, nacionalidad, posición, altura, pie, foto |
| `games` | Resultados de liga 2012/13 – 2025/26 (63.382 partidos) |
| `appearances` | Minutos, goles, asistencias y tarjetas por partido (se agregan por temporada) |
| `player_valuations` | Historial de valor de mercado |

### Qué NO trae la fuente (y por eso no aparece en la app)

- Remates, pases, pases progresivos, regates, duelos, recuperaciones, xG.
- Apariciones de jugadores para 17 ligas agregadas en 2024 (Argentina, Brasil, MLS, México, Japón,
  Corea, Arabia Saudita, Austria, Suiza, Suecia, Noruega, Polonia, Rumania, Serbia, Chequia,
  Croacia, Australia). De esas ligas hay **solo resultados**: se usan en Teams y Match Predictor.

Se evaluó **StatsBomb Open Data** (eventos detallados, gratis con atribución), pero cubre pocas
competiciones completas, pesa varios GB en eventos y sus ids no coinciden con los de Transfermarkt.
Queda como mejora posible con un módulo de fuente propio (`backend/app/data/sources/`).

### Imágenes

Las fotos de jugadores (`players.image_url`) y los escudos/logos (CDN público de Transfermarkt) **no**
son parte de la licencia CC0: tienen derechos de sus dueños. La app solo los enlaza (no los descarga
ni los redistribuye). Para un uso público o comercial, desactivarlos con `VITE_SHOW_IMAGES=false`.

## Carpetas

- `raw/transfermarkt/` — dataset completo descargado por `scripts/import_data.py` (no se versiona).
- `sample/transfermarkt/` — **muestra real incluida en el repositorio** (2,7 MB): Premier League,
  LaLiga y Liga Profesional argentina, temporadas 2022/23 en adelante. Generada con
  `scripts/make_sample.py` a partir del dataset completo, sin modificar valores.
- `reports/data_quality.json` — informe de calidad de la última importación (filas descartadas,
  duplicados, faltantes, cobertura por liga).

## Datos sintéticos

Solo existen en `backend/tests/synthetic.py`, para los tests automatizados. Están marcados como
sintéticos y nunca se cargan en la aplicación.
