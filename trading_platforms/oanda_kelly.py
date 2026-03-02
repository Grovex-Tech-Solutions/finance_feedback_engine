"""
OANDA Kelly Fraction Calculator

This script retrieves recent price data from OANDA for a given instrument,
calculates the Kelly fraction based on mean and variance of daily returns,
and prints the recommended position size.

Usage:
    export OANDA_API_KEY=<your-oanda-api-key>
    export OANDA_ACCOUNT_ID=<your-oanda-account-id>   # optional – if omitted, the script will attempt to fetch the default account via the OANDA API
    python oanda_kelly.py EUR_USD [--account-balance <balance>]

Optional arguments:
    --account-balance <balance>  Specify the capital to allocate (in the account's currency). If omitted, the script will query the account's current balance via the OANDA API.
"""

import argparse
import os
import sys
import json
import math
from datetime import datetime, timedelta

import requests

OANDA_API_URL = "https://api-fxtrade.oanda.com/v3"
DEFAULT_GRANULARITY = "D"  # daily candles
DEFAULT_COUNT = 90  # number of recent candles to fetch (approx. a quarter of trading days)

def get_api_key():
    api_key = os.getenv("OANDA_API_KEY")
    if not api_key:
        sys.stderr.write("Error: OANDA_API_KEY environment variable not set\n")
        sys.exit(1)
    return api_key

def get_account_id(provided_id=None):
    if provided_id:
        return provided_id
    # Attempt to fetch the default account via the API (requires API key)
    headers = {"Authorization": f"Bearer {get_api_key()}"}
    resp = requests.get(f"{OANDA_API_URL}/accounts", headers=headers)
    if resp.status_code != 200:
        sys.stderr.write(f"Error fetching accounts: {resp.status_code} {resp.text}\n")
        sys.exit(1)
    data = resp.json()
    accounts = data.get("accounts", [])
    if not accounts:
        sys.stderr.write("No accounts found for this API key. Provide OANDA_ACCOUNT_ID manually.\n")
        sys.exit(1)
    # Return the first account ID
    return accounts[0]["id"]

def fetch_candles(instrument, account_id, count=DEFAULT_COUNT, granularity=DEFAULT_GRANULARITY):
    headers = {"Authorization": f"Bearer {get_api_key()}"}
    params = {
        "price": "M",  # midpoint price
        "granularity": granularity,
        "count": count,
    }
    url = f"{OANDA_API_URL}/instruments/{instrument}/candles"
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        sys.stderr.write(f"Error fetching candles for {instrument}: {resp.status_code} {resp.text}\n")
        sys.exit(1)
    return resp.json()["candles"]

def compute_returns(candles):
    # Compute simple daily returns using close prices
    returns = []
    for i in range(1, len(candles)):
        prev_close = float(candles[i-1]["midpoint"]["c"])
        cur_close = float(candles[i]["midpoint"]["c"])
        ret = (cur_close - prev_close) / prev_close
        returns.append(ret)
    return returns

def calculate_kelly_fraction(mean_ret, var_ret):
    if var_ret == 0:
        return 0.0
    kelly = mean_ret / var_ret
    # Cap Kelly fraction between 0 and 1 (0% – 100% of capital)
    return max(0.0, min(kelly, 1.0))

def get_account_balance(account_id):
    headers = {"Authorization": f"Bearer {get_api_key()}"}
    resp = requests.get(f"{OANDA_API_URL}/accounts/{account_id}/summary", headers=headers)
    if resp.status_code != 200:
        sys.stderr.write(f"Error fetching account summary: {resp.status_code} {resp.text}\n")
        sys.exit(1)
    data = resp.json()
    # The balance is in the account's base currency (e.g., USD)
    return float(data["account"]["balance"])

def main():
    parser = argparse.ArgumentParser(description="Calculate Kelly fraction for an OANDA instrument.")
    parser.add_argument("instrument", help="Instrument symbol, e.g., EUR_USD")
    parser.add_argument("--account-balance", type=float, help="Capital amount to allocate (defaults to account balance)")
    parser.add_argument("--account-id", help="OANDA account ID (optional if you have only one account)")
    args = parser.parse_args()

    api_key = get_api_key()
    account_id = get_account_id(args.account_id)

    candles = fetch_candles(args.instrument, account_id)
    if len(candles) < 2:
        sys.stderr.write("Not enough candle data to compute returns.\n")
        sys.exit(1)

    returns = compute_returns(candles)
    mean_ret = sum(returns) / len(returns)
    var_ret = sum((r - mean_ret) ** 2 for r in returns) / len(returns)

    kelly_frac = calculate_kelly_fraction(mean_ret, var_ret)
    # If the user provided a specific capital amount, use it; otherwise fetch the account balance.
    capital = args.account_balance if args.account_balance is not None else get_account_balance(account_id)
    recommended_position = capital * kelly_frac

    # Output results
    print(f"Instrument: {args.instrument}")
    print(f"Data points used: {len(returns)} (daily returns)\n")
    print(f"Mean return (μ): {mean_ret:.6f}")
    print(f"Return variance (σ²): {var_ret:.6f}\n")
    print(f"Kelly fraction (f* = μ/σ²): {kelly_frac:.4%}")
    print(f"Capital available: {capital:,.2f} {data[\"account\"][\"currency\"]}\n")
    print(f"Recommended position size: {recommended_position:,.2f} {data[\"account\"][\"currency\"]}\n")
    print("---\nNotes:\n- Kelly fraction is capped to the range [0,1] to avoid over‑leveraging.\n- This calculation assumes simple daily returns; for higher‑frequency data adjust the granularity and count accordingly.\n- Always consider risk limits, margin requirements, and transaction costs before executing the trade.")

if __name__ == "__main__":
    main()
