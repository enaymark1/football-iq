# Football IQ — Scouting & Analytics

Plataforma web de análisis de fútbol, scouting y modelos predictivos sobre **datos reales**
(transfermarkt-datasets, licencia CC0). Backend en FastAPI + SQLAlchemy + scikit-learn; frontend
en React + TypeScript + Vite + Tailwind + Recharts.

> El nombre se cambia en un solo lugar: `VITE_APP_NAME` (frontend/.env) y `FIQ_APP_NAME` (.env).

## Qué hace

| Sección | Qué ofrece |
|---|---|
| **Overview** | KPIs de la temporada, jugadores por posición y edad, top por valor y por rendimiento, comparación entre ligas, evolución de goles y ventaja de local, actividad de la sesión |
| **Players** | Explorador con 13 filtros combinables, orden por columna, búsqueda y paginación. Perfil con estadísticas por 90, percentiles contra su posición, fortalezas y debilidades, evolución por temporada, historial de valor, valor estimado por el modelo, similares y calidad de los datos |
| **Player Comparison** | 2 a 4 jugadores: radar de percentiles, barras por 90, tabla con diferencias (% o puntos) |
| **Scouting** | Perfil buscado (posición, edad, presupuesto, ligas, minutos, métricas y pesos) → candidatos ordenados con explicación generada a partir de los datos |
| **Similar Players** | 10 perfiles más parecidos (similitud coseno), variables ajustables |
| **Market Opportunities** | Índice de Oportunidad Estadística configurable + estimador de valor de mercado |
| **Match Predictor** | Probabilidades 1X2, goles esperados y resultados exactos (Poisson + Elo), comparado con logística y baseline |
| **Teams** | Equipos por liga con Elo; ficha con historial, local/visitante, forma, plantel y evolución del Elo |
| **Model Performance** | Métricas reales de evaluación, matriz de confusión, curvas de calibración e informe de calidad de datos |

## Datos

Fuente: **transfermarkt-datasets** — https://github.com/dcaribou/transfermarkt-datasets (CC0).
Detalle de tablas, cobertura y limitaciones en [datasets/README.md](datasets/README.md).

Importación completa verificada (19/10/2026):

| | Registros |
|---|---|
| Ligas domésticas | 31 |
| Equipos | 773 |
| Partidos de liga (2012/13 – 2025/26) | 63.382 |
| Jugadores | 16.902 (95% con foto) |
| Temporadas jugador (2019/20 – 2025/26) | 46.085 |
| Valoraciones de mercado | 312.086 |
| Apariciones procesadas | 827.215 |

- Estadísticas de jugadores: **14 ligas europeas**. Las otras 17 ligas solo traen resultados (se usan en
  Teams y Match Predictor).
- Métricas disponibles: minutos, goles, asistencias, tarjetas y contexto de equipo en los partidos jugados.
  **No hay** remates, pases ni acciones defensivas en la fuente; la app lo indica donde corresponde.
- Si la descarga falla, la importación usa la **muestra real incluida** (`datasets/sample`, 2,7 MB).

## Instalación en Windows (PowerShell)

### 1. Requisitos

- **Python 3.11 o superior** (probado con 3.13): https://www.python.org/downloads/ — marcar *Add python.exe to PATH*.
- **Node.js 20 o superior** (probado con 22 LTS): https://nodejs.org/ o desde PowerShell:

```powershell
winget install OpenJS.NodeJS.LTS
```

Cerrá y abrí PowerShell después de instalar, y verificá con `python --version` y `node --version`.

### 2. Backend: entorno virtual y dependencias

```powershell
cd football-iq\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell bloquea `Activate.ps1`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (o usá
`.\.venv\Scripts\python.exe` directamente en lugar de `python`).

### 3. Variables de entorno (opcional)

```powershell
cd ..
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

Sin `.env` todo funciona con los valores por defecto (SQLite local, sin claves de API).

### 4. Importar los datos (desde la raíz `football-iq`, con el entorno activado)

```powershell
python scripts\import_data.py            # descarga ~65 MB la primera vez y crea backend\football_iq.db
python scripts\import_data.py --sample   # alternativa sin internet: muestra incluida
```

Tarda ~20 segundos (más la descarga). Genera `datasets\reports\data_quality.json`.

### 5. Entrenar los modelos

```powershell
python scripts\train_models.py
```

Tarda ~1 minuto. Guarda los modelos en `backend\artifacts\` y sus métricas en la base.
Hay que volver a correrlo después de cada importación.

### 6. Iniciar el backend

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

API en http://127.0.0.1:8000 · documentación interactiva en http://127.0.0.1:8000/docs

### 7. Iniciar el frontend (otra ventana de PowerShell)

```powershell
cd football-iq\frontend
npm install
npm run dev
```

Abrir http://localhost:5173. En desarrollo, Vite redirige `/api` al backend.

### 8. Tests

```powershell
cd football-iq\backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

Y el chequeo de tipos + build del frontend: `cd frontend; npm run build`.

## Errores frecuentes

