"""
AI予測スクリプト: 全72グループステージ試合 + ノックアウトブラケットを予測する

アルゴリズム（子供でもわかるように）:
- 各チームのEA FC 26データからシュート力・守備力・総合力を計算
- 攻撃力が高くて相手の守備が弱いほど多く点が入る
- 乱数はmatch_idのhashでシードして再現可能

使い方:
  python scripts/predict_all_matches.py
"""

import json
import random
import sys
from pathlib import Path

# ── パス設定 ─────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
DATA = BASE / "data"
PLAYERS_DIR = DATA / "players"
SCHEDULE_FILE = DATA / "matches" / "schedule.json"
GROUPS_FILE = DATA / "groups" / "group_assignments.json"
PREDICTIONS_DIR = DATA / "predictions"

PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

# ── ブラケット定数（app/app.py からコピー） ───────────────────────────────────
R32_SLOTS = [
    # (match_id, slot_home, slot_away, date, time_et)
    ("KO001", "1E", "3ABCDF", "2026-06-28", "12:00"),
    ("KO002", "1I", "3CDFGH", "2026-06-28", "16:00"),
    ("KO003", "2A", "2B",     "2026-06-28", "20:00"),
    ("KO004", "1F", "2C",     "2026-06-29", "12:00"),
    ("KO005", "2K", "2L",     "2026-06-29", "16:00"),
    ("KO006", "1H", "2J",     "2026-06-29", "20:00"),
    ("KO007", "1D", "3BEFIJ", "2026-06-30", "12:00"),
    ("KO008", "1G", "3AEHIJ", "2026-06-30", "16:00"),
    ("KO009", "1C", "2F",     "2026-06-30", "20:00"),
    ("KO010", "2E", "2I",     "2026-07-01", "12:00"),
    ("KO011", "1A", "3CEFHI", "2026-07-01", "16:00"),
    ("KO012", "1L", "3EHIJK", "2026-07-01", "20:00"),
    ("KO013", "1J", "2H",     "2026-07-02", "12:00"),
    ("KO014", "2D", "2G",     "2026-07-02", "16:00"),
    ("KO015", "1B", "3EFGIJ", "2026-07-02", "20:00"),
    ("KO016", "1K", "3DEIJL", "2026-07-03", "12:00"),
]

R16_SLOTS = [
    # (match_id, winner_of_1, winner_of_2, date, time_et)
    ("KO017", "KO001", "KO002", "2026-07-05", "16:00"),
    ("KO018", "KO003", "KO004", "2026-07-05", "20:00"),
    ("KO019", "KO005", "KO006", "2026-07-06", "16:00"),
    ("KO020", "KO007", "KO008", "2026-07-06", "20:00"),
    ("KO021", "KO009", "KO010", "2026-07-07", "16:00"),
    ("KO022", "KO011", "KO012", "2026-07-07", "20:00"),
    ("KO023", "KO013", "KO014", "2026-07-08", "16:00"),
    ("KO024", "KO015", "KO016", "2026-07-08", "20:00"),
]

QF_SLOTS = [
    ("KO025", "KO017", "KO018", "2026-07-11", "16:00"),
    ("KO026", "KO019", "KO020", "2026-07-11", "20:00"),
    ("KO027", "KO021", "KO022", "2026-07-12", "16:00"),
    ("KO028", "KO023", "KO024", "2026-07-12", "20:00"),
]

SF_SLOTS = [
    ("KO029", "KO025", "KO026", "2026-07-14", "20:00"),
    ("KO030", "KO027", "KO028", "2026-07-15", "20:00"),
]

BRONZE_SLOT = ("KO031", "KO029_loser", "KO030_loser", "2026-07-18", "16:00")
FINAL_SLOT  = ("KO032", "KO029", "KO030", "2026-07-19", "20:00")

# R32の3位枠割り当て順序
THIRD_SLOT_ORDER = ["KO001", "KO002", "KO007", "KO008", "KO011", "KO012", "KO015", "KO016"]

