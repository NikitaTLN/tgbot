from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CACHE_FILE = Path("races_cache.json")


class OnlyDraftsClient:
    def __init__(self, email: str, password: str, base_url: str = "https://onlydrafts.racing"):
        self.base_url = base_url.rstrip("/")
        self._email = email
        self._password = password
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Content-Type": "application/json"},
            follow_redirects=True,
        )
        self._logged_in = False
        self._seen_race_ids: set[int] = set()
        self._load_cache()

    async def login(self) -> None:
        logger.info("Logging into OnlyDrafts...")
        resp = await self._client.post(
            "/api/auth/login",
            json={"email": self._email, "password": self._password},
        )
        data = resp.json()
        if resp.status_code != 200:
            raise RuntimeError(f"Login failed: {data.get('error', resp.text)}")
        self._logged_in = True
        logger.info("Login successful — user: %s", data.get("user", {}).get("displayName", "?"))

    async def get_races(self) -> list[dict[str, Any]]:
        if not self._logged_in:
            raise RuntimeError("Not logged in — call login() first")
        resp = await self._client.get("/api/races")
        data = resp.json()
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch races: {data.get('error', resp.text)}")
        return data

    def get_new_races(self, races: list[dict]) -> list[dict]:
        new = [r for r in races if r["id"] not in self._seen_race_ids]
        if new:
            self._seen_race_ids.update(r["id"] for r in new)
            self._save_cache()
        return new

    def _cache_path(self) -> Path:
        return CACHE_FILE

    def _load_cache(self) -> None:
        path = self._cache_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._seen_race_ids = set(data.get("seen_ids", []))
                logger.info("Loaded %d seen race IDs from cache", len(self._seen_race_ids))
            except Exception as exc:
                logger.warning("Failed to load race cache: %s", exc)

    def _save_cache(self) -> None:
        path = self._cache_path()
        try:
            path.write_text(json.dumps({"seen_ids": list(self._seen_race_ids)}))
        except Exception as exc:
            logger.warning("Failed to save race cache: %s", exc)

    async def close(self) -> None:
        await self._client.aclose()


def format_race_message(race: dict) -> str:
    name = race.get("name", "Без названия")
    track = race.get("track", "—")
    laps = race.get("laps", "—")
    race_date = race.get("race_date", "")
    cars_raw = race.get("cars")
    cars: list[str] = []
    if isinstance(cars_raw, list):
        cars = cars_raw
    elif isinstance(cars_raw, str):
        try:
            cars = json.loads(cars_raw)
        except (json.JSONDecodeError, TypeError):
            cars = [cars_raw] if cars_raw else []

    date_str = "—"
    if race_date:
        try:
            dt = datetime.fromisoformat(race_date)
            date_str = dt.strftime("%d.%m.%Y %H:%M")
        except (ValueError, TypeError):
            date_str = race_date

    stages_raw = race.get("stages", [])
    stages = sorted(stages_raw, key=lambda s: s.get("n", 0)) if stages_raw else []
    total_laps = sum(s.get("laps", 0) for s in stages)

    lines = [
        f"🏁 <b>{name}</b>",
        f"📍 Трасса: {track}",
        f"📅 Дата: {date_str}",
    ]
    if stages:
        for s in stages:
            lines.append(f"  ● Стейдж {s['n']}: {s['laps']} кр.")
        lines.append(f"  ────────  = {total_laps} кр.")
    else:
        lines.append(f"🔄 Кругов: {laps}")
    if cars:
        lines.append(f"🚗 Машины: {', '.join(cars)}")

    lines.append(f'\n🔗 <a href="https://onlydrafts.racing">OnlyDrafts.racing</a>')
    return "\n".join(lines)


def format_no_races_message() -> str:
    return (
        "👋 <b>Бот запущен</b>\n"
        "На данный момент доступных гонок нет.\n"
        "Я буду следить за новыми и сообщу, когда они появятся.\n\n"
        f'🔗 <a href="https://onlydrafts.racing">OnlyDrafts.racing</a>'
    )
