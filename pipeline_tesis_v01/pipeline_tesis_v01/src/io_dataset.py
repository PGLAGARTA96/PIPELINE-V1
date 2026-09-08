from pathlib import Path
from typing import Dict, Iterator, List, Tuple


def iterar_historias(directorio: Path) -> Iterator[Tuple[str, int, str]]:
    """
    Recorre archivos .txt.
    Cada línea no vacía se considera una historia de usuario.
    Retorna: nombre_archivo, numero_linea, historia.
    """
    for archivo in sorted(directorio.glob("*.txt")):
        with archivo.open("r", encoding="utf-8-sig", errors="replace") as f:
            for numero_linea, linea in enumerate(f, start=1):
                historia = linea.strip()
                if historia:
                    yield archivo.name, numero_linea, historia


def procesar_directorio(directorio: Path, pipeline) -> Dict[str, object]:
    """Procesa cada historia de forma aislada y conserva su procedencia."""
    resultados: List[Dict[str, object]] = []
    errores: List[Dict[str, object]] = []

    for archivo, linea, historia in iterar_historias(directorio):
        try:
            resultado = pipeline.procesar_historia(historia)
            resultado["origen"] = {"archivo": archivo, "linea": linea}
            resultados.append(resultado)
        except Exception as error:
            errores.append({
                "archivo": archivo, "linea": linea, "historia": historia,
                "error": f"{type(error).__name__}: {error}",
            })

    componentes = [resultado["componentes"] for resultado in resultados]
    estadisticas = {
        "historias_procesadas": len(resultados),
        "rol_no_identificado": sum(c["rol"] is None for c in componentes),
        "verbo_intencion_no_identificado": sum(c["verbo_intencion"] is None for c in componentes),
        "accion_no_identificada": sum(c["accion"] is None for c in componentes),
        "objeto_no_identificado": sum(c["objeto"] is None for c in componentes),
        "beneficio_no_identificado": sum(c["beneficio"] is None for c in componentes),
        "historias_conformes": sum(r["conformidad"]["es_conforme"] for r in resultados),
        "historias_no_conformes": sum(not r["conformidad"]["es_conforme"] for r in resultados),
        "errores_procesamiento": len(errores),
    }
    return {"resultados": resultados, "errores": errores, "estadisticas": estadisticas}