# フラグ絵文字
FLAGS = {
    "MEX": "🇲🇽", "RSA": "🇿🇦", "KOR": "🇰🇷", "CZE": "🇨🇿",
    "CAN": "🇨🇦", "BIH": "🇧🇦", "USA": "🇺🇸", "PAR": "🇵🇾",
    "QAT": "🇶🇦", "SUI": "🇨🇭", "AUS": "🇦🇺", "TUR": "🇹🇷",
    "BRA": "🇧🇷", "MAR": "🇲🇦", "GER": "🇩🇪", "CUW": "🇨🇼",
    "HAI": "🇭🇹", "SCO": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "NED": "🇳🇱", "JPN": "🇯🇵",
    "CIV": "🇨🇮", "ECU": "🇪🇨", "SWE": "🇸🇪", "TUN": "🇹🇳",
    "ESP": "🇪🇸", "CPV": "🇨🇻", "AUT": "🇦🇹", "JOR": "🇯🇴",
    "IRN": "🇮🇷", "NZL": "🇳🇿", "BEL": "🇧🇪", "EGY": "🇪🇬",
    "GHA": "🇬🇭", "PAN": "🇵🇦", "IRQ": "🇮🇶", "NOR": "🇳🇴",
    "FRA": "🇫🇷", "SEN": "🇸🇳", "ARG": "🇦🇷", "ALG": "🇩🇿",
    "ENG": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "CRO": "🇭🇷", "UZB": "🇺🇿", "COL": "🇨🇴",
    "POR": "🇵🇹", "COD": "🇨🇩", "KSA": "🇸🇦", "URU": "🇺🇾",
}


def flag(code: str) -> str:
    return FLAGS.get(code, "")


# ── チーム強度計算 ──────────────────────────────────────────────────────────────

def team_strength(code: str) -> dict:
    """
    EA FC 26データからチームの攻撃力・守備力・総合力を計算する。

    attack  = shooting > 40 の選手の shooting 平均
    defense = defending > 40 の選手の defending 平均
    overall = 全選手の overall 平均

    EAFC26カバレッジが低いチーム（< 50%）は OVR から atk/def を推定する。
    これによりデータ不足チームが不当に強くなるバグを防ぐ。
    """
    path = PLAYERS_DIR / f"{code}.json"
    if not path.exists():
        return {"atk": 60.0, "def": 60.0, "ovr": 65.0}

    with open(path) as f:
        data = json.load(f)

    players = data.get("players", [])
    total_players = len(players)

    atk_vals = []
    def_vals = []
    ovr_vals = []

    for p in players:
        eafc = p.get("eafc26", {})
        shooting  = eafc.get("shooting")
        defending = eafc.get("defending")
        overall   = eafc.get("overall")

        if overall is not None:
            ovr_vals.append(overall)
        if shooting is not None and shooting > 40:
            atk_vals.append(shooting)
        if defending is not None and defending > 40:
            def_vals.append(defending)

    overall = sum(ovr_vals) / len(ovr_vals) if ovr_vals else 65.0

    # OVRカバレッジが低い場合（選手の半数以下にしかOVRデータがない）、
    # OVRから攻守を推定する（shooting ≈ OVR×0.87, defending ≈ OVR×0.92）
    coverage = len(ovr_vals) / total_players if total_players > 0 else 0.0

    if coverage < 0.5 or len(atk_vals) < 5:
        # OVRから推定した基準値
        estimated_atk = overall * 0.87
        estimated_def = overall * 0.92
        if len(atk_vals) >= 3:
            # 実データで補間（実データ重み: coverage, 推定値重み: 1-coverage）
            actual_atk = sum(atk_vals) / len(atk_vals)
            actual_def = sum(def_vals) / len(def_vals) if def_vals else estimated_def
            attack  = actual_atk * coverage + estimated_atk * (1 - coverage)
            defense = actual_def * coverage + estimated_def * (1 - coverage)
        else:
            attack  = estimated_atk
            defense = estimated_def
    else:
        attack  = sum(atk_vals) / len(atk_vals)
        defense = sum(def_vals) / len(def_vals) if def_vals else overall * 0.92

    return {"atk": attack, "def": defense, "ovr": overall}


# 全チームの強度をキャッシュ
_strength_cache: dict = {}


def get_strength(code: str) -> dict:
    if code not in _strength_cache:
        _strength_cache[code] = team_strength(code)
    return _strength_cache[code]


