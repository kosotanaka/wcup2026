"""
StatsBomb Open Data から国際大会の戦術データを取得し、
data/tactics/{CODE}.json にチームプロファイルを生成する。

対象大会:
  - FIFA World Cup 2022  (comp=43, season=106)
  - UEFA Euro 2024       (comp=55, season=282)
  - Copa America 2024    (comp=223, season=282)
  - AFCON 2023           (comp=1267, season=107)

出力フォーマット (data/tactics/{CODE}.json):
{
  "name": "Japan",
  "code": "JPN",
  "matches_analyzed": 5,
  "formations": {"4-2-3-1": 3, "4-3-3": 2},
  "primary_formation": "4-2-3-1",
  "avg_starting_xi": [...],          # 最頻出先発メンバー
  "common_substitutions": [...],     # よく交代で入る選手
  "matches": [...]                   # 個別試合データ
}
"""

import json
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# 対象大会 (comp_id, season_id, label)
COMPETITIONS = [
    (43,   106, "FIFA World Cup 2022"),
    (55,   282, "UEFA Euro 2024"),
    (223,  282, "Copa America 2024"),
    (1267, 107, "AFCON 2023"),
]

# StatsBomb国名 → WC2026コード
TEAM_CODE_MAP = {
    "Japan": "JPN", "Germany": "GER", "Spain": "ESP", "France": "FRA",
    "Brazil": "BRA", "Argentina": "ARG", "England": "ENG", "Portugal": "POR",
    "Netherlands": "NED", "Belgium": "BEL", "Croatia": "CRO", "Uruguay": "URU",
    "Morocco": "MAR", "Senegal": "SEN", "Australia": "AUS", "South Korea": "KOR",
    "Mexico": "MEX", "United States": "USA", "Canada": "CAN", "Ecuador": "ECU",
    "Switzerland": "SUI", "Denmark": "DEN", "Tunisia": "TUN", "Ghana": "GHA",
    "Cameroon": "CMR", "Qatar": "QAT", "Saudi Arabia": "KSA", "Iran": "IRN",
    "Poland": "POL", "Serbia": "SRB", "Wales": "WAL", "Costa Rica": "CRC",
    "Sweden": "SWE", "Norway": "NOR", "Austria": "AUT", "Turkey": "TUR",
    "Colombia": "COL", "Chile": "CHI", "Peru": "PER", "Bolivia": "BOL",
    "Venezuela": "VEN", "Paraguay": "PAR", "Panama": "PAN",
    "Egypt": "EGY", "Nigeria": "NGA", "Ivory Coast": "CIV",
    "Algeria": "ALG", "Congo DR": "COD", "Cape Verde": "CPV",
    "South Africa": "RSA", "Zambia": "ZAM", "Mozambique": "MOZ",
    "New Zealand": "NZL", "Jordan": "JOR", "Iraq": "IRQ",
    "Uzbekistan": "UZB", "Bosnia and Herzegovina": "BIH",
    "Czech Republic": "CZE", "Scotland": "SCO", "Haiti": "HAI",
    "Curaçao": "CUW", "Curacao": "CUW",
}

# WC2026出場チームコード
WC2026_TEAMS = set([
    "MEX","RSA","KOR","CZE","CAN","BIH","QAT","SUI","BRA","MAR","HAI","SCO",
    "USA","PAR","AUS","TUR","GER","CIV","ECU","CUW","NED","JPN","SWE","TUN",
    "BEL","EGY","IRN","NZL","ESP","URU","KSA","CPV","FRA","SEN","IRQ","NOR",
    "ARG","AUT","ALG","JOR","POR","COL","COD","UZB","ENG","CRO","GHA","PAN",
])

def fetch_json(url: str, retries: int = 3) -> dict | list | None:
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if i < retries - 1:
                time.sleep(2 ** i)
            else:
                print(f"    FAILED: {url} — {e}")
                return None

def parse_formation(tactics_event: dict) -> str | None:
    """StatsBombイベントのtacticsからフォーメーション文字列を返す"""
    try:
        fmt = tactics_event["tactics"]["formation"]
        s = str(fmt)
        # 例: 4231 → "4-2-3-1"
        if len(s) == 3:
            return f"{s[0]}-{s[1]}-{s[2]}"
        if len(s) == 4:
            return f"{s[0]}-{s[1]}-{s[2]}-{s[3]}"
        if len(s) == 5:
            return f"{s[0]}-{s[1]}-{s[2]}-{s[3]}-{s[4]}"
        return s
    except (KeyError, TypeError):
        return None

