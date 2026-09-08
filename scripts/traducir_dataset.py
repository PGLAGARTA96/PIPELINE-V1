from pathlib import Path

import torch
from transformers import MarianMTModel, MarianTokenizer


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

BASE_DIR = Path(
    r"C:\Users\CIST\Downloads\Selene-PFC\dataset"
)

CARPETA_ENTRADA = BASE_DIR / "originales"
CARPETA_SALIDA = BASE_DIR / "traducciones"

MODELO_TRADUCCION = "Helsinki-NLP/opus-mt-en-es"


# ==========================================================
# CARGA DEL MODELO DE TRADUCCIÓN
# ==========================================================

def cargar_traductor():
    print("=" * 70)
    print("CARGA DEL MODELO DE TRADUCCIÓN")
    print("=" * 70)

    dispositivo = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print(f"Modelo: {MODELO_TRADUCCION}")
    print(
        "Dispositivo:",
        "GPU" if dispositivo.type == "cuda" else "CPU"
    )

    print("Cargando tokenizer...")

    tokenizer = MarianTokenizer.from_pretrained(
        MODELO_TRADUCCION
    )

    print("Cargando modelo...")

    modelo = MarianMTModel.from_pretrained(
        MODELO_TRADUCCION
    )

    modelo.to(dispositivo)
    modelo.eval()

    print("Modelo cargado correctamente.")

    return tokenizer, modelo, dispositivo


# ==========================================================
# LECTURA SEGURA DE ARCHIVOS
# ==========================================================