# ── 期待得点計算 ────────────────────────────────────────────────────────────────

def expected_goals(team_a_code: str, team_b_code: str) -> float:
    """
    team_a（攻撃側）が team_b（守備側）に対する期待得点を返す。

    base = 1.2（ワールドカップ平均得点）
    atk_ratio = チームAの攻撃力 / 70.0
    def_ratio = 70.0 / チームBの守備力  （守備が強いほど低くなる）
    xg = base * atk_ratio * def_ratio  → クランプ [0.4, 3.5]
    """
    sa = get_strength(team_a_code)
    sb = get_strength(team_b_code)

    base = 1.2
    atk_ratio = sa["atk"] / 70.0
    def_ratio = 70.0 / max(sb["def"], 1.0)  # ゼロ除算防止
    xg = base * atk_ratio * def_ratio
    return max(0.4, min(3.5, xg))


def predict_score(match_id: str, home_code: str, away_code: str, is_knockout: bool = False) -> dict:
    """
    match_id をシードにして再現可能な予測スコアを返す。

    アップセット要素: xG差 < 0.3 のとき 25% の確率で結果を逆転させる。
    ノックアウトでは引き分けを ET/PK で解決する。
    """
    xg_home = expected_goals(home_code, away_code)
    xg_away = expected_goals(away_code, home_code)

    # 再現可能な乱数 (match_id の hash でシード)
    rng = random.Random(hash(match_id) & 0xFFFFFFFF)

    # ノイズを加えてスコアを整数に変換
    noise_home = rng.uniform(-0.4, 0.4)
    noise_away = rng.uniform(-0.4, 0.4)
    home_goals = max(0, round(xg_home + noise_home))
    away_goals = max(0, round(xg_away + noise_away))

    # アップセット判定: xG差が小さいとき、まれに結果を逆転
    xg_diff = abs(xg_home - xg_away)
    if xg_diff < 0.3:
        if rng.random() < 0.25:
            home_goals, away_goals = away_goals, home_goals

    result = {"home": home_goals, "away": away_goals}

    if is_knockout:
        et = False
        pk = False
        if home_goals == away_goals:
            # 引き分け → 延長戦へ
            et = True
            if rng.random() < 0.4:
                # 延長戦で決着: 期待得点が高い方が点を取る
                if xg_home >= xg_away:
                    home_goals += 1
                else:
                    away_goals += 1
            else:
                # PK戦へ: 期待得点が高い方が勝つ
                pk = True
                if xg_home >= xg_away:
                    home_goals += 1
                else:
                    away_goals += 1
        result = {"home": home_goals, "away": away_goals, "et": et, "pk": pk}

    return result


# ── グループステージ順位計算 ────────────────────────────────────────────────────

def compute_standings(predictions: dict, schedule_matches: list) -> dict:
    """グループステージ予測から各グループの順位表を計算する (W=3, D=1, L=0, タイブレーク: GD→GF→H2H)。"""
    groups: dict = {}
    for m in schedule_matches:
        grp = m["group"]
        if grp not in groups:
            groups[grp] = {}
        for code in (m["home"], m["away"]):
            if code not in groups[grp]:
                groups[grp][code] = {"pts": 0, "gd": 0, "gf": 0, "results_vs": {}}

    for m in schedule_matches:
        mid = m["match_id"]
        grp = m["group"]
        h_code = m["home"]
        a_code = m["away"]
        pick = predictions.get(mid)
        if pick is None:
            continue
        hg = int(pick["home"])
        ag = int(pick["away"])

        if hg > ag:
            h_pts, a_pts = 3, 0
            h_res, a_res = "W", "L"
        elif hg < ag:
            h_pts, a_pts = 0, 3
            h_res, a_res = "L", "W"
        else:
            h_pts = a_pts = 1
            h_res = a_res = "D"

        td = groups[grp]
        td[h_code]["pts"] += h_pts
        td[h_code]["gd"]  += hg - ag
        td[h_code]["gf"]  += hg
        td[h_code]["results_vs"][a_code] = {"scored": hg, "conceded": ag, "res": h_res}

        td[a_code]["pts"] += a_pts
        td[a_code]["gd"]  += ag - hg
        td[a_code]["gf"]  += ag
        td[a_code]["results_vs"][h_code] = {"scored": ag, "conceded": hg, "res": a_res}

    def h2h_key(code, others, td):
        pts, gd, gf = 0, 0, 0
        for opp in others:
            rv = td[code]["results_vs"].get(opp)
            if rv:
                pts += 3 if rv["res"] == "W" else (1 if rv["res"] == "D" else 0)
                gd  += rv["scored"] - rv["conceded"]
                gf  += rv["scored"]
        return (pts, gd, gf)

    standings = {}
    for grp, teams in groups.items():
        raw = [(c, d["pts"], d["gd"], d["gf"]) for c, d in teams.items()]
        raw.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)

        result = []
        i = 0
        while i < len(raw):
            j = i + 1
            while (j < len(raw)
                   and raw[j][1] == raw[i][1]
                   and raw[j][2] == raw[i][2]
                   and raw[j][3] == raw[i][3]):
                j += 1
            group_slice = list(raw[i:j])
            if j - i > 1:
                td = groups[grp]
                tied_codes = [x[0] for x in group_slice]
                group_slice.sort(
                    key=lambda item: h2h_key(
                        item[0], [c for c in tied_codes if c != item[0]], td
                    ),
                    reverse=True,
                )
            result.extend(group_slice)
            i = j

        standings[grp] = result
    return standings


