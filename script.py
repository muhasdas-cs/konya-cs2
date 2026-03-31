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

matches_list = []

def get_rank(elo):
    if elo < 800:
        return "Silver"
    elif elo < 1000:
        return "Gold"
    elif elo < 1200:
        return "Platinum"
    elif elo < 1400:
        return "Diamond"
    else:
        return "Immortal"


# 💣 EN KRİTİK YER (FIX BURADA)
def get_match_result(match_name):

    json_files = sorted([
        f for f in os.listdir(JSON_FOLDER)
        if f.startswith(match_name)
    ])

    if not json_files:
        return 0, 0

    last_file = json_files[-1]

    try:
        with open(os.path.join(JSON_FOLDER, last_file), encoding="utf-8") as f:
            data = json.load(f)

        team1_data = data.get("PlayersOnTeam1", {})
        team2_data = data.get("PlayersOnTeam2", {})

        team1_score = 0
        team2_score = 0

        # team1'den ilk oyuncuyu al
        for p in team1_data.values():
            team1_score = int(p.get("roundsWon", 0))
            break

        # team2'den ilk oyuncuyu al
        for p in team2_data.values():
            team2_score = int(p.get("roundsWon", 0))
            break

        return team1_score, team2_score

    except:
        return 0, 0


for file in os.listdir(CSV_FOLDER):
    if not file.endswith(".csv"):
        continue

    match_name = file.replace(".csv", "")
    df = pd.read_csv(os.path.join(CSV_FOLDER, file))

    # oyuncuları initialize et
    for name in df["name"].unique():
        if name not in players_elo:
            players_elo[name] = START_ELO
            players_stats[name] = {
                "kills": 0,
                "deaths": 0,
                "assists": 0,
                "damage": 0,
                "hs": 0,
                "matches": 0,
                "wins": 0
            }

    # 🔥 GERÇEK SKOR
    t1, t2 = get_match_result(match_name)

    teams = df["team"].unique()
    if len(teams) < 2:
        continue

    teamA = teams[0]
    teamB = teams[1]

    team_map = {teamA: 1, teamB: 2}

    team1_players = list(df[df["team"] == teamA]["name"].unique())
    team2_players = list(df[df["team"] == teamB]["name"].unique())

    winner = 1 if t1 > t2 else 2

    matches_list.append({
        "match": match_name,
        "score": f"{t1}-{t2}",
        "winner": winner,
        "team1": team1_players,
        "team2": team2_players
    })

    # MVP
    mvp = df.loc[df["kills"].idxmax()]["name"]

    # maç sayısı
    for name in df["name"].unique():
        if name not in match_seen:
            match_seen[name] = set()

        if match_name not in match_seen[name]:
            players_stats[name]["matches"] += 1
            match_seen[name].add(match_name)

    # oyuncu stat + elo
    for _, row in df.iterrows():
        name = row["name"]
        player_team = row["team"]

        kills = row["kills"]
        deaths = row["deaths"]
        damage = row["damage"]
        hs = row["head_shot_kills"]

        kd = kills / deaths if deaths > 0 else kills

        bonus = (kd - 1) * 5
        hs_bonus = (hs / kills * 10) if kills > 0 else 0
        mvp_bonus = 10 if name == mvp else 0

        if team_map[player_team] == winner:
            change = K * 0.5

            if name not in win_seen:
                win_seen[name] = set()

            if match_name not in win_seen[name]:
                players_stats[name]["wins"] += 1
                win_seen[name].add(match_name)
        else:
            change = -K * 0.5

        players_elo[name] += change + bonus + hs_bonus + mvp_bonus

        players_stats[name]["kills"] += kills
        players_stats[name]["deaths"] += deaths
        players_stats[name]["assists"] += row["assists"]
        players_stats[name]["damage"] += damage
        players_stats[name]["hs"] += hs


players = []

for name in players_elo:
    s = players_stats[name]

    kd = s["kills"] / s["deaths"] if s["deaths"] > 0 else s["kills"]
    adr = s["damage"] / s["matches"]
    hs_percent = (s["hs"] / s["kills"] * 100) if s["kills"] > 0 else 0
    winrate = (s["wins"] / s["matches"] * 100) if s["matches"] > 0 else 0

    players.append({
        "name": name,
        "elo": int(players_elo[name]),
        "rank": get_rank(players_elo[name]),
        "kd": round(kd, 2),
        "adr": round(adr, 1),
        "hs_percent": round(hs_percent, 1),
        "matches": s["matches"],
        "wins": s["wins"],
        "winrate": round(winrate, 1),
        "rounds": int(s["matches"] * 24)
    })

players = sorted(players, key=lambda x: x["elo"], reverse=True)

with open("players.json", "w", encoding="utf-8") as f:
    json.dump(players, f, indent=4, ensure_ascii=False)

with open("matches.json", "w", encoding="utf-8") as f:
    json.dump(matches_list, f, indent=4, ensure_ascii=False)

print("🔥 SYSTEM FIXED - REAL SCORES WORKING")