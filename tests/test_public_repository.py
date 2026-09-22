from __future__ import annotations

import csv
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicRepositoryContracts(unittest.TestCase):
    def test_restricted_file_types_are_absent(self):
        forbidden = {".gpkg", ".shp", ".shx", ".dbf", ".tif", ".tiff", ".pt", ".pth", ".onnx", ".zip", ".docx", ".pkl", ".pickle", ".npy", ".npz", ".parquet", ".feather", ".h5", ".hdf5"}
        found = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and p.suffix.lower() in forbidden]
        self.assertEqual(found, [])

    def test_restricted_names_are_absent(self):
        patterns = ("dataset.csv", "dataset.gpkg", "val_catas.csv", "fold_assignments.csv", "split.csv", "mascara_imputacion.csv")
        found = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name.lower() in patterns]
        self.assertEqual(found, [])

    def test_no_absolute_personal_paths_in_text(self):
        suffixes = {".py", ".md", ".txt", ".yml", ".yaml", ".toml"}
        bad = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in suffixes:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"C:[\\/]Users[\\/]", text, flags=re.IGNORECASE):
                bad.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(bad, [])

    def test_published_tables_have_no_record_identifiers(self):
        forbidden_columns = {"predio", "predio_join", "x", "y", "geometry", "lat", "lon", "longitude", "latitude"}
        for path in list(ROOT.glob("results/**/*.csv")) + list(ROOT.glob("revision_metodologica/salidas/**/*.csv")):
            with path.open(encoding="utf-8", newline="") as handle:
                header = {column.strip().lower() for column in next(csv.reader(handle))}
            self.assertFalse(header & forbidden_columns, path.name)

    def test_conjunto_prueba_ranking_matches_thesis(self):
        with (ROOT / "results" / "conjunto_prueba.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        # El orden cambio al pasar los modelos estocasticos a la media de sus
        # diez replicas: GNNWR queda en 97,89 y adelanta a GWR, que esta en
        # 98,15. Los separan 0,26, dentro de la variacion de GNNWR entre
        # semillas. Este test verifica el orden, no una equivalencia inferencial.
        self.assertEqual([row["model"] for row in rows], ["Random Forest", "SANNWR", "GNNWR", "GWR", "OLS"])
        self.assertAlmostEqual(float(rows[0]["rmse"]), 76.75)
        self.assertAlmostEqual(float(rows[-1]["rmse"]), 139.01)

    def test_validation_figure_reports_both_cross_validation_deviations(self):
        source = (ROOT / "figures" / "publication" / "generate_summary_figures.py").read_text(encoding="utf-8")
        self.assertIn('yerr=validacion_aleatoria["rmse_sd"]', source)
        self.assertIn('yerr=bloques_espaciales["rmse_sd_regions"]', source)
        self.assertIn("Validación cruzada aleatoria: media ± DE de 5 particiones", source)
        self.assertIn("Validación por bloques espaciales: media ± DE de 5 regiones", source)

    def test_markdown_uses_final_thesis_terminology(self):
        forbidden = ("—", "Holdout", "holdout", "RandomKFold", "SpatialBlock", " fold", "fold ")
        found = []
        for path in ROOT.rglob("*.md"):
            if ".git" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(term in text for term in forbidden):
                found.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
