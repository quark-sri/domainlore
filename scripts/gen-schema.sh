#!/usr/bin/env bash
# Regenerate the JSON Schemas in src/domainlore/schemas/ from schema/domainlore.yaml (LinkML).
# Run after every schema change; CI checks that the committed output is current.
set -euo pipefail
cd "$(dirname "$0")/.."
out=src/domainlore/schemas
for class in Entity Rule Actor Journey Screen Term Gap SpecConflict; do
  uvx -p 3.12 --from 'linkml==1.12.1' gen-json-schema --top-class "$class" --not-closed \
    schema/domainlore.yaml 2>/dev/null > "$out/$class.json"
done
# LinkML's Any excludes arrays; OKF allows `verified` as a list, so widen it.
python3 - "$out" <<'PY'
import json, pathlib, sys
for path in sorted(pathlib.Path(sys.argv[1]).glob("*.json")):
    schema = json.loads(path.read_text())
    schema["$defs"]["Any"] = {"description": "Any value."}
    path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
PY
echo "Wrote $(ls "$out" | wc -l | tr -d ' ') schemas to $out"