def get_third_place_qualifiers(standings: dict) -> list:
    """全グループの3位チームから上位8チームを pts→GD→GF で選ぶ。"""
    thirds = []
    for grp in sorted(standings.keys()):
        grp_standing = standings[grp]
        if len(grp_standing) >= 3:
            thirds.append(grp_standing[2])  # (code, pts, gd, gf)
    thirds.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    return [t[0] for t in thirds[:8]]


# ── ブラケット解決 ──────────────────────────────────────────────────────────────

def resolve_ko_slot(slot: str, standings: dict, third_qualifiers: list, ko_picks: dict):
    """スロット文字列（"1A", "2B", "KO001", "KO029_loser"）をチームコードに解決する。"""
    if len(slot) == 2 and slot[0] in ("1", "2"):
        rank = int(slot[0]) - 1
        grp = slot[1]
        grp_standing = standings.get(grp, [])
        if len(grp_standing) > rank:
            return grp_standing[rank][0]
        return None

    if slot.startswith("3"):
        return None  # 呼び出し側で third_slot_assignments から解決

    if slot.endswith("_loser"):
        src_mid = slot[:-6]
        pick = ko_picks.get(src_mid, {})
        home_code = pick.get("home_code")
        away_code = pick.get("away_code")
        h_score = int(pick.get("home") or 0)
        a_score = int(pick.get("away") or 0)
        if not home_code and not away_code:
            return None
        if h_score > a_score:
            return away_code
        else:
            return home_code  # 同点 or アウェイ勝ち → ホームが敗者

    if slot.startswith("KO"):
        pick = ko_picks.get(slot, {})
        home_code = pick.get("home_code")
        away_code = pick.get("away_code")
        h_score = int(pick.get("home") or 0)
        a_score = int(pick.get("away") or 0)
        if not home_code and not away_code:
            return None
        if h_score > a_score:
            return home_code
        elif a_score > h_score:
            return away_code
        else:
            return home_code  # 同点 → ホーム（PK勝ち）

    return None