| Síntoma | Solución |
|---|---|
| La app muestra "No hay estadísticas de jugadores importadas" (HTTP 409) | Correr `python scripts\import_data.py` |
| Match Predictor dice "El modelo no está entrenado" (HTTP 503) | Correr `python scripts\train_models.py` |
| "No se pudo conectar con el backend" | Iniciar el backend (paso 6) en el puerto 8000 |
| `npm` no se reconoce | Instalar Node.js y reabrir PowerShell |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| La descarga falla (sin internet / firewall) | El script usa la muestra; o `python scripts\import_data.py --sample` |
| `database is locked` al importar | Frenar el backend (Ctrl+C) antes de reimportar |
| Errores raros de rutas largas en Windows | Usar una carpeta con ruta corta (p. ej. `C:\proyectos\football-iq`) |
| OneDrive tarda o bloquea archivos | `node_modules` y `.venv` tienen miles de archivos: conviene pausar la sincronización o usar una carpeta fuera de OneDrive |
| No se ven fotos ni escudos | Necesitan internet; si fallan se muestran iniciales. `VITE_SHOW_IMAGES=false` las apaga |

## Arquitectura

```
football-iq/
├─ README.md · .env.example · .gitignore
├─ scripts/                 import_data.py · train_models.py · make_sample.py
├─ datasets/                README.md · sample/ (muestra real versionada) · raw/ y reports/ (generados)
├─ backend/
│  ├─ requirements.txt
│  ├─ app/
│  │  ├─ main.py            FastAPI, CORS, manejo de errores
│  │  ├─ core/              configuración (.env), motor de base, errores de dominio
│  │  ├─ models/            tablas SQLAlchemy
│  │  ├─ schemas/           Pydantic: validación de entrada y salida
│  │  ├─ repositories/      consultas a la base (SQLAlchemy puro, portables a PostgreSQL)
│  │  ├─ services/          lógica: métricas, scouting, similitud, oportunidades, perfiles, equipos
│  │  ├─ ml/                features sin leakage, modelos, evaluación, registro de artefactos
│  │  ├─ data/              fuente reemplazable (sources/), limpieza (pipeline), escritura (loader)
│  │  └─ api/routes/        endpoints REST
│  └─ tests/                pytest con datos sintéticos marcados
└─ frontend/src/
   ├─ pages/ · layouts/ · components/ · hooks/ · services/api.ts · types/ · utils/
```

Separación: `repositories` (acceso a datos) → `services` / `ml` (lógica y modelos) → `api` (HTTP) →
`frontend` (presentación). El frontend solo conoce la API, no la fuente de datos.
Para cambiar de fuente: un módulo nuevo en `backend/app/data/sources/` que devuelva las mismas tablas.
Para PostgreSQL: `FIQ_DATABASE_URL=postgresql+psycopg://...` e instalar `psycopg[binary]`.

### Esquema de la base

| Tabla | Columnas principales |
|---|---|
| `leagues` | id, source, source_id, name, country, confederation, tier, image_url |
| `seasons` | year (2025 = 2025/26), label |
| `teams` | id, source, source_id, name, league_id→leagues, stadium, stadium_seats, image_url |
| `players` | id, source, source_id, name, date_of_birth, nationality, position, sub_position, foot, height_cm, current_team_id→teams, market_value_eur, market_value_date, highest_market_value_eur, image_url |
| `matches` | id, source, source_id, league_id, season, date, home_team_id, away_team_id, home_goals, away_goals |
| `player_season_stats` | player_id, season (único juntos), team_id, league_id, age, matches, minutes, goals, assists, tarjetas, contexto de equipo (team_matches, team_goals_for/against, team_points, clean_sheets, matches_60), derivadas por 90 y proporciones, valor al inicio/fin de temporada, rating, rating_reliability |
| `valuations` | player_id, date, value_eur |
| `model_runs` | model_key, name, objective, trained_at, n_train, n_test, features, metrics (JSON), validation, limitations |
| `import_reports` | created_at, source, report (JSON de calidad) |

Cada entidad importada guarda `source` + `source_id` (único por fuente); la clave interna es `id`,
así los identificadores de distintas fuentes no chocan.

### API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado de la base, datos y modelos |
| GET | `/api/meta` | Catálogo de métricas, definiciones, ligas, temporadas, informe de datos |
| GET | `/api/overview` | Dashboard de una temporada |
| GET | `/api/search?q=` | Búsqueda global de jugadores y equipos |
| GET | `/api/leagues` | Ligas con cobertura |
| GET | `/api/players` | Explorador (filtros, orden, paginación) |
| GET | `/api/players/filters` | Valores posibles de los filtros |
| GET | `/api/players/{id}` | Perfil completo |
| GET | `/api/players/{id}/similar` | Similares (variables y minutos ajustables) |
| POST | `/api/players/compare` | Comparación de 2 a 4 jugadores |
| POST | `/api/scouting/search` | Scouting configurable |
| POST | `/api/market/opportunities` | Índice de Oportunidad Estadística |
| POST | `/api/market/value-estimate` | Valor estimado (jugador o perfil hipotético) |
| POST | `/api/matches/predict` | Predicción de partido |
| GET | `/api/teams` · `/api/teams/{id}` | Equipos y ficha |
| GET | `/api/models/performance` | Última evaluación guardada de cada modelo |

