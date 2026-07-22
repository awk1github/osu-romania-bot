from __future__ import annotations

from datetime import datetime
from typing import Any


def mod_acronyms(score_or_mods: dict[str, Any] | list[Any] | None) -> list[str]:
    if isinstance(score_or_mods, dict):
        mods = score_or_mods.get("mods") or []
    else:
        mods = score_or_mods or []

    acronyms: list[str] = []

    for mod in mods:
        if isinstance(mod, str):
            acronyms.append(mod)
        elif isinstance(mod, dict):
            acronym = mod.get("acronym")
            if acronym:
                acronyms.append(str(acronym))

    return acronyms


def format_mods(score_or_mods: dict[str, Any] | list[Any] | None) -> str:
    acronyms = mod_acronyms(score_or_mods)
    return "".join(acronyms) if acronyms else "NM"


def score_value(score: dict[str, Any]) -> int:
    # Prefer the lazer total score, then the classic/legacy equivalents.
    for key in (
        "total_score",
        "classic_total_score",
        "legacy_total_score",
        "score",
    ):
        value = score.get(key)
        if value is None:
            continue

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return 0


def played_at(score: dict[str, Any]) -> datetime | None:
    raw_value = score.get("ended_at") or score.get("created_at")

    if not raw_value:
        return None

    try:
        return datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
    except ValueError:
        return None


def miss_count(score: dict) -> int:
    statistics = score.get("statistics") or {}

    return int(
        statistics.get(
            "miss",
            statistics.get("count_miss", 0),
        )
    )


def score_url(score: dict[str, Any], ruleset: str = "osu") -> str | None:
    score_id = score.get("id")
    legacy_score_id = score.get("legacy_score_id")

    if score_id is not None:
        return f"https://osu.ppy.sh/scores/{score_id}"

    if legacy_score_id is not None:
        return f"https://osu.ppy.sh/scores/{ruleset}/{legacy_score_id}"

    return None
