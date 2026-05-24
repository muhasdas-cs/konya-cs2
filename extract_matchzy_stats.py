import os
import re
import json
from collections import defaultdict

JSON_FOLDER = "jsons"

START_ELO = 1000
WIN_ELO = 25
LOSS_ELO = -25

def to_int(value, default=0):
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default

def to_float(value, default=0.0):
    try:
        return float(str(value).strip())
    except Exception:
        return default

def get_rank(elo):
    if elo < 800:
        return "Silver"
    if elo < 1000:
        return "Gold"
    if elo < 1200:
        return "Platinum"
    if elo < 1400:
        return "Diamond"
    return "Immortal"

def split_match_round(filename):
    """
    matchzy_2_0_round01.json -> ("matchzy_2_0", 1)
    match1_round02.json       -> ("match1", 2)
    """
    m = re.match(r"(.+)_round(\d+)\.json$", filename, re.IGNORECASE)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))

def tokenize_vdf(text):
    """
    Valve backup text looks like:
    "SaveFile"
    {
        "PlayersOnTeam1"
        {
            "123"
            {
                "name" "MuHasdas"
            }
        }
    }
    """
    return re.findall(r'"([^"]*)"|([{}])', text)

def parse_vdf(text):
    tokens_raw = tokenize_vdf(text)
    tokens = []
    for string_token, brace in tokens_raw:
        tokens.append(brace if brace else string_token)

    index = 0

    def parse_object():
        nonlocal index
        obj = {}
        while index < len(tokens):
            token = tokens[index]

            if token == "}":
                index += 1
                return obj

            key = token
            index += 1

            if index >= len(tokens):
                obj[key] = ""
                return obj

            nxt = tokens[index]

            if nxt == "{":
                index += 1
                obj[key] = parse_object()
            else:
                obj[key] = nxt
                index += 1

        return obj

    root = {}
    while index < len(tokens):
        key = tokens[index]
        index += 1

        if index < len(tokens) and tokens[index] == "{":
            index += 1
            root[key] = parse_object()
        elif index < len(tokens):
            root[key] = tokens[index]
            index += 1

    return root

def get_savefile(data):
    """
    MatchZy usually stores detailed player stats inside data["valve_backup"].
    Parse it and return SaveFile object.
    """
    backup = data.get("valve_backup", "")
    if not backup:
        return {}

    parsed = parse_vdf(backup)
    return parsed.get("SaveFile", parsed)

def iter_team_players(team_block):
    """
    team_block can be a dict of steamid -> player dict.
    Some formats may already be a list. This handles both.
    """
    if isinstance(team_block, dict):
        for steam_id, player in team_block.items():
            if isinstance(player, dict):
                yield str(steam_id), player
    elif isinstance(team_block, list):
        for i, player in enumerate(team_block):
            if isinstance(player, dict):
                yield str(player.get("steamid", i)), player

def player_total(player, key):
    totals = player.get("MatchStats", {}).get("Totals", {})
    return to_int(totals.get(key, player.get(key, 0)))

def player_name(player, steam_id):
    return (
        player.get("name")
        or player.get("playerName")
        or player.get("username")
        or f"steam_{steam_id}"
    )

def make_player_row(steam_id, player, team_no):
    kills = player_total(player, "Kills")
    deaths = player_total(player, "Deaths")
    assists = player_total(player, "Assists")
    damage = player_total(player, "Damage")
    hs = player_total(player, "HeadshotKills")

    # Some backups use HeadShotKills in round section but Totals usually HeadshotKills.
    if hs == 0:
        hs = player_total(player, "HeadShotKills")

    utility_damage = player_total(player, "UtilityDamage")
    utility_count = player_total(player, "UtilityCount")
    utility_successes = player_total(player, "UtilitySuccesses")
    flash_count = player_total(player, "FlashCount")
    flash_successes = player_total(player, "FlashSuccesses")
    enemies_flashed = player_total(player, "EnemiesFlashed")
    entry_count = player_total(player, "EntryCount")
    entry_wins = player_total(player, "EntryWins")
    clutch_1v1_count = player_total(player, "1v1Count")
    clutch_1v1_wins = player_total(player, "1v1Wins")
    clutch_1v2_count = player_total(player, "1v2Count")
    clutch_1v2_wins = player_total(player, "1v2Wins")

    return {
        "steam_id": steam_id,
        "name": player_name(player, steam_id),
        "team": team_no,
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "damage": damage,
        "headshot_kills": hs,
        "utility_damage": utility_damage,
        "utility_count": utility_count,
        "utility_successes": utility_successes,
        "flash_count": flash_count,
        "flash_successes": flash_successes,
        "enemies_flashed": enemies_flashed,
        "entry_count": entry_count,
        "entry_wins": entry_wins,
        "clutch_1v1_count": clutch_1v1_count,
        "clutch_1v1_wins": clutch_1v1_wins,
        "clutch_1v2_count": clutch_1v2_count,
        "clutch_1v2_wins": clutch_1v2_wins,
        "kd": round(kills / deaths, 2) if deaths else float(kills),
        "hs_percent": round((hs / kills * 100), 1) if kills else 0.0
    }

