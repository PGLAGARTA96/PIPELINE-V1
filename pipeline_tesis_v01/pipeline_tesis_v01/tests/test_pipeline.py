import unittest
from unittest.mock import Mock

from src.pipeline import PipelineHistoriasUsuario


class PreprocesamientoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = PipelineHistoriasUsuario()

    def preprocesar(self, historia):
        return self.pipeline.procesar_historia(historia)["preprocesamiento"]

    def test_una_oracion(self):
        resultado = self.preprocesar("Como usuario quiero registrar pedidos.")
        self.assertEqual(len(resultado["oraciones"]), 1)

    def test_dos_oraciones(self):
        resultado = self.preprocesar("Quiero registrar pedidos. Debo validarlos.")
        self.assertEqual(len(resultado["oraciones"]), 2)

    def test_tokenizacion_y_puntuacion(self):
        tokens = self.preprocesar(
            "Como usuario, quiero registrar pedidos."
        )["oraciones"][0]["tokens"]
        self.assertIn(",", tokens)
        self.assertIn(".", tokens)
        self.assertIn("pedidos", tokens)

    def test_espacios_multiples_no_generan_tokens_vacios(self):
        tokens = self.preprocesar(
            "Como   usuario quiero registrar pedidos."
        )["oraciones"][0]["tokens"]
        self.assertNotIn("", tokens)
        self.assertFalse(any(token.isspace() for token in tokens))


class ExtraccionComponentesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = PipelineHistoriasUsuario()

    def extraer(self, historia):
        # La prueba también respeta el uso de un solo Doc por historia.
        doc = self.pipeline.nlp(historia)
        return self.pipeline.extraer_componentes(doc)

    def test_historia_completa(self):
        componentes = self.extraer(
            "Como diseñador de interfaz quiero actualizar la página de recursos "
            "para que coincida con el nuevo diseño."
        )
        self.assertEqual(componentes["rol"], "diseñador de interfaz")
        self.assertEqual(componentes["accion"], "actualizar")
        self.assertEqual(componentes["objeto"], "la página de recursos")
        self.assertEqual(componentes["beneficio"], "coincida con el nuevo diseño")

    def test_historia_sin_beneficio(self):
        componentes = self.extraer("Como usuario quiero registrar pedidos.")
        self.assertEqual(componentes["rol"], "usuario")
        self.assertEqual(componentes["verbo_intencion"], "querer")
        self.assertEqual(componentes["accion"], "registrar")
        self.assertEqual(componentes["objeto"], "pedidos")
        self.assertIsNone(componentes["beneficio"])

    def test_ejemplo_exacto_historia_completa(self):
        componentes = self.extraer(
            "Como usuario quiero registrar pedidos para mejorar el control."
        )
        self.assertEqual(componentes, {
            "rol": "usuario",
            "verbo_intencion": "querer",
            "accion": "registrar",
            "objeto": "pedidos",
            "beneficio": "mejorar el control",
        })

    def test_rol_compuesto(self):
        componentes = self.extraer(
            "Como usuario de la agencia necesito consultar reportes."
        )
        self.assertEqual(componentes["rol"], "usuario de la agencia")

    def test_objeto_compuesto(self):
        componentes = self.extraer(
            "Como administrador deseo actualizar los datos del cliente."
        )
        self.assertEqual(componentes["objeto"], "los datos del cliente")


class VerificacionConformidadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = PipelineHistoriasUsuario()

    def procesar(self, historia):
        return self.pipeline.procesar_historia(historia)

    def test_spacy_se_ejecuta_una_vez_por_historia(self):
        nlp_original = self.pipeline.nlp
        nlp_observado = Mock(wraps=nlp_original)
        self.pipeline.nlp = nlp_observado
        try:
            self.pipeline.procesar_historia(
                "Como usuario quiero registrar pedidos para mejorar el control."
            )
        finally:
            self.pipeline.nlp = nlp_original
        nlp_observado.assert_called_once()

    def test_p1_conforme(self):
        resultado = self.procesar(
            "Como usuario quiero registrar pedidos para mejorar el control."
        )
        self.assertEqual(resultado["componentes"]["verbo_intencion"], "querer")
        self.assertEqual(resultado["componentes"]["objeto"], "pedidos")
        self.assertTrue(resultado["conformidad"]["es_conforme"])
        self.assertEqual(resultado["conformidad"]["plantilla"], "P1")

    def test_p1_no_conforme_sin_beneficio(self):
        resultado = self.procesar("Como usuario quiero registrar pedidos.")
        self.assertIsNone(resultado["componentes"]["beneficio"])
        self.assertFalse(resultado["conformidad"]["es_conforme"])
        self.assertEqual(resultado["conformidad"]["plantilla_mas_cercana"], "P1")
        self.assertIn(
            "Beneficio no identificado", resultado["conformidad"]["incumplimientos"]
        )

    def test_p2_conforme(self):
        resultado = self.procesar(
            "Como administrador necesito generar reportes para mejorar el seguimiento."
        )
        self.assertEqual(resultado["componentes"]["verbo_intencion"], "necesitar")
        self.assertTrue(resultado["conformidad"]["es_conforme"])
        self.assertEqual(resultado["conformidad"]["plantilla"], "P2")

    def test_p3_conforme(self):
        resultado = self.procesar(
            "Como usuario puedo consultar reportes para revisar la información."
        )
        self.assertEqual(resultado["componentes"]["verbo_intencion"], "poder")
        self.assertTrue(resultado["conformidad"]["es_conforme"])
        self.assertEqual(resultado["conformidad"]["plantilla"], "P3")

    def test_rol_y_objeto_compuestos(self):
        resultado = self.procesar(
            "Como diseñador de interfaz quiero actualizar la página de recursos "
            "para mejorar la navegación."
        )
        self.assertEqual(resultado["componentes"]["rol"], "diseñador de interfaz")
        self.assertIn("página de recursos", resultado["componentes"]["objeto"])
        self.assertTrue(resultado["conformidad"]["es_conforme"])
        self.assertEqual(resultado["conformidad"]["plantilla"], "P1")

    def test_historia_incompleta_sin_rol(self):
        resultado = self.procesar("Quiero registrar pedidos.")
        self.assertIsNone(resultado["componentes"]["rol"])
        self.assertFalse(resultado["conformidad"]["es_conforme"])
        self.assertIn("Rol no identificado", resultado["conformidad"]["incumplimientos"])

    def test_historia_sin_verbo_de_intencion_no_genera_excepcion(self):
        resultado = self.procesar("El usuario registra pedidos.")
        self.assertIsNone(resultado["componentes"]["verbo_intencion"])
        self.assertFalse(resultado["conformidad"]["es_conforme"])

    def test_p4_conforme(self):
        resultado = self.procesar(
            "Con el fin de mejorar el control, como usuario, puedo registrar pedidos."
        )
        componentes = resultado["componentes"]
        self.assertEqual(componentes["rol"], "usuario")
        self.assertEqual(componentes["verbo_intencion"], "poder")
        self.assertEqual(componentes["accion"], "registrar")
        self.assertEqual(componentes["objeto"], "pedidos")
        self.assertIsNotNone(componentes["beneficio"])
        self.assertTrue(resultado["conformidad"]["es_conforme"])
        self.assertEqual(resultado["conformidad"]["plantilla"], "P4")


if __name__ == "__main__":
    unittest.main()
