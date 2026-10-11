#!/usr/bin/env python3
"""
Daily S&P 500 moving-average status via ntfy.

Sends one notification per trading day showing where the S&P 500 closed
relative to its 50-, 100-, and 200-day simple moving averages. If the index
newly crossed below an average that day, the notification is high priority.

Stateless, so it runs fine on GitHub Actions or any scheduler.

Config via environment variables:
    NTFY_TOPIC   long, random topic name (required)
    NTFY_SERVER  defaults to https://ntfy.sh
    FORCE        set to 1 to send even if today isn't a trading day (for testing)

Setup: pip install yfinance requests
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
FORCE = os.environ.get("FORCE") == "1"
TICKER = "^GSPC"
WINDOWS = [50, 100, 200]


def notify(title: str, message: str, priority: str, tags: str) -> None:
    requests.post(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Tags": tags},
        timeout=15,
    ).raise_for_status()


def main() -> int:
    if not NTFY_TOPIC:
        print("NTFY_TOPIC is not set.", file=sys.stderr)
        return 1

    closes = yf.Ticker(TICKER).history(period="2y", interval="1d")["Close"].dropna()
    if len(closes) < max(WINDOWS) + 2:
        print("Not enough data returned; skipping.", file=sys.stderr)
        return 1

    last_close, prev_close = float(closes.iloc[-1]), float(closes.iloc[-2])
    last_date = closes.index[-1].date()

    # Skip market holidays (no new close today) unless forced
    today_et = datetime.now(ZoneInfo("America/New_York")).date()
    if last_date != today_et and not FORCE:
        print(f"No new close today (latest is {last_date}); skipping.")
        return 0

    lines, newly_crossed, below_count = [], [], 0
    for w in WINDOWS:
        sma = closes.rolling(w).mean()
        sma_now, sma_prev = float(sma.iloc[-1]), float(sma.iloc[-2])
        pct = (last_close / sma_now - 1) * 100
        below = last_close < sma_now
        below_count += below
        if below and not (prev_close < sma_prev):
            newly_crossed.append(f"{w}d")
        icon = "🔴 below" if below else "🟢 above"
        lines.append(f"{w}d  {sma_now:,.0f}  {icon} ({pct:+.1f}%)")

    message = f"Close {last_close:,.2f} ({last_date})\n" + "\n".join(lines)
    if newly_crossed:
        title = f"S&P 500 crossed below {', '.join(newly_crossed)}"
        priority, tags = "high", "rotating_light"
    else:
        title = f"S&P 500 daily: {len(WINDOWS) - below_count}/{len(WINDOWS)} averages above"
        priority, tags = "default", "chart_with_upwards_trend" if below_count == 0 else "warning"

    print(title)
    print(message)
    notify(title, message, priority, tags)
    return 0


if __name__ == "__main__":
    sys.exit(main())
