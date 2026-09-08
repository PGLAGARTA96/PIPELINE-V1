# Pipeline de tesis v0.3

Primera implementación del pipeline para historias de usuario en español.

## Fases implementadas
1. Preprocesamiento: segmentación en oraciones y tokenización.
2. Análisis lingüístico: POS, lema y dependencias sintácticas.
3. Extracción de componentes: ROL, ACCIÓN, OBJETO y BENEFICIO.
4. Verificación de conformidad con las plantillas P1, P2, P3 y P4.

## Instalación

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m spacy download es_core_news_sm
```

## Uso

Coloca uno o más archivos `.txt` en `data/entrada/`.
Cada línea no vacía debe corresponder a una historia de usuario en español.

Ejecuta:

```powershell
py main.py
```

Los resultados se guardarán en `data/salida/resultados.json`.

## Pruebas

```powershell
py -m unittest discover -s tests -v
```
