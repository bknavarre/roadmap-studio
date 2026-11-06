#!/usr/bin/env python3
"""Promote candidate JSON only when roadmap data actually changed."""
import json
import shutil
from pathlib import Path

candidate_data = Path("build/roadmap_data.json")
candidate_status = Path("build/roadmap_status.json")
public_data = Path("public/roadmap_data.json")
public_status = Path("public/roadmap_status.json")

new = json.loads(candidate_data.read_text(encoding="utf-8"))
old = json.loads(public_data.read_text(encoding="utf-8")) if public_data.exists() else None

# Ignore generated timestamp. Compare the actual roadmap payload and counts.
changed = old is None or any([
    new.get("sourceCount") != old.get("sourceCount"),
    new.get("expandedCount") != old.get("expandedCount"),
    new.get("items") != old.get("items"),
])

if not changed:
    print("No normalized roadmap data changes. Nothing will be committed.")
else:
    public_data.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate_data, public_data)
    shutil.copy2(candidate_status, public_status)
    print(f"Roadmap changed: {new['sourceCount']} source records, {new['expandedCount']} roadmap lines. Promoted candidate JSON.")
