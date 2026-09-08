from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import spacy
from spacy.tokens import Doc, Span, Token


PLANTILLAS = {
    "P1": {
        "verbo_intencion": "querer",
        "requiere_beneficio": True,
        "orden": "rol_intencion_beneficio",
    },
    "P2": {
        "verbo_intencion": "necesitar",
        "requiere_beneficio": True,
        "orden": "rol_intencion_beneficio",
    },
    "P3": {
        "verbo_intencion": "poder",
        "requiere_beneficio": True,
        "orden": "rol_intencion_beneficio",
    },
    "P4": {
        "verbo_intencion": "poder",
        "requiere_beneficio": True,
        "orden": "beneficio_rol_intencion",
    },
}

class PipelineHistoriasUsuario:
    """
    Versión 0.3:
      Fase 1: Preprocesamiento
      Fase 2: Análisis lingüístico
      Fase 3: Extracción de componentes
      Fase 4: Verificación de conformidad

    La conformidad se evalúa con las plantillas P1, P2, P3 y P4.
    """

    def __init__(self, modelo: str = "es_core_news_sm") -> None:
        self.nlp = spacy.load(modelo)

    def preprocesar(self, doc: Doc) -> Dict[str, List[Dict[str, object]]]:
        """
        Entrada: historia de usuario redactada en español.
        Salida: lista de oraciones tokenizadas.
        """
        return {
            "oraciones": [
                {
                    "texto": oracion.text,
                    "tokens": [token.text for token in oracion if not token.is_space],
                }
                for oracion in doc.sents
                if oracion.text.strip()
            ]
        }

    def analizar_linguisticamente(self, doc: Doc) -> Dict[str, List[Dict[str, object]]]:
        """
        Obtiene POS, lema y dependencias sintácticas.
        Se realiza en una sola ejecución del modelo para evitar
        procesar el mismo texto varias veces innecesariamente.
        """
        resultado: List[Dict[str, object]] = []

        for oracion in doc.sents:
            if not oracion.text.strip():
                continue

            analisis = [
                {
                    "texto": token.text,
                    "lema": token.lemma_,
                    "pos": token.pos_,
                    "dependencia": token.dep_,
                    "depende_de": token.head.text,
                }
                for token in oracion
                if not token.is_space
            ]
            resultado.append({"texto": oracion.text, "tokens": analisis})

        return {"oraciones": resultado}

    def extraer_componentes(self, doc: Doc) -> Dict[str, Optional[str]]:
        """Extrae los componentes de la historia desde el mismo Doc analizado."""
        verbo_intencion = self._buscar_verbo_intencion(doc)
        accion_token = self._extraer_accion(verbo_intencion)

        return {
            "rol": self._extraer_rol(doc, verbo_intencion),
            "verbo_intencion": (
                verbo_intencion.lemma_.lower() if verbo_intencion else None
            ),
            "accion": accion_token.lemma_.lower() if accion_token else None,
            "objeto": self._extraer_objeto(accion_token),
            "beneficio": self._extraer_beneficio(doc, verbo_intencion),
        }

    def _buscar_verbo_intencion(self, doc: Doc) -> Optional[Token]:
        """Localiza el primer verbo de intención de la historia."""
        verbos_intencion = {"querer", "necesitar", "poder", "desear", "requerir"}

        return next(
            (token for token in doc if token.lemma_.lower() in verbos_intencion),
            None,
        )

    def _extraer_rol(
        self, doc: Doc, verbo_intencion: Optional[Token]
    ) -> Optional[str]:
        """Toma el texto situado entre 'Como' y el verbo de intención."""
        if verbo_intencion is None:
            return None

        marcador_como = next(
            (
                token
                for token in doc[verbo_intencion.sent.start:verbo_intencion.i]
                if token.lower_ == "como"
            ),
            None,
        )
        if marcador_como is None or marcador_como.i + 1 >= verbo_intencion.i:
            return None

        rol = doc[marcador_como.i + 1:verbo_intencion.i].text.strip(" ,.;:")
        return rol or None

    def _extraer_accion(self, verbo_intencion: Optional[Token]) -> Optional[Token]:
        """Prioriza complementos verbales xcomp/ccomp del verbo de intención."""
        if verbo_intencion is None:
            return None

        for dependencia in ("xcomp", "ccomp"):
            candidato = next(
                (hijo for hijo in verbo_intencion.children if hijo.dep_ == dependencia),
                None,
            )
            if candidato is not None:
                return candidato

        # Respaldo sencillo ante variaciones del analizador: primer verbo posterior.
        candidato = next(
            (
                token
                for token in verbo_intencion.sent
                if token.i > verbo_intencion.i and token.pos_ in {"VERB", "AUX"}
            ),
            None,
        )
        if candidato is not None:
            return candidato

        return next(
            (
                token
                for token in verbo_intencion.sent
                if token.i > verbo_intencion.i
                and token.is_alpha
                and token.lower_ not in {"que", "para"}
            ),
            None,
        )

    def _buscar_marcador_beneficio(
        self, oracion: Span, desde: int
    ) -> Optional[Tuple[int, int]]:
        """Retorna los índices de inicio y fin del marcador de beneficio."""
        patrones = (
            ("con", "el", "fin", "de"),
            ("a", "fin", "de"),
            ("para", "que"),
            ("para",),
        )
        tokens = list(oracion)
        for posicion, token in enumerate(tokens):
            if token.i < desde:
                continue
            for patron in patrones:
                fin = posicion + len(patron)
                if tuple(t.lower_ for t in tokens[posicion:fin]) == patron:
                    return token.i, token.i + len(patron)
        return None

    def _extraer_objeto(self, accion: Optional[Token]) -> Optional[str]:
        """Extrae el complemento de la acción sin confiar en su etiqueta POS."""
        if accion is None:
            return None

        objeto = None
        for dependencia in ("obj", "iobj", "obl"):
            objeto = next(
                (hijo for hijo in accion.children if hijo.dep_ == dependencia),
                None,
            )
            if objeto is not None:
                break
        if objeto is None:
            marcador = self._buscar_marcador_beneficio(accion.sent, accion.i + 1)
            limite = marcador[0] if marcador else accion.sent.end
            candidatos = [
                token for token in accion.doc[accion.i + 1:limite]
                if not token.is_punct and not token.is_space
            ]
            if not candidatos:
                return None
            frase = accion.doc[candidatos[0].i:candidatos[-1].i + 1].text
            return frase.strip(" ,.;:") or None

        marcador = self._buscar_marcador_beneficio(accion.sent, accion.i + 1)
        limite = marcador[0] if marcador else accion.sent.end
        indices = [
            token.i
            for token in objeto.subtree
            if token.i < limite and not token.is_punct
        ]
        if not indices:
            return None

        frase = accion.doc[min(indices):max(indices) + 1].text.strip(" ,.;:")
        return frase or None

    def _extraer_beneficio(
        self, doc: Doc, verbo_intencion: Optional[Token]
    ) -> Optional[str]:
        """
        Extrae el beneficio de la historia.

        Los marcadores 'para que', 'con el fin de' y 'a fin de'
        se consideran marcadores directos de beneficio.

        El marcador simple 'para' solo se considera beneficio
        cuando introduce una expresión verbal.
        """

        if verbo_intencion is None:
            return None

        oracion = verbo_intencion.sent

        marcador = self._buscar_marcador_beneficio(
            oracion,
            oracion.start
        )

        if marcador is None:
            return None

        inicio_marcador, fin_marcador = marcador

        # ------------------------------------------------------
        # CORRECCIÓN:
        # 'para' por sí solo es ambiguo.
        # Solo se acepta como beneficio si después aparece
        # una forma verbal.
        # ------------------------------------------------------

        tokens_marcador = [
            doc[i].lower_
            for i in range(
                inicio_marcador,
                fin_marcador
            )
        ]

        if tokens_marcador == ["para"]:

            tokens_posteriores = [
                token
                for token in doc[
                    fin_marcador:oracion.end
                ]
                if not token.is_punct
                and not token.is_space
            ]

            if not tokens_posteriores:
                return None

            tiene_verbo = any(
                token.pos_ in {"VERB", "AUX"}
                for token in tokens_posteriores
            )

            if not tiene_verbo:
                return None

        # ------------------------------------------------------
        # P4:
        # el beneficio aparece antes del rol
        # ------------------------------------------------------

        fin = oracion.end

        marcador_como = next(
            (
                token.i
                for token in oracion
                if token.lower_ == "como"
                and token.i > fin_marcador
            ),
            None,
        )

        if (
            inicio_marcador < verbo_intencion.i
            and marcador_como is not None
        ):
            fin = marcador_como

        if fin_marcador >= fin:
            return None

        beneficio = doc[
            fin_marcador:fin
        ].text.strip(" ,.;:")

        return beneficio or None

    def verificar_conformidad(
        self, doc: Doc, componentes: Dict[str, Optional[str]]
    ) -> Dict[str, object]:
        """Evalúa todas las plantillas y selecciona la conforme o más cercana."""
        evaluaciones = [
            self._evaluar_plantilla(doc, componentes, nombre, configuracion)
            for nombre, configuracion in PLANTILLAS.items()
        ]

        conforme = next(
            (evaluacion for evaluacion in evaluaciones if all(evaluacion["reglas"].values())),
            None,
        )
        if conforme is not None:
            return {
                "es_conforme": True,
                "plantilla": conforme["plantilla"],
                "reglas": conforme["reglas"],
                "incumplimientos": [],
            }

        # En empate se favorece la plantilla cuyo verbo de intención coincide.
        mas_cercana = max(
            evaluaciones,
            key=lambda evaluacion: (
                sum(evaluacion["reglas"].values()),
                evaluacion["reglas"]["verbo_intencion"],
            ),
        )
        return {
            "es_conforme": False,
            "plantilla": None,
            "plantilla_mas_cercana": mas_cercana["plantilla"],
            "reglas": mas_cercana["reglas"],
            "incumplimientos": self._describir_incumplimientos(
                mas_cercana["reglas"]
            ),
        }

    def _evaluar_plantilla(
        self,
        doc: Doc,
        componentes: Dict[str, Optional[str]],
        nombre: str,
        configuracion: Dict[str, object],
    ) -> Dict[str, object]:
        reglas = {
            "rol": componentes["rol"] is not None,
            "accion": componentes["accion"] is not None,
            "objeto": componentes["objeto"] is not None,
            "beneficio": (
                componentes["beneficio"] is not None
                if configuracion["requiere_beneficio"]
                else True
            ),
            "verbo_intencion": (
                componentes["verbo_intencion"] == configuracion["verbo_intencion"]
            ),
            "estructura": self._verificar_estructura(doc, configuracion["orden"]),
        }
        return {"plantilla": nombre, "reglas": reglas}

    def _verificar_estructura(self, doc: Doc, orden: object) -> bool:
        verbo = self._buscar_verbo_intencion(doc)
        if verbo is None:
            return False

        oracion = verbo.sent
        posicion_rol = next(
            (token.i for token in oracion if token.lower_ == "como"),
            None,
        )
        marcador_beneficio = self._buscar_marcador_beneficio(oracion, oracion.start)
        posicion_beneficio = marcador_beneficio[0] if marcador_beneficio else None
        if posicion_rol is None:
            return False

        if orden == "beneficio_rol_intencion":
            return (
                posicion_beneficio is not None
                and posicion_beneficio < posicion_rol < verbo.i
            )

        # Si falta el beneficio, su ausencia se informa en RG4; el orden parcial
        # rol-intención puede seguir siendo estructuralmente compatible.
        return posicion_rol < verbo.i and (
            posicion_beneficio is None or verbo.i < posicion_beneficio
        )

    def _describir_incumplimientos(self, reglas: Dict[str, bool]) -> List[str]:
        mensajes = {
            "rol": "Rol no identificado",
            "accion": "Acción no identificada",
            "objeto": "Objeto no identificado",
            "beneficio": "Beneficio no identificado",
            "verbo_intencion": "Verbo de intención incompatible",
            "estructura": "Estructura incompatible con la plantilla",
        }
        return [mensajes[regla] for regla, cumple in reglas.items() if not cumple]

    def procesar_historia(self, historia: str):
        doc = self.nlp(historia.strip())
        componentes = self.extraer_componentes(doc)

        return {
            "historia_original": historia.strip(),
            "preprocesamiento": self.preprocesar(doc),
            "analisis_linguistico": self.analizar_linguisticamente(doc),
            "componentes": componentes,
            "conformidad": self.verificar_conformidad(doc, componentes)
        }
