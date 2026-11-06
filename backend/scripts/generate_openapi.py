import json
import os
import sys

# Set up paths to allow running from any directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.openapi.utils import get_openapi
from backend.main import app

def generate_openapi_spec():
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    
    # Target path: docs/openapi.json relative to project root
    output_path = os.path.join(PROJECT_ROOT, "docs", "openapi.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"OpenAPI schema generated at: {output_path}")

if __name__ == "__main__":
    generate_openapi_spec()
