from pathlib import Path
import json
import sys


# ==========================================================
# RUTAS DEL PROYECTO
# ==========================================================

BASE_PROYECTO = Path(
    r"C:\Users\CIST\Downloads\Selene-PFC"
)

CARPETA_TRADUCCIONES = (
    BASE_PROYECTO
    / "dataset"
    / "traducciones"
)

CARPETA_RESULTADOS = (
    BASE_PROYECTO
    / "dataset"
    / "resultados"
)

CARPETA_PIPELINE = (
    BASE_PROYECTO
    / "pipeline_tesis_v01"
    / "pipeline_tesis_v01"
    / "src"
)

# Permitir importar pipeline.py
sys.path.insert(
    0,
    str(CARPETA_PIPELINE)
)


# ==========================================================
# IMPORTAR EL PIPELINE
# ==========================================================

try:
    from pipeline import PipelineHistoriasUsuario

except ImportError as error:

    print("=" * 70)
    print("ERROR AL IMPORTAR EL PIPELINE")
    print("=" * 70)

    print()
    print(
        "No se pudo importar PipelineHistoriasUsuario "
        "desde pipeline.py"
    )

    print()
    print("Ruta buscada:")
    print(CARPETA_PIPELINE)

    print()
    print(f"Detalle: {error}")

    raise


# ==========================================================
# CARGAR EL PIPELINE UNA SOLA VEZ
# ==========================================================

print()
print("=" * 70)
print("CARGA DEL PIPELINE")
print("=" * 70)

print()
print("Cargando modelo spaCy y pipeline...")

try:
    pipeline_tesis = PipelineHistoriasUsuario()

except Exception as error:

    print()
    print("ERROR AL CARGAR EL PIPELINE")
    print(f"Detalle: {error}")

    print()
    print(
        "Verifique que esté instalado el modelo:"
    )

    print(
        "python -m spacy download es_core_news_sm"
    )

    raise

print("Pipeline cargado correctamente.")


# ==========================================================
# LEER HISTORIAS
# ==========================================================

def leer_historias(ruta_archivo):
    """
    Lee un archivo de historias traducidas.

    Se considera que cada línea no vacía contiene
    una historia de usuario independiente.
    """

    codificaciones = [
        "utf-8",
        "utf-8-sig",
        "latin-1"
    ]

    for codificacion in codificaciones:

        try:

            with open(
                ruta_archivo,
                "r",
                encoding=codificacion
            ) as archivo:

                lineas = archivo.readlines()

            historias = [
                linea.strip()
                for linea in lineas
                if linea.strip()
            ]

            return historias, codificacion

        except UnicodeDecodeError:
            continue

    raise UnicodeError(
        f"No se pudo leer el archivo: {ruta_archivo}"
    )


# ==========================================================
# PROCESAR UNA HISTORIA DE FORMA SEGURA
# ==========================================================

def procesar_historia_segura(
    historia,
    archivo_origen,
    numero_historia
):
    """
    Ejecuta las cuatro fases del pipeline sobre
    una historia de usuario.

    Si ocurre un error, el dataset continúa
    procesándose.
    """

    try:

        resultado_pipeline = (
            pipeline_tesis.procesar_historia(
                historia
            )
        )

        return {
            "archivo_origen": archivo_origen,
            "numero_historia": numero_historia,
            **resultado_pipeline
        }

    except Exception as error:

        return {
            "archivo_origen": archivo_origen,
            "numero_historia": numero_historia,
            "historia_original": historia,
            "error_procesamiento": str(error),
            "preprocesamiento": None,
            "analisis_linguistico": None,
            "componentes": None,
            "conformidad": None
        }


# ==========================================================
# ACTUALIZAR RESUMEN
# ==========================================================

def actualizar_resumen(
    resultado,
    resumen
):
    """
    Actualiza las estadísticas del archivo procesado.
    """

    if resultado.get(
        "error_procesamiento"
    ):

        resumen["errores"] += 1
        return

    componentes = (
        resultado.get("componentes")
        or {}
    )

    conformidad = (
        resultado.get("conformidad")
        or {}
    )

    # ======================================================
    # COMPONENTES NO IDENTIFICADOS
    # ======================================================

    if not componentes.get("rol"):
        resumen["sin_rol"] += 1

    if not componentes.get(
        "verbo_intencion"
    ):
        resumen[
            "sin_verbo_intencion"
        ] += 1

    if not componentes.get("accion"):
        resumen["sin_accion"] += 1

    if not componentes.get("objeto"):
        resumen["sin_objeto"] += 1

    if not componentes.get("beneficio"):
        resumen["sin_beneficio"] += 1

    # ======================================================
    # CONFORMIDAD
    # ======================================================

    if conformidad.get(
        "es_conforme"
    ) is True:

        resumen["conformes"] += 1

    else:

        resumen["no_conformes"] += 1

    # ======================================================
    # PLANTILLAS
    # ======================================================

    plantilla = conformidad.get(
        "plantilla"
    )

    if plantilla in resumen[
        "plantillas"
    ]:

        resumen[
            "plantillas"
        ][plantilla] += 1


