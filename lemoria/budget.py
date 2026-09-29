"""A monthly token budget, and what is left of it.

The Omarchy panel already knows how to draw a `balance: {funded, remaining}`
meter, so the budget publishes itself in that shape and the meter comes for
free. What we had to decide for ourselves is the *unit*.

It cannot be dollars. opencode records `cost: 0.0` for every provider reached
through a subscription, so a dollar budget would sit at zero forever and look
like a bug. Tokens are the one number opencode reports honestly, and they are
what the user actually rations.

No budget configured is not an error: `funded` is None, the panel hides the
meter, and nothing here guesses a number on the user's behalf.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# At 80% the meter turns amber: still fine, but worth knowing before it is
# not. Only a budget the user set is ever compared against.
WARN_AT = 0.8

_UNITS = {"k": 1_000, "m": 1_000_000, "g": 1_000_000_000, "b": 1_000_000_000}
_LIMIT = re.compile(r"^\s*([0-9][0-9_,.]*)\s*([kmgb]?)\s*$", re.IGNORECASE)


def parse_limit(text: str) -> int:
    """Turn what a human types into a token count.

    ``500M``, ``500m``, ``2_000_000`` and ``1.5B`` all mean something. A bare
    number is tokens, because that is the unit everything else in this tool is
    already reported in and a wrong guess there is a silent one.
    """
    match = _LIMIT.match(text)
    if not match:
        raise ValueError(f"cannot read a token count out of {text!r}")
    number, unit = match.groups()
    try:
        value = float(number.replace("_", "").replace(",", ""))
    except ValueError as exc:  # pragma: no cover - the regex already filtered
        raise ValueError(f"cannot read a token count out of {text!r}") from exc
    if value <= 0:
        raise ValueError("a budget of zero is not a budget")
    return int(value * _UNITS.get(unit.lower(), 1))


def format_limit(tokens: int) -> str:
    """The same number, the way the panel shows it."""
    for scale, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if tokens >= scale:
            value = tokens / scale
            return f"{value:.1f}".rstrip("0").rstrip(".") + suffix
    return str(tokens)


def default_budget_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(config_home) / "lemoria" / "budget.json"


@dataclass(frozen=True)
class Budget:
    """A monthly token ceiling, or the absence of one."""

    monthly_tokens: int | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> Budget:
        target = path or default_budget_path()
        if not target.exists():
            return cls()
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupt file must not take the timer down with it. The panel
            # degrades to "no budget" and the user can re-set it.
            return cls()
        value = raw.get("monthlyTokens") if isinstance(raw, dict) else None
        return cls(monthly_tokens=int(value) if isinstance(value, int) and value > 0 else None)

    def save(self, path: Path | None = None) -> Path:
        target = path or default_budget_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"monthlyTokens": self.monthly_tokens}, indent=2) + "\n",
            encoding="utf-8",
        )
        return target

    def as_contract(self, month_used: int) -> dict | None:
        """The `balance` the Omarchy panel already renders, or nothing at all.

        Carries the real remaining, not null: the panel's own meter reads
        `remaining` and would draw an empty bar for a budget that is half
        spent.
        """
        if self.monthly_tokens is None:
            return None
        return {
            "funded": self.monthly_tokens,
            "remaining": self.monthly_tokens - month_used,
        }

    def state(self, month_used: int) -> dict:
        """How much of the budget is gone, and whether that is worth a colour.

        ``remaining`` is allowed to go negative: a budget that is 20% past is
        information, and clamping it to zero would hide exactly the case the
        user wants to notice.
        """
        if self.monthly_tokens is None:
            return {
                "funded": None, "used": month_used, "remaining": None,
                "percent": None, "status": "unset",
            }
        funded = self.monthly_tokens
        remaining = funded - month_used
        ratio = month_used / funded
        return {
            "funded": funded,
            "used": month_used,
            "remaining": remaining,
            "percent": round(ratio * 100, 1),
            "status": "over" if ratio >= 1 else "warn" if ratio >= WARN_AT else "ok",
        }


def month_start_ms(now: datetime | None = None) -> int:
    """Midnight on the 1st, local, in epoch milliseconds.

    Local because "what did I spend this month" is a question about the
    calendar on the wall, not about UTC.
    """
    moment = now or datetime.now(UTC).astimezone()
    return int(moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
