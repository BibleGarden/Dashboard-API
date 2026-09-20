# extract-openapi.py
import argparse
import json
import sys
import yaml
from uvicorn.importer import import_from_string

parser = argparse.ArgumentParser(prog="extract-openapi.py")
parser.add_argument("app",       help='App import string. Eg. "main:app"', default="main:app")
parser.add_argument("--app-dir", help="Directory containing the app", default=None)
parser.add_argument("--out",     help="Output file ending in .json or .yaml", default="openapi.yaml")

def replace_nullable_anyof(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                # FastAPI emits nullable scalars as anyOf. Swift OpenAPI
                # Generator handles that shape less predictably, so normalize
                # it while retaining all validation keywords. Response fields
                # that genuinely return null opt into preserving nullability.
                if 'anyOf' in value and isinstance(value['anyOf'], list):
                    preserve_nullability = value.pop(
                        'x-preserve-nullability', False
                    )
                    schemas = [v for v in value['anyOf'] if isinstance(v, dict)]
                    null_schemas = [v for v in schemas if v.get('type') == 'null']
                    non_null_schemas = [v for v in schemas if v.get('type') != 'null']
                    if len(non_null_schemas) == 1 and null_schemas:
                        actual_schema = non_null_schemas[0]
                        value.pop('anyOf')
                        value.update(actual_schema)
                        if (
                            preserve_nullability
                            and isinstance(actual_schema.get('type'), str)
                        ):
                            value['type'] = [actual_schema['type'], 'null']
                        replace_nullable_anyof(value)
                    else:
                        replace_nullable_anyof(value)
                else:
                    # Recursively traverse nested dictionaries
                    replace_nullable_anyof(value)
            elif isinstance(value, list):
                # Recursively traverse lists
                for item in value:
                    replace_nullable_anyof(item)
    elif isinstance(data, list):
        for item in data:
            replace_nullable_anyof(item)

if __name__ == "__main__":
    args = parser.parse_args()

    if args.app_dir is not None:
        print(f"adding {args.app_dir} to sys.path")
        sys.path.insert(0, args.app_dir)

    print(f"importing app from {args.app}")
    app = import_from_string(args.app)
    openapi = app.openapi()
    version = openapi.get("openapi", "unknown version")

    # hook to solve the issue https://github.com/apple/swift-openapi-generator/issues/513#issuecomment-1911980259
    replace_nullable_anyof(openapi)

    print(f"writing openapi spec v{version}")
    with open(args.out, "w") as f:
        if args.out.endswith(".json"):
            json.dump(openapi, f, indent=2)
        else:
            yaml.dump(openapi, f, sort_keys=False)

    print(f"spec written to {args.out}")