Errores: 404 (no existe), 409 (faltan datos importados), 422 (validación), 503 (modelo sin entrenar),
siempre con `{"error", "message", "details"}` o el detalle de validación de FastAPI.

## Métricas y modelos

### FIQ Rating (métrica propia, 0–100)
Promedio ponderado de percentiles por posición dentro de su liga y temporada (referencia: 450+ minutos),
encogido hacia 50 según minutos: `confianza = minutos / (minutos + 600)`. Pesos por posición en
`backend/app/services/metrics.py`. Es relativo a la liga: no corrige diferencias de nivel entre ligas.

### Scouting
1. Filtros obligatorios (posición, ligas, minutos, edad, presupuesto contra el valor registrado).
2. Cada métrica → percentil contra la posición (450+ minutos, todas las ligas).
3. Dirección: en tarjetas, goles recibidos, edad y valor, menos es mejor (percentil invertido).
4. Pesos del usuario normalizados. 5. Puntaje = promedio ponderado de percentiles disponibles.
6. Orden. 7. Explicación con las métricas que más aportan, la más floja y los requisitos cumplidos.

### Jugadores similares
Similitud coseno sobre z-scores de variables según la posición, solo contra la misma posición y
excluyendo al jugador. Faltantes del candidato → mediana de la posición (se informa); faltantes del
jugador elegido → la variable no se usa. Es un índice algorítmico (−1 a 1), no una probabilidad.

### Índice de Oportunidad Estadística (métrica propia)
Combina rendimiento (FIQ Rating), valor bajo dentro de la posición, valor estimado por el modelo vs
registrado (solo fuera de muestra), edad y continuidad, con pesos configurables, y multiplica por
`0,75 + 0,25 × min(1, minutos/2000)`. Marca la incertidumbre (baja/media/alta) según minutos y
cobertura de datos. **No es una valoración oficial ni afirma que un jugador esté infravalorado.**

### Predictor de partidos
- Variables (todas previas al partido): diferencia de Elo, goles a favor/en contra de los últimos 10,
  puntos de los últimos 5, promedio de goles local/visitante de la liga.
- Modelo principal: dos regresiones de Poisson (goles local y visitante) → matriz de resultados.
- Comparación: logística multinomial y baseline de frecuencias históricas.
- Validación cronológica: entrenamiento 2012/13–2022/23, evaluación 2023/24–2025/26 (17.960 partidos).

| Modelo | Log loss ↓ | Brier ↓ | RPS ↓ | Accuracy |
|---|---|---|---|---|
| Poisson + Elo | 0,9965 | 0,5949 | 0,2025 | 51,2% |
| Logística multinomial | 0,9956 | 0,5945 | 0,2024 | 51,2% |
| Baseline (frecuencias) | 1,0749 | 0,6505 | 0,2294 | 43,4% |

### Estimador de valor de mercado
HistGradientBoosting sobre log(valor), con edad, posición, liga, minutos, producción y contexto.
**No usa historial de valores** (a propósito). Validación temporal: entrena 2019/20–2024/25, evalúa 2025/26
(5.729 jugadores).

| Método | MAE | RMSE | Error % mediano |
|---|---|---|---|
| Modelo | 3,10 M€ | 7,84 M€ | 39,1% |
| Baseline: mediana por liga, posición y edad | 5,06 M€ | 12,72 M€ | 61,1% |
| Referencia: repetir el valor anterior (usa historial) | 2,66 M€ | 6,30 M€ | 28,6% |

### Evaluación de similares
Auto-recuperación entre temporadas (perfil 2024/25 buscado entre los de 2025/26, 2.173 jugadores):
hit@10 = 5,6% vs 1,1% al azar. Señal real pero débil: con estas variables los perfiles cambian bastante
de una temporada a la siguiente.

## Limitaciones

- Sin datos de eventos (pases, remates, presión, xG): el análisis de rol y estilo es limitado, y en
  defensores y arqueros pesan métricas de contexto de equipo.
- Estadísticas de jugadores solo para 14 ligas europeas; el resto, solo resultados.
- El FIQ Rating es relativo a cada liga. El Elo también: comparar equipos de ligas distintas no es fiable.
- Los valores de Transfermarkt son estimaciones comunitarias, no precios de transferencia.
- La fuente está congelada al 6/7/2026.
- No incluye Docker: no se pudo verificar en este entorno, y la ejecución local es directa.

## Posibles mejoras

- Agregar StatsBomb Open Data o FBref (respetando términos) como fuente de eventos, con un cruce de ids.
- Ajuste de nivel entre ligas (coeficientes) para el rating y el scouting.
- Modelo Dixon-Coles (corrección de empates) y calibración isotónica.
- Autenticación y listas de seguimiento guardadas por usuario.
