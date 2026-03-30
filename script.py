import os
import pandas as pd
import json

START_ELO = 1000
K = 32

CSV_FOLDER = "data"
JSON_FOLDER = "jsons"

players_elo = {}
players_stats = {}

match_seen = {}
win_seen = {}

# 🔥 RANK SİSTEMİ
def get_rank(elo):
    if elo < 800: return "Silver"
    elif elo < 1000: return "Gold"
    elif elo < 1200: return "Platinum"
    elif elo < 1400: return "Diamond"
    else: return "Immortal"

# 🔥 GERÇEK SKOR (OT + FIX)
def get_match_result(match_name):
    json_files = [f for f in os.listdir(JSON_FOLDER) if f.startswith(match_name)]

    max_t1 = 0
    max_t2 = 0

    for jf in json_files:
        try:
            with open(os.path.join(JSON_FOLDER, jf)) as f:
                data = json.load(f)

            t1 = int(data["team1_score"])
            t2 = int(data["team2_score"])

            if t1 > max_t1:
                max_t1 = t1
            if t2 > max_t2:
                max_t2 = t2

        except:
            continue

    if max_t1 == 0 and max_t2 == 0:
        return None

    # winner bul
    if max_t1 > max_t2:
        winner = 1
        loser_score = max_t2
    else:
        winner = 2
        loser_score = max_t1

    # normal maç fix (13)
    if max(max_t1, max_t2) < 13:
        if winner == 1:
            return 13, loser_score
        else:
            return loser_score, 13

    # overtime fix
    if abs(max_t1 - max_t2) < 2:
        if winner == 1:
            return max_t2 + 2, max_t2
        else:
            return max_t1, max_t1 + 2

    return max_t1, max_t2


# maçları dön
for file in os.listdir(CSV_FOLDER):
    if not file.endswith(".csv"):
        continue

    match_name = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(CSV_FOLDER, file))

    for name in df["name"].unique():
        if name not in players_elo:
            players_elo[name] = START_ELO
            players_stats[name] = {
                "kills":0,
                "deaths":0,
                "assists":0,
                "damage":0,
                "hs":0,
                "matches":0,
                "wins":0
            }

    result = get_match_result(match_name)
    if not result:
        print(f"{match_name} skor yok ❌")
        continue

    t1_score, t2_score = result
    result1, result2 = (1,0) if t1_score > t2_score else (0,1)

    print(f"{match_name} → {t1_score}-{t2_score}")

    teams = list(df.groupby("team"))
    if len(teams) < 2:
        continue

    team1 = teams[0][1]
    team2 = teams[1][1]

    t1_players = team1["name"].tolist()
    t2_players = team2["name"].tolist()

    mvp = df.loc[df["kills"].idxmax()]["name"]

    # match sayısı
    for name in df["name"].unique():
        if name not in match_seen:
            match_seen[name] = set()

        if match_name not in match_seen[name]:
            players_stats[name]["matches"] += 1
            match_seen[name].add(match_name)

    # oyuncuları işle
    for _, row in df.iterrows():
        name = row["name"]

        kills = row["kills"]
        deaths = row["deaths"]
        damage = row["damage"]
        hs = row["head_shot_kills"]

        kd = kills/deaths if deaths>0 else kills

        bonus = (kd-1)*5
        hs_bonus = (hs/kills*10) if kills>0 else 0
        mvp_bonus = 10 if name == mvp else 0

        if name in t1_players:
            change = K*(result1-0.5)

            if result1 == 1:
                if name not in win_seen:
                    win_seen[name] = set()

                if match_name not in win_seen[name]:
                    players_stats[name]["wins"] += 1
                    win_seen[name].add(match_name)

        else:
            change = K*(result2-0.5)

            if result2 == 1:
                if name not in win_seen:
                    win_seen[name] = set()

                if match_name not in win_seen[name]:
                    players_stats[name]["wins"] += 1
                    win_seen[name].add(match_name)

        players_elo[name] += change + bonus + hs_bonus + mvp_bonus

        players_stats[name]["kills"] += kills
        players_stats[name]["deaths"] += deaths
        players_stats[name]["assists"] += row["assists"]
        players_stats[name]["damage"] += damage
        players_stats[name]["hs"] += hs


# JSON output
players = []

for name in players_elo:
    s = players_stats[name]

    kd = s["kills"]/s["deaths"] if s["deaths"]>0 else s["kills"]
    adr = s["damage"]/s["matches"]
    hs_percent = (s["hs"]/s["kills"]*100) if s["kills"]>0 else 0
    winrate = (s["wins"]/s["matches"]*100) if s["matches"]>0 else 0

    players.append({
        "name": name,
        "elo": int(players_elo[name]),
        "rank": get_rank(players_elo[name]),
        "kd": round(kd,2),
        "adr": round(adr,1),
        "hs_percent": round(hs_percent,1),
        "matches": s["matches"],
        "wins": s["wins"],
        "winrate": round(winrate,1),
        "rounds": int(s["matches"] * 24)
    })

players = sorted(players, key=lambda x: x["elo"], reverse=True)

with open("players.json","w") as f:
    json.dump(players,f,indent=4)

print("🔥 TAM ÇALIŞAN SİSTEM")