def simulate_ko_round(
    slots: list,
    standings: dict,
    third_qualifiers: list,
    ko_picks: dict,
    third_slot_assignments: dict,
) -> list:
    """
    ノックアウトラウンド 1 ラウンド分をシミュレートして ko_picks を更新する。
    返り値: [(match_id, home_code, away_code, score_dict)] のリスト
    """
    results = []
    for match_id, slot_h, slot_a, _date, _time_et in slots:
        # ホームチームを解決
        if slot_h.startswith("3"):
            home_code = third_slot_assignments.get(match_id)
        else:
            home_code = resolve_ko_slot(slot_h, standings, third_qualifiers, ko_picks)

        # アウェイチームを解決
        if slot_a.startswith("3"):
            away_code = third_slot_assignments.get(match_id)
        else:
            away_code = resolve_ko_slot(slot_a, standings, third_qualifiers, ko_picks)

        if not home_code or not away_code:
            print(
                f"  [警告] {match_id}: チームが未確定 "
                f"(home={home_code}, away={away_code})",
                file=sys.stderr,
            )
            ko_picks[match_id] = {
                "home_code": home_code,
                "away_code": away_code,
                "home": 0,
                "away": 0,
                "et": False,
                "pk": False,
            }
            results.append((match_id, home_code, away_code, {"home": 0, "away": 0, "et": False, "pk": False}))
            continue

        score = predict_score(match_id, home_code, away_code, is_knockout=True)
        ko_picks[match_id] = {"home_code": home_code, "away_code": away_code, **score}
        results.append((match_id, home_code, away_code, score))

    return results


# ── メイン処理 ──────────────────────────────────────────────────────────────────

