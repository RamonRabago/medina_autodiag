"""
Exporta el esquema OpenAPI a un archivo JSON estático.
Útil para publicar documentación por separado o integrar con herramientas externas.

  python scripts/export_openapi.py

Genera docs/openapi.json (o ruta indicada por OPENAPI_OUTPUT).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    from app.main import app

    schema = app.openapi()
    out_path = os.environ.get("OPENAPI_OUTPUT", os.path.join(ROOT, "docs", "openapi.json"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"OpenAPI exportado a: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
