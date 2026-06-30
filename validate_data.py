from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "records"

REQUIRED = [
    DATA_DIR / "samples.csv",
    DATA_DIR / "bom_components.csv",
    DATA_DIR / "test_catalog.csv",
    DATA_DIR / "test_runs.csv",
    DATA_DIR / "defects.csv",
    DATA_DIR / "availability.csv",
    DATA_DIR / "order_requests.csv",
]

if __name__ == "__main__":
    missing = [p for p in REQUIRED if not p.exists()]
    if not missing:
        print("Datenbestand ist bereits vorhanden. Es wird nichts überschrieben.")
        print("Falls du den Datenbestand neu bereitstellen willst, stelle die CSV-Dateien im Datenordner wieder her.")
        sys.exit(0)

    print("Einige Datendateien fehlen:")
    for p in missing:
        print(" -", p)
    print("\nDieses Repo enthält die benötigten CSV-Dateien bereits.")
    print("Bitte entpacke das ZIP vollständig oder stelle die Dateien im Datenordner wieder her.")
    sys.exit(1)
