import tempfile
import unittest
from pathlib import Path

from src.io_dataset import procesar_directorio


class PipelineConErrorControlado:
    def procesar_historia(self, historia):
        if historia == "historia defectuosa":
            raise ValueError("error de prueba")
        return {
            "componentes": {
                "rol": None,
                "verbo_intencion": None,
                "accion": None,
                "objeto": None,
                "beneficio": None,
            },
            "conformidad": {"es_conforme": False},
        }


class ProcesamientoDatasetTest(unittest.TestCase):
    def test_un_error_no_interrumpe_las_historias_restantes(self):
        with tempfile.TemporaryDirectory() as temporal:
            entrada = Path(temporal)
            (entrada / "historias.txt").write_text(
                "historia valida\nhistoria defectuosa\notra historia valida\n",
                encoding="utf-8",
            )

            lote = procesar_directorio(entrada, PipelineConErrorControlado())

        self.assertEqual(lote["estadisticas"]["historias_procesadas"], 2)
        self.assertEqual(lote["estadisticas"]["errores_procesamiento"], 1)
        self.assertEqual(lote["errores"][0]["archivo"], "historias.txt")
        self.assertEqual(lote["errores"][0]["linea"], 2)
        self.assertEqual(lote["errores"][0]["historia"], "historia defectuosa")
        self.assertIn("ValueError", lote["errores"][0]["error"])


if __name__ == "__main__":
    unittest.main()
