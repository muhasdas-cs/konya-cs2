import os
import pandas as pd
import json

players = {}
matches = []

for file in os.listdir("data"):

    if not file.endswith(".csv"):
        continue

    if "match_data" in file:
        continue

    df = pd.read_csv("data/" + file)
    match = file.replace(".csv", "")

    teams = df["team"].unique()

    if len(teams) < 2:
        continue

    team1 = df[df["team"] == teams[0]]
    team2 = df[df["team"] == teams[1]]

    score1 = len(team1)
    score2 = len(team2)

    winner = 1 if score1 > score2 else 2

    matches.append({
        "match": match,
        "score": f"{score1}-{score2}",
        "winner": winner,
        "team1": list(team1["name"].unique()),
        "team2": list(team2["name"].unique())
    })

    for name in df["name"].unique():
        if name not in players:
            players[name] = {"matches": 0, "wins": 0}

        players[name]["matches"] += 1

        player_team = df[df["name"] == name]["team"].iloc[0]

        if (winner == 1 and player_team == teams[0]) or (winner == 2 and player_team == teams[1]):
            players[name]["wins"] += 1


players_out = []

for name, data in players.items():

    matches_played = data["matches"]
    wins = data["wins"]

    winrate = (wins / matches_played * 100) if matches_played > 0 else 0

    players_out.append({
        "name": name,
        "elo": 1000,
        "winrate": round(winrate, 1),
        "kd": 1,
        "adr": 0,
        "matches": matches_played,
        "wins": wins
    })

with open("players.json", "w", encoding="utf-8") as f:
    json.dump(players_out, f, indent=4, ensure_ascii=False)

with open("matches.json", "w", encoding="utf-8") as f:
    json.dump(matches, f, indent=4, ensure_ascii=False)

print("OK")