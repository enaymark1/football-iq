"""Importa los datos reales a la base.

Uso (desde la raíz del proyecto):
    python scripts/import_data.py                 # usa datasets/raw si existe; si no, descarga
    python scripts/import_data.py --download      # fuerza la descarga del dataset completo
    python scripts/import_data.py --sample        # usa la muestra incluida en datasets/sample

Si la descarga falla, se informa el error y se usa la muestra (avisándolo).
"""
import argparse
import logging
import sys

import _bootstrap  # noqa: F401

from app.core.config import get_settings
from app.core.database import engine
from app.data import loader, pipeline
from app.data.sources import transfermarkt

log = logging.getLogger("import_data")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--download", action="store_true", help="volver a descargar los archivos")
    parser.add_argument("--sample", action="store_true", help="usar la muestra incluida en el repositorio")
    parser.add_argument("--first-season", type=int, default=None, help="primera temporada de jugadores")
    args = parser.parse_args()
    settings = get_settings()

    raw_dir = settings.raw_data_dir / transfermarkt.SOURCE_NAME
    sample_dir = settings.sample_data_dir / transfermarkt.SOURCE_NAME
    source_label = "transfermarkt (completo)"
    if args.sample:
        source_dir, source_label = sample_dir, "transfermarkt (muestra incluida)"
    else:
        source_dir = raw_dir
        if args.download or not transfermarkt.available(raw_dir):
            try:
                transfermarkt.download(raw_dir, force=args.download)
            except transfermarkt.SourceError as exc:
                log.error("%s", exc)
                if not transfermarkt.available(sample_dir):
                    log.error("Tampoco está la muestra en %s. No hay datos para importar.", sample_dir)
                    return 1
                log.warning("SE USA LA MUESTRA INCLUIDA (%s): menos ligas y temporadas.", sample_dir)
                source_dir, source_label = sample_dir, "transfermarkt (muestra incluida)"

    raw = transfermarkt.read(source_dir)
    result = pipeline.build(raw, source=transfermarkt.SOURCE_NAME,
                            first_player_season=args.first_season or settings.first_player_season)
    result.report["source_label"] = source_label
    result.report["source_license"] = transfermarkt.LICENSE
    result.report["source_url"] = transfermarkt.HOMEPAGE
    report = loader.write_tables(engine, result.tables, result.report, settings.reports_dir)

    log.info("Importación terminada (%s)", source_label)
    for table, info in report["tables"].items():
        log.info("  %-22s %s", table, info)
    log.info("  descartados: %s", report["dropped"])
    log.info("Informe de calidad: %s", settings.reports_dir / "data_quality.json")
    log.info("Siguiente paso: python scripts/train_models.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