# ==========================================================
# PROCESAR UN ARCHIVO
# ==========================================================

def procesar_archivo(
    archivo_entrada,
    archivo_salida
):
    """
    Procesa todas las historias de un archivo .txt
    traducido.
    """

    historias, codificacion = leer_historias(
        archivo_entrada
    )

    total = len(historias)

    print()
    print("-" * 70)
    print(
        f"Archivo: {archivo_entrada.name}"
    )
    print(
        f"Codificación: {codificacion}"
    )
    print(
        f"Historias encontradas: {total}"
    )
    print("-" * 70)

    resultados = []

    resumen = {
        "historias": total,
        "conformes": 0,
        "no_conformes": 0,
        "sin_rol": 0,
        "sin_verbo_intencion": 0,
        "sin_accion": 0,
        "sin_objeto": 0,
        "sin_beneficio": 0,
        "errores": 0,

        "plantillas": {
            "P1": 0,
            "P2": 0,
            "P3": 0,
            "P4": 0
        }
    }

    # ======================================================
    # PROCESAR CADA HISTORIA
    # ======================================================

    for numero, historia in enumerate(
        historias,
        start=1
    ):

        resultado = (
            procesar_historia_segura(
                historia=historia,
                archivo_origen=archivo_entrada.name,
                numero_historia=numero
            )
        )

        resultados.append(
            resultado
        )

        actualizar_resumen(
            resultado,
            resumen
        )

        # ==================================================
        # MOSTRAR PROGRESO
        # ==================================================

        if resultado.get(
            "error_procesamiento"
        ):

            print(
                f"[{numero}/{total}] "
                f"ERROR | "
                f"{historia[:60]}"
            )

            continue

        conformidad = (
            resultado.get(
                "conformidad"
            )
            or {}
        )

        if conformidad.get(
            "es_conforme"
        ):

            plantilla = (
                conformidad.get(
                    "plantilla"
                )
            )

            estado = (
                f"CONFORME ({plantilla})"
            )

        else:

            plantilla_cercana = (
                conformidad.get(
                    "plantilla_mas_cercana"
                )
            )

            if plantilla_cercana:

                estado = (
                    "NO CONFORME "
                    f"({plantilla_cercana})"
                )

            else:

                estado = "NO CONFORME"

        print(
            f"[{numero}/{total}] "
            f"{estado} | "
            f"{historia[:60]}"
        )

    # ======================================================
    # GUARDAR RESULTADOS DEL ARCHIVO
    # ======================================================

    archivo_salida.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    contenido_salida = {
        "archivo_origen":
            archivo_entrada.name,

        "total_historias":
            total,

        "resumen":
            resumen,

        "resultados":
            resultados
    }

    with open(
        archivo_salida,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            contenido_salida,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print()
    print(
        f"Resultado guardado:"
    )

    print(
        archivo_salida
    )

    print()
    print(
        f"Conformes:     "
        f"{resumen['conformes']}"
    )

    print(
        f"No conformes:  "
        f"{resumen['no_conformes']}"
    )

    print(
        f"Errores:       "
        f"{resumen['errores']}"
    )

    return resumen


# ==========================================================
# PROCESAR DATASET COMPLETO
# ==========================================================

def procesar_dataset():

    print()
    print("=" * 70)
    print(
        "PROCESAMIENTO DEL DATASET"
    )
    print("=" * 70)

    # Crear carpeta de resultados
    CARPETA_RESULTADOS.mkdir(
        parents=True,
        exist_ok=True
    )

    # Buscar archivos traducidos
    archivos = sorted(
        CARPETA_TRADUCCIONES.glob(
            "*.txt"
        )
    )

    if not archivos:

        print()
        print(
            "No se encontraron archivos "
            "traducidos en:"
        )

        print(
            CARPETA_TRADUCCIONES
        )

        return

    print()
    print(
        f"Archivos encontrados: "
        f"{len(archivos)}"
    )

    # ======================================================
    # RESUMEN GLOBAL
    # ======================================================

    resumen_global = {
        "archivos": len(archivos),
        "historias": 0,
        "conformes": 0,
        "no_conformes": 0,
        "sin_rol": 0,
        "sin_verbo_intencion": 0,
        "sin_accion": 0,
        "sin_objeto": 0,
        "sin_beneficio": 0,
        "errores": 0,

        "plantillas": {
            "P1": 0,
            "P2": 0,
            "P3": 0,
            "P4": 0
        }
    }

    detalle_archivos = []

    # ======================================================
    # RECORRER LOS ARCHIVOS
    # ======================================================

    for numero_archivo, archivo_entrada in enumerate(
        archivos,
        start=1
    ):

        print()
        print("=" * 70)
        print(
            f"ARCHIVO "
            f"{numero_archivo}/"
            f"{len(archivos)}"
        )
        print("=" * 70)

        nombre_base = (
            archivo_entrada.stem
            .replace(
                "-traducido",
                ""
            )
        )

        archivo_salida = (
            CARPETA_RESULTADOS
            / f"{nombre_base}-resultados.json"
        )

        resumen = procesar_archivo(
            archivo_entrada,
            archivo_salida
        )

        detalle_archivos.append(
            {
                "archivo":
                    archivo_entrada.name,

                **resumen
            }
        )

        # ==================================================
        # ACUMULAR RESULTADOS
        # ==================================================

        resumen_global[
            "historias"
        ] += resumen[
            "historias"
        ]

        resumen_global[
            "conformes"
        ] += resumen[
            "conformes"
        ]

        resumen_global[
            "no_conformes"
        ] += resumen[
            "no_conformes"
        ]

        resumen_global[
            "sin_rol"
        ] += resumen[
            "sin_rol"
        ]

        resumen_global[
            "sin_verbo_intencion"
        ] += resumen[
            "sin_verbo_intencion"
        ]

        resumen_global[
            "sin_accion"
        ] += resumen[
            "sin_accion"
        ]

        resumen_global[
            "sin_objeto"
        ] += resumen[
            "sin_objeto"
        ]

        resumen_global[
            "sin_beneficio"
        ] += resumen[
            "sin_beneficio"
        ]

        resumen_global[
            "errores"
        ] += resumen[
            "errores"
        ]

        # ==================================================
        # ACUMULAR PLANTILLAS
        # ==================================================

        for plantilla in [
            "P1",
            "P2",
            "P3",
            "P4"
        ]:

            resumen_global[
                "plantillas"
            ][plantilla] += (
                resumen[
                    "plantillas"
                ][plantilla]
            )

    # ======================================================
    # GUARDAR RESUMEN GLOBAL
    # ======================================================

    archivo_resumen = (
        CARPETA_RESULTADOS
        / "resumen_dataset.json"
    )

    with open(
        archivo_resumen,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            {
                "resumen_global":
                    resumen_global,

                "detalle_archivos":
                    detalle_archivos
            },
            archivo,
            ensure_ascii=False,
            indent=4
        )

    # ======================================================
    # MOSTRAR RESUMEN FINAL
    # ======================================================

    print()
    print("=" * 70)
    print(
        "RESUMEN GLOBAL DEL DATASET"
    )
    print("=" * 70)

    print()

    print(
        f"Archivos procesados:       "
        f"{resumen_global['archivos']}"
    )

    print(
        f"Historias procesadas:      "
        f"{resumen_global['historias']}"
    )

    print()

    print(
        f"Conformes:                 "
        f"{resumen_global['conformes']}"
    )

    print(
        f"No conformes:              "
        f"{resumen_global['no_conformes']}"
    )

    print()

    print(
        f"Plantilla P1:              "
        f"{resumen_global['plantillas']['P1']}"
    )

    print(
        f"Plantilla P2:              "
        f"{resumen_global['plantillas']['P2']}"
    )

    print(
        f"Plantilla P3:              "
        f"{resumen_global['plantillas']['P3']}"
    )

    print(
        f"Plantilla P4:              "
        f"{resumen_global['plantillas']['P4']}"
    )

    print()

    print(
        f"Sin rol:                   "
        f"{resumen_global['sin_rol']}"
    )

    print(
        f"Sin verbo de intención:    "
        f"{resumen_global['sin_verbo_intencion']}"
    )

    print(
        f"Sin acción:                "
        f"{resumen_global['sin_accion']}"
    )

    print(
        f"Sin objeto:                "
        f"{resumen_global['sin_objeto']}"
    )

    print(
        f"Sin beneficio:             "
        f"{resumen_global['sin_beneficio']}"
    )

    print()

    print(
        f"Errores de procesamiento:  "
        f"{resumen_global['errores']}"
    )

    print()
    print(
        "Resumen guardado en:"
    )

    print(
        archivo_resumen
    )


# ==========================================================
# EJECUCIÓN PRINCIPAL
# ==========================================================

if __name__ == "__main__":

    procesar_dataset()