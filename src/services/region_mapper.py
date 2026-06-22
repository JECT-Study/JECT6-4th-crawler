from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


_REGION_RAW_PATH = Path(__file__).resolve().parents[2] / "region_raw.json"
_SEPARATORS_RE = re.compile(r"[\s,/|>·ㆍ_\-]+")

_PARENT_ALIASES: dict[str, tuple[str, ...]] = {
    "서울특별시": ("서울",),
    "부산광역시": ("부산",),
    "대구광역시": ("대구",),
    "인천광역시": ("인천",),
    "광주광역시": ("광주",),
    "대전광역시": ("대전",),
    "울산광역시": ("울산",),
    "세종특별자치시": ("세종",),
    "경기도": ("경기",),
    "강원특별자치도": ("강원", "강원도"),
    "충청북도": ("충북", "충청북"),
    "충청남도": ("충남", "충청남"),
    "전북특별자치도": ("전북", "전라북", "전라북도"),
    "전라남도": ("전남", "전라남"),
    "경상북도": ("경북", "경상북"),
    "경상남도": ("경남", "경상남"),
    "제주특별자치도": ("제주", "제주도"),
}


@dataclass(frozen=True)
class RegionIds:
    parent_region_id: int | None = None
    child_region_id: int | None = None
    parent_name: str | None = None
    child_name: str | None = None


@dataclass(frozen=True)
class _RegionMatch:
    parent: dict[str, Any]
    child: dict[str, Any] | None = None


@dataclass(frozen=True)
class _RegionIndex:
    parent_by_alias: dict[str, dict[str, Any]]
    child_by_parent_alias: dict[int, dict[str, dict[str, Any]]]
    child_matches_by_alias: dict[str, list[_RegionMatch]]
    parent_aliases_by_length: tuple[str, ...]
    child_aliases_by_parent_length: dict[int, tuple[str, ...]]
    child_aliases_by_length: tuple[str, ...]


def resolve_region_ids(
    region_depth1: str | None,
    region_depth2: str | None = None,
) -> RegionIds:
    index = _load_region_index()
    if not index.parent_by_alias:
        return RegionIds()

    parts = [part for part in (region_depth1, region_depth2) if part]
    if not parts:
        return RegionIds()

    combined = _normalize(" ".join(parts))
    parent = _find_parent(index, region_depth1, combined)
    child = _find_child(index, parent, region_depth2, combined)

    if parent is None and child is not None:
        parent = _find_parent_by_id(index, child.get("parent_id"))

    return RegionIds(
        parent_region_id=parent.get("id") if parent else None,
        child_region_id=child.get("id") if child else None,
        parent_name=parent.get("name") if parent else None,
        child_name=child.get("name") if child else None,
    )


@lru_cache(maxsize=1)
def _load_region_index() -> _RegionIndex:
    try:
        raw_regions = json.loads(_REGION_RAW_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw_regions = []

    parent_by_alias: dict[str, dict[str, Any]] = {}
    child_by_parent_alias: dict[int, dict[str, dict[str, Any]]] = {}
    child_matches_by_alias: dict[str, list[_RegionMatch]] = {}

    if not isinstance(raw_regions, list):
        raw_regions = []

    for parent in raw_regions:
        if not isinstance(parent, dict):
            continue

        parent_id = parent.get("id")
        if not isinstance(parent_id, int):
            continue

        for alias in _parent_aliases(parent.get("name")):
            parent_by_alias[alias] = parent

        child_aliases: dict[str, dict[str, Any]] = {}
        for child in parent.get("children") or []:
            if not isinstance(child, dict):
                continue

            for alias in _child_aliases(child.get("name")):
                child_aliases[alias] = child
                child_matches_by_alias.setdefault(alias, []).append(
                    _RegionMatch(parent=parent, child=child)
                )

        child_by_parent_alias[parent_id] = child_aliases

    parent_aliases_by_length = tuple(
        sorted(parent_by_alias, key=len, reverse=True)
    )
    child_aliases_by_parent_length = {
        parent_id: tuple(sorted(child_aliases, key=len, reverse=True))
        for parent_id, child_aliases in child_by_parent_alias.items()
    }
    child_aliases_by_length = tuple(
        sorted(child_matches_by_alias, key=len, reverse=True)
    )

    return _RegionIndex(
        parent_by_alias=parent_by_alias,
        child_by_parent_alias=child_by_parent_alias,
        child_matches_by_alias=child_matches_by_alias,
        parent_aliases_by_length=parent_aliases_by_length,
        child_aliases_by_parent_length=child_aliases_by_parent_length,
        child_aliases_by_length=child_aliases_by_length,
    )


def _find_parent(
    index: _RegionIndex,
    region_depth1: str | None,
    combined: str,
) -> dict[str, Any] | None:
    depth1 = _normalize(region_depth1)
    if depth1 in index.parent_by_alias:
        return index.parent_by_alias[depth1]

    for text in (depth1, combined):
        if not text:
            continue

        for alias in index.parent_aliases_by_length:
            if alias in text:
                return index.parent_by_alias[alias]

    return None


def _find_child(
    index: _RegionIndex,
    parent: dict[str, Any] | None,
    region_depth2: str | None,
    combined: str,
) -> dict[str, Any] | None:
    depth2 = _normalize(region_depth2)

    if parent:
        parent_id = parent.get("id")
        child_aliases = index.child_by_parent_alias.get(parent_id, {})

        if depth2 in child_aliases:
            return child_aliases[depth2]

        for text in (depth2, combined):
            if not text:
                continue

            for alias in index.child_aliases_by_parent_length.get(parent_id, ()):
                if alias in text:
                    return child_aliases[alias]

        return None

    if depth2:
        unique_match = _get_unique_child_match(index, depth2)
        if unique_match:
            return unique_match.child

    for alias in index.child_aliases_by_length:
        if alias in combined:
            unique_match = _get_unique_child_match(index, alias)
            if unique_match:
                return unique_match.child

    return None


def _find_parent_by_id(
    index: _RegionIndex,
    parent_id: int | None,
) -> dict[str, Any] | None:
    if parent_id is None:
        return None

    for parent in index.parent_by_alias.values():
        if parent.get("id") == parent_id:
            return parent

    return None


def _get_unique_child_match(
    index: _RegionIndex,
    alias: str,
) -> _RegionMatch | None:
    matches = index.child_matches_by_alias.get(alias, [])
    parent_ids = {match.parent.get("id") for match in matches}
    return matches[0] if len(parent_ids) == 1 else None


def _parent_aliases(name: Any) -> set[str]:
    normalized_name = _normalize(name)
    if not normalized_name:
        return set()

    aliases = {normalized_name}
    for alias in _PARENT_ALIASES.get(str(name), ()):
        normalized_alias = _normalize(alias)
        if normalized_alias:
            aliases.add(normalized_alias)

    return aliases


def _child_aliases(name: Any) -> set[str]:
    normalized_name = _normalize(name)
    if not normalized_name:
        return set()

    aliases = {normalized_name}
    if len(normalized_name) >= 3 and normalized_name[-1] in {"시", "군", "구"}:
        aliases.add(normalized_name[:-1])

    return aliases


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return _SEPARATORS_RE.sub("", str(value).strip().lower())
