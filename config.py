import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    od_email: str = field(default_factory=lambda: os.getenv("OD_EMAIL", ""))
    od_password: str = field(default_factory=lambda: os.getenv("OD_PASSWORD", ""))
    chat_id: int | None = field(
        default_factory=lambda: (
            int(os.getenv("CHAT_ID")) if os.getenv("CHAT_ID") else None
        )
    )
    poll_interval: int = field(
        default_factory=lambda: int(os.getenv("POLL_INTERVAL", "60"))
    )
    base_url: str = "https://onlydrafts.racing"

    def validate(self):
        missing = []
        if not self.bot_token:
            missing.append("BOT_TOKEN")
        if not self.od_email:
            missing.append("OD_EMAIL")
        if not self.od_password:
            missing.append("OD_PASSWORD")
        if missing:
            raise ValueError(
                f"Missing required env vars: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill them in."
            )
