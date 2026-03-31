import os
import pandas as pd
import json

CSV_FOLDER = "data"

players = {}

for file in os.listdir(CSV_FOLDER):
    if not file.endswith(".csv"):
        continue

    df = pd.read_csv(os.path.join(CSV_FOLDER, file))

    for _, row in df.iterrows():
        name = row["name"]

        if name not in players:
            players[name] = {
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "damage": 0,
                "hs": 0,
                "utility_damage": 0,
                "flash_count": 0,
                "flash_success": 0,
                "entry_count": 0,
                "entry_wins": 0,
                "matches": 0
            }

        p = players[name]

        p["kills"] += row.get("kills",0)
        p["deaths"] += row.get("deaths",0)
        p["assists"] += row.get("assists",0)
        p["damage"] += row.get("damage",0)
        p["hs"] += row.get("head_shot_kills",0)

        p["utility_damage"] += row.get("utility_damage",0)
        p["flash_count"] += row.get("flash_count",0)
        p["flash_success"] += row.get("flash_successes",0)
        p["entry_count"] += row.get("entry_count",0)
        p["entry_wins"] += row.get("entry_wins",0)

        p["matches"] += 1

result = []

for name, s in players.items():

    kd = s["kills"]/s["deaths"] if s["deaths"]>0 else s["kills"]
    hs_percent = (s["hs"]/s["kills"]*100) if s["kills"]>0 else 0
    flash_success_rate = (s["flash_success"]/s["flash_count"]*100) if s["flash_count"]>0 else 0
    entry_success_rate = (s["entry_wins"]/s["entry_count"]*100) if s["entry_count"]>0 else 0

    result.append({
        "name": name,
        "kills": s["kills"],
        "assists": s["assists"],
        "kd": round(kd,2),
        "hs_percent": round(hs_percent,1),
        "utility_damage": s["utility_damage"],
        "flash_count": s["flash_count"],
        "flash_success_rate": round(flash_success_rate,1),
        "entry_count": s["entry_count"],
        "entry_success_rate": round(entry_success_rate,1)
    })

with open("players_extra.json","w",encoding="utf-8") as f:
    json.dump(result,f,indent=4,ensure_ascii=False)

print("EXTRA STATS READY")