def get_lineup_from_tactics(tactics_event: dict) -> list[str]:
    try:
        return [p["player"]["name"] for p in tactics_event["tactics"]["lineup"]]
    except (KeyError, TypeError):
        return []

def process_match_events(match_id: int, team_name: str) -> dict:
    """1試合のイベントデータを解析してフォーメーション・先発・交代を返す"""
    events = fetch_json(f"{BASE}/events/{match_id}.json")
    if not events:
        return {}

    formations = []
    lineups = []
    subs_in = []

    for ev in events:
        if ev.get("team", {}).get("name") != team_name:
            continue
        etype = ev.get("type", {}).get("name", "")
        if etype == "Starting XI":
            fmt = parse_formation(ev)
            lineup = get_lineup_from_tactics(ev)
            if fmt:
                formations.append(fmt)
            if lineup:
                lineups = lineup
        elif etype == "Tactical Shift":
            fmt = parse_formation(ev)
            if fmt:
                formations.append(fmt)
        elif etype == "Substitution":
            replacement = ev.get("substitution", {}).get("replacement", {}).get("name")
            if replacement:
                subs_in.append(replacement)

    return {
        "formations": formations,
        "starting_xi": lineups,
        "subs_in": subs_in,
    }

def main():
    out_dir = Path("data/tactics")
    out_dir.mkdir(parents=True, exist_ok=True)

    # チームごとの集計データ
    team_data: dict[str, dict] = defaultdict(lambda: {
        "matches": [],
        "all_formations": [],
        "all_starters": [],
        "all_subs_in": [],
    })

    for comp_id, season_id, label in COMPETITIONS:
        print(f"\n{'='*50}")
        print(f"Fetching: {label}")
        matches = fetch_json(f"{BASE}/matches/{comp_id}/{season_id}.json")
        if not matches:
            continue
        print(f"  {len(matches)} matches found")

        for m in matches:
            home = m["home_team"]["home_team_name"]
            away = m["away_team"]["away_team_name"]
            match_id = m["match_id"]

            for team_name in [home, away]:
                code = TEAM_CODE_MAP.get(team_name)
                if not code or code not in WC2026_TEAMS:
                    continue

                print(f"  [{code}] {team_name} vs {'away' if team_name==home else 'home'} (match {match_id})")
                result = process_match_events(match_id, team_name)
                time.sleep(0.3)  # rate limit

                opponent = away if team_name == home else home
                score_h = m["home_score"]
                score_a = m["away_score"]
                score_str = f"{score_h}-{score_a}" if team_name == home else f"{score_a}-{score_h}"

                match_record = {
                    "competition": label,
                    "match_id": match_id,
                    "opponent": opponent,
                    "score": score_str,
                    "formation": result.get("formations", [None])[0],
                    "starting_xi": result.get("starting_xi", []),
                    "subs_in": result.get("subs_in", []),
                }
                td = team_data[code]
                td["matches"].append(match_record)
                td["all_formations"].extend(result.get("formations", []))
                td["all_starters"].extend(result.get("starting_xi", []))
                td["all_subs_in"].extend(result.get("subs_in", []))

    print("\n\nBuilding team profiles...")

    # チームJSONをロードして名前を取得
    players_dir = Path("data/players")
    team_names = {}
    for code in WC2026_TEAMS:
        jp = players_dir / f"{code}.json"
        if jp.exists():
            with open(jp) as f:
                team_names[code] = json.load(f).get("name", code)

    for code, td in team_data.items():
        if not td["matches"]:
            continue

        formations_counter = Counter(td["all_formations"])
        primary = formations_counter.most_common(1)[0][0] if formations_counter else None

        # 先発出場頻度上位11名
        starters_counter = Counter(td["all_starters"])
        top_starters = [name for name, _ in starters_counter.most_common(15)]

        # 途中出場頻度上位5名
        subs_counter = Counter(td["all_subs_in"])
        top_subs = [name for name, _ in subs_counter.most_common(8)]

        profile = {
            "name": team_names.get(code, code),
            "code": code,
            "matches_analyzed": len(td["matches"]),
            "formations": dict(formations_counter),
            "primary_formation": primary,
            "top_starters": top_starters,
            "top_subs": top_subs,
            "matches": td["matches"],
        }

        out_path = out_dir / f"{code}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        print(f"  {code}: {len(td['matches'])} matches, primary={primary}")

    print("\nDone.")

if __name__ == "__main__":
    main()
