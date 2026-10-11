#!/usr/bin/env python3
"""
Sends an ntfy push notification when the S&P 500 closes below its
50-, 100-, or 200-day simple moving average.

Stateless: a "cross" is detected from the data itself (today's close is below
the average, yesterday's close was not), so it runs fine on GitHub Actions
or any scheduler with no saved files.

Config via environment variable:
    NTFY_TOPIC   long, random topic name (anyone who knows it can read it)
Optional:
    NTFY_SERVER  defaults to https://ntfy.sh

Setup: pip install yfinance requests
"""

import os
import sys

import requests
import yfinance as yf

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
TICKER = "^GSPC"
WINDOWS = [50, 100, 200]


def notify(title: str, message: str) -> None:
    requests.post(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": "high", "Tags": "chart_with_downwards_trend"},
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
    crossed = []

    for w in WINDOWS:
        sma = closes.rolling(w).mean()
        sma_now, sma_prev = float(sma.iloc[-1]), float(sma.iloc[-2])
        below_now = last_close < sma_now
        below_prev = prev_close < sma_prev
        print(f"{last_date}  close {last_close:,.2f}  {w}d SMA {sma_now:,.2f}  below={below_now}")
        if below_now and not below_prev:
            crossed.append(f"{w}-day SMA ({sma_now:,.2f})")

    if crossed:
        notify(
            "S&P 500 closed below key average",
            f"Close {last_close:,.2f} on {last_date} is below the " + ", ".join(crossed) + ".",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