def leer_archivo(ruta_archivo):
    """
    Intenta leer el archivo utilizando distintas codificaciones.
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

            return lineas, codificacion

        except UnicodeDecodeError:
            continue

    raise UnicodeError(
        f"No se pudo determinar la codificación de: "
        f"{ruta_archivo}"
    )


# ==========================================================
# TRADUCCIÓN DE UNA HISTORIA
# ==========================================================

def traducir_texto(
    texto,
    tokenizer,
    modelo,
    dispositivo
):
    """
    Traduce una historia de usuario del inglés al español.
    """

    texto = texto.strip()

    if not texto:
        return ""

    try:

        entrada = tokenizer(
            texto,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )

        entrada = {
            clave: valor.to(dispositivo)
            for clave, valor in entrada.items()
        }

        with torch.no_grad():

            salida = modelo.generate(
                **entrada,
                max_length=512
            )

        traduccion = tokenizer.decode(
            salida[0],
            skip_special_tokens=True
        )

        return traduccion.strip()

    except Exception as error:

        print()
        print("ERROR DURANTE LA TRADUCCIÓN")
        print(f"Historia: {texto}")
        print(f"Detalle: {error}")

        # Si una historia falla, se conserva el texto original
        # para evitar perder registros del dataset.
        return texto


# ==========================================================
# CONTAR HISTORIAS
# ==========================================================

def obtener_historias(lineas):
    """
    Elimina líneas vacías y devuelve las historias válidas.
    """

    return [
        linea.strip()
        for linea in lineas
        if linea.strip()
    ]


# ==========================================================
# TRADUCCIÓN DE UN ARCHIVO
# ==========================================================

def traducir_archivo(
    archivo_entrada,
    archivo_salida,
    tokenizer,
    modelo,
    dispositivo
):
    """
    Traduce todas las historias de un archivo .txt.
    """

    lineas, codificacion = leer_archivo(
        archivo_entrada
    )

    historias = obtener_historias(lineas)

    total = len(historias)

    print()
    print("-" * 70)
    print(f"Archivo: {archivo_entrada.name}")
    print(f"Codificación detectada: {codificacion}")
    print(f"Historias encontradas: {total}")
    print("-" * 70)

    traducciones = []

    errores = 0

    for indice, historia in enumerate(
        historias,
        start=1
    ):

        try:

            traduccion = traducir_texto(
                historia,
                tokenizer,
                modelo,
                dispositivo
            )

            traducciones.append(
                traduccion
            )

        except Exception as error:

            errores += 1

            print(
                f"ERROR en historia {indice}: {error}"
            )

            traducciones.append(
                historia
            )

        print(
            f"[{indice}/{total}] "
            f"{historia[:70]}"
        )

    archivo_salida.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        archivo_salida,
        "w",
        encoding="utf-8"
    ) as archivo:

        for traduccion in traducciones:

            archivo.write(
                traduccion + "\n"
            )

    # ======================================================
    # VALIDACIÓN
    # ======================================================

    lineas_salida, _ = leer_archivo(
        archivo_salida
    )

    historias_salida = obtener_historias(
        lineas_salida
    )

    total_salida = len(
        historias_salida
    )

    valido = total == total_salida

    print()
    print(f"Archivo generado: {archivo_salida.name}")
    print(
        f"Entrada : {total} historias"
    )
    print(
        f"Salida  : {total_salida} historias"
    )

    if valido:

        print(
            "Validación: CORRECTA ✓"
        )

    else:

        print(
            "Validación: ERROR ✗"
        )

    return {
        "archivo": archivo_entrada.name,
        "entrada": total,
        "salida": total_salida,
        "valido": valido,
        "errores": errores
    }


# ==========================================================
# TRADUCCIÓN COMPLETA DEL DATASET
# ==========================================================

def traducir_dataset():

    print()
    print("=" * 70)
    print("TRADUCCIÓN DEL DATASET DE HISTORIAS DE USUARIO")
    print("=" * 70)

    # Crear carpeta de salida si no existe
    CARPETA_SALIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    # Buscar todos los TXT
    archivos = sorted(
        CARPETA_ENTRADA.glob("*.txt")
    )

    if not archivos:

        print()
        print(
            "No se encontraron archivos .txt en:"
        )

        print(
            CARPETA_ENTRADA
        )

        return

    print()
    print(
        f"Archivos encontrados: {len(archivos)}"
    )

    # Cargar modelo UNA SOLA VEZ
    tokenizer, modelo, dispositivo = (
        cargar_traductor()
    )

    resultados = []

    total_historias_entrada = 0
    total_historias_salida = 0
    total_errores = 0

    # ======================================================
    # PROCESAR TODOS LOS ARCHIVOS
    # ======================================================

    for numero, archivo_entrada in enumerate(
        archivos,
        start=1
    ):

        print()
        print("=" * 70)
        print(
            f"ARCHIVO {numero}/{len(archivos)}"
        )
        print("=" * 70)

        nombre_salida = (
            f"{archivo_entrada.stem}-traducido.txt"
        )

        archivo_salida = (
            CARPETA_SALIDA
            / nombre_salida
        )

        resultado = traducir_archivo(
            archivo_entrada,
            archivo_salida,
            tokenizer,
            modelo,
            dispositivo
        )

        resultados.append(
            resultado
        )

        total_historias_entrada += (
            resultado["entrada"]
        )

        total_historias_salida += (
            resultado["salida"]
        )

        total_errores += (
            resultado["errores"]
        )

    # ======================================================
    # RESUMEN FINAL
    # ======================================================

    print()
    print("=" * 70)
    print("RESUMEN FINAL DE LA TRADUCCIÓN")
    print("=" * 70)

    print()
    print(
        f"Archivos procesados: "
        f"{len(resultados)}"
    )

    print(
        f"Historias de entrada: "
        f"{total_historias_entrada}"
    )

    print(
        f"Historias de salida: "
        f"{total_historias_salida}"
    )

    print(
        f"Errores registrados: "
        f"{total_errores}"
    )

    archivos_correctos = sum(
        1
        for resultado in resultados
        if resultado["valido"]
    )

    archivos_incorrectos = (
        len(resultados)
        - archivos_correctos
    )

    print(
        f"Archivos validados correctamente: "
        f"{archivos_correctos}"
    )

    print(
        f"Archivos con diferencias: "
        f"{archivos_incorrectos}"
    )

    print()
    print(
        f"Traducciones guardadas en:"
    )

    print(
        CARPETA_SALIDA
    )

    # ======================================================
    # VALIDACIÓN GLOBAL
    # ======================================================

    print()
    print("=" * 70)
    print("VALIDACIÓN GLOBAL")
    print("=" * 70)

    if (
        total_historias_entrada
        == total_historias_salida
        and archivos_incorrectos == 0
    ):

        print(
            "RESULTADO: CORRECTO ✓"
        )

        print(
            "Todas las historias de entrada tienen "
            "una traducción correspondiente."
        )

    else:

        print(
            "RESULTADO: REVISAR ✗"
        )

        print(
            "Existen diferencias entre el dataset "
            "original y el dataset traducido."
        )

    # ======================================================
    # RESUMEN POR ARCHIVO
    # ======================================================

    print()
    print("=" * 70)
    print("DETALLE POR ARCHIVO")
    print("=" * 70)

    for resultado in resultados:

        estado = (
            "OK"
            if resultado["valido"]
            else "ERROR"
        )

        print(
            f"{resultado['archivo']:<35} "
            f"Entrada: {resultado['entrada']:<5} "
            f"Salida: {resultado['salida']:<5} "
            f"{estado}"
        )


# ==========================================================
# EJECUCIÓN PRINCIPAL
# ==========================================================

if __name__ == "__main__":

    traducir_dataset()