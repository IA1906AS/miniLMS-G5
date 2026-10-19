"""Load a fresh in-memory store from seed data."""

import json
from pathlib import Path
from typing import Any

from app.auth import hash_password


def load_store() -> dict[str, Any]:
    seed_path = Path(__file__).resolve().parent.parent / "seed.json"

    with seed_path.open(encoding="utf-8") as file:
        data = json.load(file)

    for user in data["users"]:
        password = user.pop("password")
        user["password_hash"] = hash_password(password)

    return {
        "users": {user["id"]: user for user in data["users"]},
        "courses": {course["id"]: course for course in data["courses"]},
        "enrollments": data["enrollments"],
    }
