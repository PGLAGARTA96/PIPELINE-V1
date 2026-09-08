from pathlib import Path
import argparse
import json

from src.io_dataset import procesar_directorio
from src.pipeline import PipelineHistoriasUsuario


BASE = Path(__file__).resolve().parent
ENTRADA = BASE / "data" / "entrada"
SALIDA = BASE / "data" / "salida" / "resultados.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Procesa historias de usuario en archivos TXT.")
    parser.add_argument("--entrada", type=Path, default=ENTRADA)
    parser.add_argument("--salida", type=Path, default=SALIDA)
    argumentos = parser.parse_args()
    pipeline = PipelineHistoriasUsuario()
    lote = procesar_directorio(argumentos.entrada, pipeline)

    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    argumentos.salida.write_text(
        json.dumps(lote, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Historias procesadas: {lote['estadisticas']['historias_procesadas']}")
    print(f"Errores: {lote['estadisticas']['errores_procesamiento']}")
    print(f"Resultados: {argumentos.salida}")


if __name__ == "__main__":
    main()