def main():
    print("=== AI予測: FIFA ワールドカップ 2026 ===\n")

    # スケジュール・グループ情報を読み込む
    with open(SCHEDULE_FILE) as f:
        schedule_data = json.load(f)
    schedule_matches = schedule_data["group_stage"]

    with open(GROUPS_FILE) as f:
        groups_data = json.load(f)["groups"]

    print(f"グループステージ試合数: {len(schedule_matches)}")

    # ─── Step 1: グループステージ全試合を予測 ───────────────────────────────────
    print("\n[1/4] グループステージを予測中...")
    gs_predictions = {}
    for m in schedule_matches:
        mid = m["match_id"]
        score = predict_score(mid, m["home"], m["away"], is_knockout=False)
        gs_predictions[mid] = score

    gs_output = {
        "username": "AI予測",
        "predictions": gs_predictions,
    }
    gs_path = PREDICTIONS_DIR / "AI予測.json"
    with open(gs_path, "w", encoding="utf-8") as f:
        json.dump(gs_output, f, ensure_ascii=False, indent=2)
    print(f"  → 保存: {gs_path}")

    # ─── Step 2: グループ順位を計算 ─────────────────────────────────────────────
    print("\n[2/4] グループ順位を計算中...")
    standings = compute_standings(gs_predictions, schedule_matches)
    third_qualifiers = get_third_place_qualifiers(standings)

    all_groups = sorted(standings.keys())
    print("\nグループ通過チーム:")
    for grp in all_groups:
        ranked = standings[grp]
        first  = ranked[0][0] if len(ranked) > 0 else "?"
        second = ranked[1][0] if len(ranked) > 1 else "?"
        third  = ranked[2][0] if len(ranked) > 2 else "?"
        marker = " ✅3位通過" if third in third_qualifiers else ""
        print(f"  グループ {grp}: 1位 {first}  2位 {second}  3位 {third}{marker}")

    # ─── Step 3: ノックアウトブラケットをシミュレート ────────────────────────────
    print("\n[3/4] ノックアウトブラケットをシミュレート中...")
    ko_picks: dict = {}

    # 3位枠の割り当て (THIRD_SLOT_ORDER 順)
    third_slot_assignments = {
        ko_mid: (third_qualifiers[i] if i < len(third_qualifiers) else None)
        for i, ko_mid in enumerate(THIRD_SLOT_ORDER)
    }

    r32_results = simulate_ko_round(R32_SLOTS, standings, third_qualifiers, ko_picks, third_slot_assignments)
    r16_results = simulate_ko_round(R16_SLOTS, standings, third_qualifiers, ko_picks, {})
    qf_results  = simulate_ko_round(QF_SLOTS,  standings, third_qualifiers, ko_picks, {})
    sf_results  = simulate_ko_round(SF_SLOTS,  standings, third_qualifiers, ko_picks, {})

    # 3位決定戦
    bronze_home = resolve_ko_slot("KO029_loser", standings, third_qualifiers, ko_picks)
    bronze_away = resolve_ko_slot("KO030_loser", standings, third_qualifiers, ko_picks)
    bronze_score = predict_score(BRONZE_SLOT[0], bronze_home or "?", bronze_away or "?", is_knockout=True)
    ko_picks[BRONZE_SLOT[0]] = {"home_code": bronze_home, "away_code": bronze_away, **bronze_score}

    # 決勝
    final_home = resolve_ko_slot("KO029", standings, third_qualifiers, ko_picks)
    final_away = resolve_ko_slot("KO030", standings, third_qualifiers, ko_picks)
    final_score = predict_score(FINAL_SLOT[0], final_home or "?", final_away or "?", is_knockout=True)
    ko_picks[FINAL_SLOT[0]] = {"home_code": final_home, "away_code": final_away, **final_score}

    # 優勝チームを決定
    if (final_score["home"] or 0) >= (final_score["away"] or 0):
        champion = final_home
    else:
        champion = final_away

    # ─── Step 4: ブラケット予測を保存 ────────────────────────────────────────────
    ko_picks_clean = {
        mid: {
            "home": pick.get("home", 0),
            "away": pick.get("away", 0),
            "et":   pick.get("et", False),
            "pk":   pick.get("pk", False),
        }
        for mid, pick in ko_picks.items()
    }

    bracket_output = {
        "username": "AI予測",
        "ko_picks": ko_picks_clean,
        "champion": champion,
    }
    bracket_path = PREDICTIONS_DIR / "AI予測_bracket.json"
    with open(bracket_path, "w", encoding="utf-8") as f:
        json.dump(bracket_output, f, ensure_ascii=False, indent=2)
    print(f"  → 保存: {bracket_path}")

    # ─── トーナメント結果サマリーを表示 ──────────────────────────────────────────
    def score_str(pick: dict) -> str:
        h = pick.get("home", "?")
        a = pick.get("away", "?")
        suffix = " (PK)" if pick.get("pk") else (" (ET)" if pick.get("et") else "")
        return f"{h}-{a}{suffix}"

    def winner_of(mid: str) -> str:
        pick = ko_picks.get(mid, {})
        h_code = pick.get("home_code") or ""
        a_code = pick.get("away_code") or ""
        h_score = int(pick.get("home") or 0)
        a_score = int(pick.get("away") or 0)
        return h_code if h_score >= a_score else a_code

    print("\n" + "=" * 55)
    print("=== AI予測 トーナメント結果 ===")
    print("=" * 55)

    print("\nグループ通過:")
    for grp in all_groups:
        ranked = standings[grp]
        first  = ranked[0][0] if len(ranked) > 0 else "?"
        second = ranked[1][0] if len(ranked) > 1 else "?"
        third  = ranked[2][0] if len(ranked) > 2 else "?"
        if third in third_qualifiers:
            print(
                f"  {grp}: 1位 {flag(first)}{first}  "
                f"2位 {flag(second)}{second}  "
                f"3位通過 {flag(third)}{third}"
            )
        else:
            print(
                f"  {grp}: 1位 {flag(first)}{first}  "
                f"2位 {flag(second)}{second}"
            )

    def print_round(label: str, round_results: list):
        print(f"\n{label}:")
        for match_id, home_code, away_code, score in round_results:
            hf = flag(home_code) if home_code else ""
            af = flag(away_code) if away_code else ""
            w  = winner_of(match_id)
            print(
                f"  {match_id}: {hf}{home_code} {score_str(score)} "
                f"{af}{away_code}  → {flag(w)}{w}"
            )

    print_round("R32", r32_results)
    print_round("R16", r16_results)
    print_round("QF (準々決勝)", qf_results)
    print_round("SF (準決勝)", sf_results)

    bpick = ko_picks.get(BRONZE_SLOT[0], {})
    print(f"\n3位決定戦:")
    print(
        f"  {BRONZE_SLOT[0]}: {flag(bronze_home)}{bronze_home} "
        f"{score_str(bpick)} "
        f"{flag(bronze_away)}{bronze_away}"
    )

    fpick = ko_picks.get(FINAL_SLOT[0], {})
    print(f"\n決勝:")
    print(
        f"  {FINAL_SLOT[0]}: {flag(final_home)}{final_home} "
        f"{score_str(fpick)} "
        f"{flag(final_away)}{final_away}"
    )

    print(f"\n🏆 優勝: {flag(champion)}{champion}")
    print("\n" + "=" * 55)
    print("完了!")


if __name__ == "__main__":
    main()
