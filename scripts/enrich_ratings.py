"""
EAFC26-DataHub の players.csv を読み込み、
data/players/{CODE}.json の各選手に EAFC26 レーティングを付与する。

マッチング戦略:
  1. 国籍でフィルタ
  2. short_name / long_name と選手名を正規化して完全一致
  3. 一致しなければ fuzzy match (SequenceMatcher >= 0.75)
  4. それでも一致しなければ unmatched ログに記録

出力: data/players/{CODE}.json に "eafc26" キーを追記
  "eafc26": {
    "overall": 85, "potential": 88,
    "pace": 80, "shooting": 78, "passing": 82,
    "dribbling": 84, "defending": 35, "physicality": 72,
    "player_id": 192985
  }
"""

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

EAFC_CSV = Path("/home/user/EAFC26-DataHub/data/players.csv")
PLAYERS_DIR = Path("data/players")

# WC2026チームコード → EAFC26 nationality_name マッピング
NATIONALITY_MAP = {
    "MEX": "Mexico",
    "RSA": "South Africa",
    "KOR": "Korea Republic",
    "CZE": "Czechia",
    "CAN": "Canada",
    "BIH": "Bosnia and Herzegovina",
    "QAT": "Qatar",
    "SUI": "Switzerland",
    "BRA": "Brazil",
    "MAR": "Morocco",
    "HAI": "Haiti",
    "SCO": "Scotland",
    "USA": "United States",
    "PAR": "Paraguay",
    "AUS": "Australia",
    "TUR": "Türkiye",
    "GER": "Germany",
    "CIV": "Côte d'Ivoire",
    "ECU": "Ecuador",
    "CUW": "Curacao",
    "NED": "Netherlands",
    "JPN": "Japan",
    "SWE": "Sweden",
    "TUN": "Tunisia",
    "BEL": "Belgium",
    "EGY": "Egypt",
    "IRN": "Iran",
    "NZL": "New Zealand",
    "ESP": "Spain",
    "URU": "Uruguay",
    "KSA": "Saudi Arabia",
    "CPV": "Cabo Verde",
    "FRA": "France",
    "SEN": "Senegal",
    "IRQ": "Iraq",
    "NOR": "Norway",
    "ARG": "Argentina",
    "AUT": "Austria",
    "ALG": "Algeria",
    "JOR": "Jordan",
    "POR": "Portugal",
    "COL": "Colombia",
    "COD": "Congo DR",
    "UZB": "Uzbekistan",
    "ENG": "England",
    "CRO": "Croatia",
    "GHA": "Ghana",
    "PAN": "Panama",
}

RATING_COLS = [
    "overall", "potential", "pace", "shooting",
    "passing", "dribbling", "defending", "physic",
]

def normalize(name: str) -> str:
    """小文字・アクセント除去・記号除去で正規化"""
    name = name.lower().strip()
    # アクセント文字を基本ラテン文字に近似
    replacements = {
        "á":"a","à":"a","â":"a","ä":"a","ã":"a",
        "é":"e","è":"e","ê":"e","ë":"e",
        "í":"i","ì":"i","î":"i","ï":"i",
        "ó":"o","ò":"o","ô":"o","ö":"o","õ":"o",
        "ú":"u","ù":"u","û":"u","ü":"u",
        "ñ":"n","ç":"c","ß":"ss",
        "ø":"o","å":"a","æ":"ae",
    }
    for src, dst in replacements.items():
        name = name.replace(src, dst)
    name = re.sub(r"[^a-z0-9 ]", "", name)
    return name

def fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def find_player(row_name: str, candidates: pd.DataFrame) -> pd.Series | None:
    norm_target = normalize(row_name)
    words = norm_target.split()

    # 1. 完全一致
    for col in ["short_name_norm", "long_name_norm"]:
        exact = candidates[candidates[col] == norm_target]
        if len(exact) == 1:
            return exact.iloc[0]
        if len(exact) > 1:
            return exact.sort_values("overall", ascending=False).iloc[0]

    # 2. long_name に全単語が含まれる（例: "Lionel Messi" in "Lionel Andrés Messi Cuccitini"）
    def all_words_in(target_words, long_norm):
        return all(w in long_norm for w in target_words)

    if len(words) >= 2:
        subset = candidates[candidates["long_name_norm"].apply(
            lambda ln: all_words_in(words, ln)
        )]
        if len(subset) == 1:
            return subset.iloc[0]
        if len(subset) > 1:
            return subset.sort_values("overall", ascending=False).iloc[0]

    # 3. fuzzy fallback
    best_score = 0.0
    best_row = None
    for col in ["short_name_norm", "long_name_norm"]:
        for _, r in candidates.iterrows():
            s = fuzzy_score(norm_target, r[col])
            if s > best_score:
                best_score = s
                best_row = r
    if best_score >= 0.75:
        return best_row
    return None

def main():
    print(f"Loading EAFC26 CSV...")
    df = pd.read_csv(EAFC_CSV, low_memory=False)
    df["short_name_norm"] = df["short_name"].fillna("").apply(normalize)
    df["long_name_norm"] = df["long_name"].fillna("").apply(normalize)

    total_matched = 0
    total_unmatched = 0
    unmatched_log = []

    for code, nation in NATIONALITY_MAP.items():
        json_path = PLAYERS_DIR / f"{code}.json"
        if not json_path.exists():
            print(f"  [SKIP] {code}: JSON not found")
            continue

        with open(json_path) as f:
            data = json.load(f)

        candidates = df[df["nationality_name"] == nation].copy()
        if candidates.empty:
            print(f"  [WARN] {code} ({nation}): no players in EAFC26 CSV")
            continue

        matched = 0
        unmatched = 0
        for player in data["players"]:
            result = find_player(player["name"], candidates)
            if result is not None:
                eafc = {
                    "overall":     int(result["overall"])   if pd.notna(result["overall"])   else None,
                    "potential":   int(result["potential"]) if pd.notna(result["potential"]) else None,
                    "pace":        int(result["pace"])       if pd.notna(result["pace"])       else None,
                    "shooting":    int(result["shooting"])   if pd.notna(result["shooting"])   else None,
                    "passing":     int(result["passing"])    if pd.notna(result["passing"])    else None,
                    "dribbling":   int(result["dribbling"])  if pd.notna(result["dribbling"])  else None,
                    "defending":   int(result["defending"])  if pd.notna(result["defending"])  else None,
                    "physicality": int(result["physic"])     if pd.notna(result["physic"])     else None,
                    "player_id":   int(result["player_id"]) if pd.notna(result["player_id"]) else None,
                }
                player["eafc26"] = eafc
                matched += 1
            else:
                unmatched += 1
                unmatched_log.append({"code": code, "nation": nation, "player": player["name"]})

        total_matched += matched
        total_unmatched += unmatched

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  {code} ({nation}): {matched} matched, {unmatched} unmatched")

    print(f"\n=== 完了 ===")
    print(f"マッチ成功: {total_matched}  未マッチ: {total_unmatched}")

    if unmatched_log:
        log_path = Path("data/unmatched_players.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(unmatched_log, f, ensure_ascii=False, indent=2)
        print(f"未マッチ選手リスト → {log_path}")

if __name__ == "__main__":
    main()
