"""
Rebuilds deadlock_ban_rates.csv from the public Deadlock stats API
(api.deadlock-api.com). Run with: uv run python fetch_data.py

Ban rate is estimated as:
    bans_for_hero_in_bucket / estimated_matches_in_bucket * 100

where estimated_matches_in_bucket is the sum of every hero's match
appearances in that rank bucket, divided by 12 (6v6 -> 12 hero slots
per match). This is an approximation since the API does not expose a
direct "total matches per rank bucket" figure.
"""

import csv

import requests

API = "https://api.deadlock-api.com/v1"

RANKS = {
    0: "Obscurus", 1: "Initiate", 2: "Seeker", 3: "Acolyte", 4: "Sentinel",
    5: "Mystic", 6: "Ritualist", 7: "Emissary", 8: "Oracle", 9: "Phantom",
    10: "Ascendant", 11: "Eternus",
}


def fetch(path: str, **params):
    resp = requests.get(f"{API}/{path}", params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    heroes = fetch("assets/heroes")
    hero_name = {h["id"]: h["name"] for h in heroes}

    hero_stats = fetch("analytics/hero-stats", bucket="avg_badge", match_mode="ranked")
    ban_stats = fetch("analytics/hero-ban-stats", bucket="avg_badge", match_mode="ranked")

    bucket_match_sum = {}
    for row in hero_stats:
        bucket_match_sum[row["bucket"]] = bucket_match_sum.get(row["bucket"], 0) + row["matches"]
    bucket_est_matches = {b: v / 12 for b, v in bucket_match_sum.items()}

    rows = []
    for row in ban_stats:
        hid = row["hero_id"]
        bucket = row["bucket"]
        if hid not in hero_name:
            continue
        tier, subrank = divmod(bucket, 10)
        if tier not in RANKS or subrank == 0:
            continue
        est_matches = bucket_est_matches.get(bucket)
        if not est_matches or est_matches < 50:
            continue
        rows.append({
            "hero": hero_name[hid],
            "rank_tier": tier,
            "rank_name": RANKS[tier],
            "subrank": subrank,
            "bans": row["bans"],
            "estimated_matches": round(est_matches),
            "ban_rate_pct": round(row["bans"] / est_matches * 100, 3),
        })

    with open("deadlock_ban_rates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to deadlock_ban_rates.csv")


if __name__ == "__main__":
    main()