def read_match_from_final_json(match_name, filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    save = get_savefile(data)

    team1_score = to_int(data.get("team1_score", save.get("team1_score", 0)))
    team2_score = to_int(data.get("team2_score", save.get("team2_score", 0)))

    team1_name = data.get("team1_name") or save.get("team1") or "Team 1"
    team2_name = data.get("team2_name") or save.get("team2") or "Team 2"

    team1_side = data.get("team1_side", "")
    team2_side = data.get("team2_side", "")

    team1_block = save.get("PlayersOnTeam1", data.get("PlayersOnTeam1", {}))
    team2_block = save.get("PlayersOnTeam2", data.get("PlayersOnTeam2", {}))

    team1_players = [make_player_row(sid, p, 1) for sid, p in iter_team_players(team1_block)]
    team2_players = [make_player_row(sid, p, 2) for sid, p in iter_team_players(team2_block)]

    winner = 0
    if team1_score > team2_score:
        winner = 1
    elif team2_score > team1_score:
        winner = 2

    rounds = team1_score + team2_score

    return {
        "match": match_name,
        "matchid": data.get("matchid", ""),
        "timestamp": data.get("timestamp", ""),
        "map": data.get("map_name", ""),
        "mapnumber": data.get("mapnumber", ""),
        "score": f"{team1_score}-{team2_score}",
        "team1_score": team1_score,
        "team2_score": team2_score,
        "winner": winner,
        "team1_name": team1_name,
        "team2_name": team2_name,
        "team1_side": team1_side,
        "team2_side": team2_side,
        "rounds": rounds,
        "team1": [p["name"] for p in team1_players],
        "team2": [p["name"] for p in team2_players],
        "team1_players": team1_players,
        "team2_players": team2_players
    }

def main():
    if not os.path.isdir(JSON_FOLDER):
        print(f"HATA: '{JSON_FOLDER}' klasörü bulunamadı.")
        print("script.py ile aynı klasörde jsons klasörü olmalı.")
        return

    grouped = defaultdict(list)

    for file in os.listdir(JSON_FOLDER):
        if not file.lower().endswith(".json"):
            continue

        match_name, round_no = split_match_round(file)
        if match_name is None:
            continue

        grouped[match_name].append((round_no, file))

    if not grouped:
        print("HATA: jsons klasöründe *_round00.json gibi dosya bulunamadı.")
        return

    matches = []
    skipped = []

    for match_name, items in sorted(grouped.items(), key=lambda x: x[0]):
        items.sort(key=lambda x: x[0])
        final_round, final_file = items[-1]
        final_path = os.path.join(JSON_FOLDER, final_file)

        try:
            match = read_match_from_final_json(match_name, final_path)
            match["final_round_file"] = final_file
            match["round_file_count"] = len(items)
            matches.append(match)
        except Exception as e:
            skipped.append({"match": match_name, "file": final_file, "error": str(e)})

    stats = {}

    for match in matches:
        winner = match["winner"]
        rounds = max(match["rounds"], 1)

        for p in match["team1_players"] + match["team2_players"]:
            key = p["steam_id"] if p["steam_id"] else p["name"]

            if key not in stats:
                stats[key] = {
                    "steam_id": p["steam_id"],
                    "name": p["name"],
                    "matches": 0,
                    "wins": 0,
                    "rounds": 0,
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "damage": 0,
                    "headshot_kills": 0,
                    "utility_damage": 0,
                    "utility_count": 0,
                    "utility_successes": 0,
                    "flash_count": 0,
                    "flash_successes": 0,
                    "enemies_flashed": 0,
                    "entry_count": 0,
                    "entry_wins": 0,
                    "clutch_1v1_count": 0,
                    "clutch_1v1_wins": 0,
                    "clutch_1v2_count": 0,
                    "clutch_1v2_wins": 0,
                    "match_history": []
                }

            s = stats[key]
            s["name"] = p["name"]
            s["matches"] += 1
            s["rounds"] += rounds

            if winner != 0 and p["team"] == winner:
                s["wins"] += 1

            for field in [
                "kills", "deaths", "assists", "damage", "headshot_kills",
                "utility_damage", "utility_count", "utility_successes",
                "flash_count", "flash_successes", "enemies_flashed",
                "entry_count", "entry_wins",
                "clutch_1v1_count", "clutch_1v1_wins",
                "clutch_1v2_count", "clutch_1v2_wins"
            ]:
                s[field] += p.get(field, 0)

            result = "DRAW"
            if winner != 0:
                result = "WIN" if p["team"] == winner else "LOSE"

            s["match_history"].append({
                "match": match["match"],
                "score": match["score"],
                "team": p["team"],
                "result": result,
                "kills": p["kills"],
                "deaths": p["deaths"],
                "assists": p["assists"],
                "damage": p["damage"],
                "kd": p["kd"]
            })

    players = []
    players_extra = []

    for s in stats.values():
        kills = s["kills"]
        deaths = s["deaths"]
        rounds = max(s["rounds"], 1)
        matches_played = max(s["matches"], 1)
        wins = s["wins"]

        kd = round(kills / deaths, 2) if deaths else float(kills)
        adr = round(s["damage"] / rounds, 1)
        hs_percent = round((s["headshot_kills"] / kills * 100), 1) if kills else 0.0
        winrate = round((wins / matches_played * 100), 1)
        flash_success_rate = round((s["flash_successes"] / s["flash_count"] * 100), 1) if s["flash_count"] else 0.0
        entry_success_rate = round((s["entry_wins"] / s["entry_count"] * 100), 1) if s["entry_count"] else 0.0

        elo = START_ELO + wins * WIN_ELO + (matches_played - wins) * LOSS_ELO
        elo += int((kd - 1) * 20)
        elo += int((adr - 75) * 0.2)

        players.append({
            "name": s["name"],
            "steam_id": s["steam_id"],
            "elo": int(elo),
            "rank": get_rank(elo),
            "winrate": winrate,
            "matches": s["matches"],
            "wins": wins,
            "kd": kd,
            "adr": adr,
            "hs_percent": hs_percent,
            "rounds": s["rounds"]
        })

        players_extra.append({
            "name": s["name"],
            "steam_id": s["steam_id"],
            "kills": kills,
            "deaths": deaths,
            "assists": s["assists"],
            "damage": s["damage"],
            "kd": kd,
            "adr": adr,
            "hs_percent": hs_percent,
            "utility_damage": s["utility_damage"],
            "utility_count": s["utility_count"],
            "utility_successes": s["utility_successes"],
            "flash_count": s["flash_count"],
            "flash_success_rate": flash_success_rate,
            "enemies_flashed": s["enemies_flashed"],
            "entry_count": s["entry_count"],
            "entry_success_rate": entry_success_rate,
            "clutch_1v1": f"{s['clutch_1v1_wins']}/{s['clutch_1v1_count']}",
            "clutch_1v2": f"{s['clutch_1v2_wins']}/{s['clutch_1v2_count']}",
            "match_history": s["match_history"]
        })

    players.sort(key=lambda x: x["elo"], reverse=True)
    players_extra.sort(key=lambda x: x["name"].lower())

    # matches.json remains light for index/profile.
    matches_light = []
    for m in matches:
        matches_light.append({
            "match": m["match"],
            "matchid": m["matchid"],
            "timestamp": m["timestamp"],
            "map": m["map"],
            "score": m["score"],
            "team1_score": m["team1_score"],
            "team2_score": m["team2_score"],
            "winner": m["winner"],
            "team1_name": m["team1_name"],
            "team2_name": m["team2_name"],
            "team1": m["team1"],
            "team2": m["team2"]
        })

    with open("players.json", "w", encoding="utf-8") as f:
        json.dump(players, f, indent=4, ensure_ascii=False)

    with open("players_extra.json", "w", encoding="utf-8") as f:
        json.dump(players_extra, f, indent=4, ensure_ascii=False)

    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(matches_light, f, indent=4, ensure_ascii=False)

    with open("match_details.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=4, ensure_ascii=False)

    if skipped:
        with open("skipped_jsons.json", "w", encoding="utf-8") as f:
            json.dump(skipped, f, indent=4, ensure_ascii=False)

    print("OK")
    print(f"Maç sayısı: {len(matches)}")
    print(f"Oyuncu sayısı: {len(players)}")
    print("Oluşan dosyalar:")
    print("- players.json")
    print("- players_extra.json")
    print("- matches.json")
    print("- match_details.json")
    if skipped:
        print(f"Uyarı: {len(skipped)} maç atlandı. skipped_jsons.json dosyasına bak.")

if __name__ == "__main__":
    main()
