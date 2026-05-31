"""
FIFA World Cup 2026 Multi-player Prediction App
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from scoring import compute_per_match_scores, compute_total_score, score_match

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
DATA = BASE / "data"
SCHEDULE_FILE = DATA / "matches" / "schedule.json"
GROUPS_FILE = DATA / "groups" / "group_assignments.json"
PLAYERS_DIR = DATA / "players"
TACTICS_DIR = DATA / "tactics"
PREDICTIONS_DIR = DATA / "predictions"
ANALYSIS_DIR = BASE / "analysis" / "teams"
RESULTS_FILE = DATA / "results.json"

PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_PASSWORD = "wcup2026admin"

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

WEEKDAYS_JA = ["月", "火", "水", "木", "金", "土", "日"]

TEAM_NAMES_JA = {
    "MEX": "メキシコ",     "RSA": "南アフリカ",   "KOR": "韓国",
    "CZE": "チェコ",       "CAN": "カナダ",        "BIH": "ボスニア",
    "QAT": "カタール",     "SUI": "スイス",        "BRA": "ブラジル",
    "MAR": "モロッコ",     "HAI": "ハイチ",        "SCO": "スコットランド",
    "USA": "アメリカ",     "PAR": "パラグアイ",    "AUS": "オーストラリア",
    "TUR": "トルコ",       "GER": "ドイツ",        "CUW": "キュラソー",
    "CIV": "コートジボワール", "ECU": "エクアドル", "NED": "オランダ",
    "JPN": "日本",         "SWE": "スウェーデン",  "TUN": "チュニジア",
    "BEL": "ベルギー",     "EGY": "エジプト",      "IRN": "イラン",
    "NZL": "ニュージーランド", "ESP": "スペイン",   "CPV": "カーボベルデ",
    "KSA": "サウジアラビア", "URU": "ウルグアイ",  "FRA": "フランス",
    "SEN": "セネガル",     "IRQ": "イラク",        "NOR": "ノルウェー",
    "ARG": "アルゼンチン", "ALG": "アルジェリア",  "AUT": "オーストリア",
    "JOR": "ヨルダン",     "POR": "ポルトガル",    "COL": "コロンビア",
    "COD": "コンゴ",       "UZB": "ウズベキスタン","ENG": "イングランド",
    "CRO": "クロアチア",   "GHA": "ガーナ",        "PAN": "パナマ",
}


# ── Data helpers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_schedule():
    with open(SCHEDULE_FILE) as f:
        data = json.load(f)
    return data.get("group_stage", [])


@st.cache_data(ttl=60)
def load_groups():
    with open(GROUPS_FILE) as f:
        return json.load(f)["groups"]


def load_results():
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return {}


def save_results(results: dict):
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def load_prediction(username: str) -> dict:
    path = PREDICTIONS_DIR / f"{username}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"username": username, "predictions": {}}


def save_prediction(username: str, data: dict):
    path = PREDICTIONS_DIR / f"{username}.json"
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_users():
    excluded = {"AI予測"}
    return sorted([
        p.stem for p in PREDICTIONS_DIR.glob("*.json")
        if not p.stem.endswith("_bracket") and p.stem not in excluded
    ])


def et_to_jst(date_str: str, time_str: str) -> datetime:
    dt_et = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return dt_et + timedelta(hours=13)


def format_jst(dt_jst: datetime) -> str:
    wd = WEEKDAYS_JA[dt_jst.weekday()]
    return dt_jst.strftime(f"%-m/%-d ({wd}) %H:%M JST")


def flag(code: str) -> str:
    return FLAGS.get(code, "🏳")


def ja(code: str) -> str:
    return TEAM_NAMES_JA.get(code, code)


def team_ja(code: str) -> str:
    """Flag + Katakana name for display."""
    return f"{flag(code)} {ja(code)}" if code else "—"


def match_has_result(match_id: str, results: dict) -> bool:
    r = results.get(match_id, {})
    return r.get("home") is not None and r.get("away") is not None


def is_knockout(match_id: str) -> bool:
    return not match_id.startswith("GS")


@st.cache_data(ttl=300)
def load_ai_prediction() -> tuple:
    gs_path = PREDICTIONS_DIR / "AI予測.json"
    bracket_path = PREDICTIONS_DIR / "AI予測_bracket.json"
    gs_preds: dict = {}
    ko_picks: dict = {}
    champion = None
    if gs_path.exists():
        with open(gs_path) as f:
            gs_preds = json.load(f).get("predictions", {})
    if bracket_path.exists():
        with open(bracket_path) as f:
            bd = json.load(f)
            ko_picks = bd.get("ko_picks", {})
            champion = bd.get("champion")
    return gs_preds, ko_picks, champion


@st.cache_data(ttl=300)
def load_tactics_data(code: str) -> dict | None:
    path = TACTICS_DIR / f"{code}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def show_team_summary(code: str):
    """Brief inline team summary used inside prediction page expanders."""
    player_path = PLAYERS_DIR / f"{code}.json"
    if player_path.exists():
        with open(player_path) as f:
            td = json.load(f)
        players = td.get("players", [])
        top5 = sorted(
            [p for p in players if p.get("eafc26", {}).get("overall")],
            key=lambda p: p["eafc26"]["overall"],
            reverse=True,
        )[:5]
        if top5:
            st.caption("**主要選手 (EA FC 26 OVR Top5)**")
            rows = [
                {
                    "名前": p["name"],
                    "Pos": p.get("pos", "?"),
                    "OVR": p["eafc26"]["overall"],
                }
                for p in top5
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    tactics = load_tactics_data(code)
    if tactics:
        pf = tactics.get("primary_formation", "?")
        starters = tactics.get("top_starters", [])[:7]
        st.caption(f"**フォーメーション:** {pf}")
        if starters:
            st.caption(f"**先発常連:** {', '.join(starters)}")


# ── R32ブラケット定義 ──────────────────────────────────────────────────────────
R32_SLOTS = [
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
FINAL_SLOT  = ("KO032", "KO029",       "KO030",       "2026-07-19", "20:00")

ALL_CODES = [
    "MEX","RSA","KOR","CZE","CAN","BIH","QAT","SUI","BRA","MAR","HAI","SCO",
    "USA","PAR","AUS","TUR","GER","CUW","CIV","ECU","NED","JPN","SWE","TUN",
    "BEL","EGY","IRN","NZL","ESP","CPV","KSA","URU","FRA","SEN","IRQ","NOR",
    "ARG","ALG","AUT","JOR","POR","COD","UZB","COL","ENG","CRO","GHA","PAN",
]

THIRD_SLOT_ORDER = ["KO001", "KO002", "KO007", "KO008", "KO011", "KO012", "KO015", "KO016"]


# ── Bracket helper functions ──────────────────────────────────────────────────

def compute_standings_from_predictions(user_preds: dict, schedule_matches: list) -> dict:
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
        pick = user_preds.get(mid)
        if pick is None:
            continue
        hg = pick.get("home")
        ag = pick.get("away")
        if hg is None or ag is None:
            continue
        hg, ag = int(hg), int(ag)

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

    def h2h_key(code: str, others: list, td: dict) -> tuple:
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
                    key=lambda item: h2h_key(item[0], [c for c in tied_codes if c != item[0]], td),
                    reverse=True,
                )
            result.extend(group_slice)
            i = j

        standings[grp] = result
    return standings


def get_third_place_qualifiers(standings: dict) -> list:
    thirds = []
    for grp in sorted(standings.keys()):
        grp_standing = standings[grp]
        if len(grp_standing) >= 3:
            thirds.append(grp_standing[2])
    thirds.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    return [t[0] for t in thirds[:8]]


def resolve_ko_slot(slot: str, standings: dict, third_qualifiers: list, ko_picks: dict) -> str | None:
    if len(slot) == 2 and slot[0] in ("1", "2"):
        rank = int(slot[0]) - 1
        grp = slot[1]
        grp_standing = standings.get(grp, [])
        if len(grp_standing) > rank:
            return grp_standing[rank][0]
        return None

    if slot.startswith("3"):
        return None

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
        elif a_score > h_score:
            return home_code
        else:
            return away_code

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
            return home_code

    return None


def load_bracket_prediction(username: str) -> dict:
    path = PREDICTIONS_DIR / f"{username}_bracket.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"username": username, "ko_picks": {}, "champion": None}


def save_bracket_prediction(username: str, data: dict):
    path = PREDICTIONS_DIR / f"{username}_bracket.json"
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def team_label(code: str) -> str:
    return team_ja(code) if code else "—"


# ── Pages ───────────────────────────────────────────────────────────────────

def page_login():
    st.title("🏆 FIFA ワールドカップ 2026 予測アプリ")
    st.markdown("---")
    st.subheader("ニックネームを入力して参加しよう")
    st.markdown("初めての方はそのまま登録、前回参加した方は同じ名前を入力すると記録が引き継がれます。")

    name = st.text_input("ニックネーム", max_chars=30, placeholder="例: たろう、Dad、Kenji...")

    if st.button("はじめる →", type="primary"):
        name = name.strip()
        if not name:
            st.error("名前を入力してください。")
            return

        path = PREDICTIONS_DIR / f"{name}.json"
        if path.exists():
            data = load_prediction(name)
            preds = data.get("predictions", {})
            n_preds = len([v for v in preds.values() if v.get("home") is not None])
            results = load_results()
            total_pts = compute_total_score(preds, results)
            st.session_state["username"] = name
            st.session_state["welcome_msg"] = (
                f"おかえり、{name}さん！　予測済み: {n_preds}試合 / 現在 {total_pts}pt"
            )
        else:
            save_prediction(name, {"username": name, "predictions": {}})
            st.session_state["username"] = name
            st.session_state["welcome_msg"] = f"ようこそ、{name}さん！予測を入力してみよう ⚽"

        st.rerun()


def page_predict():
    st.title("⚽ 予測入力")

    username = st.session_state["username"]
    user_data = load_prediction(username)
    preds = user_data.get("predictions", {})
    matches = load_schedule()
    results = load_results()
    ai_preds, _, _ = load_ai_prediction()

    all_groups = sorted(load_groups().keys())

    # Build group → matches dict, sorted by JST datetime within each group
    group_matches: dict[str, list] = {g: [] for g in all_groups}
    for m in matches:
        group_matches[m["group"]].append(m)
    for g in all_groups:
        group_matches[g].sort(key=lambda m: et_to_jst(m["date"], m["time_et"]))

    standings = compute_standings_from_predictions(preds, matches)

    tabs = st.tabs([f"グループ {g}" for g in all_groups])
    changed: dict = {}

    for i, grp in enumerate(all_groups):
        with tabs[i]:
            # ── Provisional standings ──
            grp_standing = standings.get(grp, [])
            if any(preds.get(m["match_id"]) for m in group_matches[grp]):
                standing_rows = []
                for rank, (code, pts, gd, gf) in enumerate(grp_standing, 1):
                    icon = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🔸" if rank == 3 else ""))
                    standing_rows.append({
                        "": icon,
                        "チーム": team_ja(code),
                        "勝点": pts,
                        "得失": f"{gd:+d}",
                        "得点": gf,
                    })
                st.dataframe(
                    pd.DataFrame(standing_rows),
                    hide_index=True,
                    use_container_width=True,
                    height=185,
                )
                st.caption("※ 保存後に更新されます")
                st.markdown("---")

            # ── Match inputs ──
            for m in group_matches[grp]:
                mid = m["match_id"]
                home_code = m["home"]
                away_code = m["away"]
                dt_jst = et_to_jst(m["date"], m["time_et"])
                locked = match_has_result(mid, results)
                existing = preds.get(mid, {})
                ex_h = existing.get("home", 0) if existing.get("home") is not None else 0
                ex_a = existing.get("away", 0) if existing.get("away") is not None else 0
                ai = ai_preds.get(mid, {})

                with st.container():
                    col_teams, col_score, col_ai, col_pts = st.columns([4, 3, 2, 1])

                    with col_teams:
                        st.markdown(
                            f"**{team_ja(home_code)}** vs **{team_ja(away_code)}**  \n"
                            f"<span style='font-size:0.8em;color:gray'>{format_jst(dt_jst)}</span>",
                            unsafe_allow_html=True,
                        )

                    with col_score:
                        if locked:
                            r = results[mid]
                            st.markdown(
                                f"結果: **{r['home']} - {r['away']}**  \n"
                                f"予測: {existing.get('home', '—')} - {existing.get('away', '—')}"
                            )
                        else:
                            c1, c2, c3 = st.columns([2, 1, 2])
                            with c1:
                                h_val = st.number_input(
                                    home_code, 0, 9, value=ex_h,
                                    key=f"h_{mid}", label_visibility="collapsed",
                                )
                            with c2:
                                st.markdown(
                                    "<div style='text-align:center;padding-top:8px'>-</div>",
                                    unsafe_allow_html=True,
                                )
                            with c3:
                                a_val = st.number_input(
                                    away_code, 0, 9, value=ex_a,
                                    key=f"a_{mid}", label_visibility="collapsed",
                                )
                            changed[mid] = {"home": h_val, "away": a_val}

                    with col_ai:
                        if ai:
                            st.caption(f"🤖 AI予測\n{ai.get('home','?')}-{ai.get('away','?')}")

                    with col_pts:
                        if locked:
                            pts = score_match(mid, existing, results[mid])
                            st.markdown(f"🔒 **{pts}pt**")

                with st.expander(f"📋 {team_ja(home_code)} vs {team_ja(away_code)} チーム詳細"):
                    col_h, col_a = st.columns(2)
                    with col_h:
                        st.markdown(f"**{team_ja(home_code)}**")
                        show_team_summary(home_code)
                    with col_a:
                        st.markdown(f"**{team_ja(away_code)}**")
                        show_team_summary(away_code)

                st.divider()

    if changed:
        st.markdown("---")
        if st.button("💾 予測を保存", type="primary"):
            for mid, entry in changed.items():
                if not match_has_result(mid, results):
                    preds[mid] = entry
            user_data["predictions"] = preds
            save_prediction(username, user_data)
            st.success("保存しました！")
            st.rerun()


def page_bracket():
    st.title("🗓️ トーナメント事前予測")

    username = st.session_state["username"]
    st.info(f"**{username}** さんの予測　— グループステージの予測から対戦カードが自動で決まります")

    schedule_matches = load_schedule()
    user_data = load_prediction(username)
    user_preds = user_data.get("predictions", {})
    bdata = load_bracket_prediction(username)
    ko_picks = bdata.get("ko_picks", {})
    ai_gs, ai_ko, ai_champion = load_ai_prediction()

    standings = compute_standings_from_predictions(user_preds, schedule_matches)
    third_qualifiers = get_third_place_qualifiers(standings)

    # ── グループ通過チーム ──
    st.markdown("---")
    st.subheader("グループ通過チーム（自動計算）")

    groups_data = load_groups()
    all_groups = sorted(groups_data.keys())

    table_rows = []
    for grp in all_groups:
        ranked = standings.get(grp, [])
        first  = ranked[0][0] if len(ranked) > 0 else "—"
        second = ranked[1][0] if len(ranked) > 1 else "—"
        if len(ranked) >= 3:
            third_code, third_pts, third_gd, _ = ranked[2]
            third_qualified = third_code in third_qualifiers
            third_str = f"{team_label(third_code)} ({third_pts}pts, GD{third_gd:+d})"
        else:
            third_str = "—"
            third_qualified = False

        table_rows.append({
            "グループ": grp,
            "1位": team_label(first) if first != "—" else "—",
            "2位": team_label(second) if second != "—" else "—",
            "3位 (勝点/得失点差)": third_str,
            "3位通過?": "✅" if third_qualified else "",
        })

    if table_rows:
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        if len(third_qualifiers) < 8:
            st.caption(
                f"※ 現在 {len(third_qualifiers)}/8 チームが算出済み。"
                f"あと {8 - len(third_qualifiers)} グループの予測が必要です。"
            )

    # ── 3rd-place slot assignments ──
    third_slot_assignments: dict[str, str | None] = {}
    for idx, ko_mid in enumerate(THIRD_SLOT_ORDER):
        third_slot_assignments[ko_mid] = third_qualifiers[idx] if idx < len(third_qualifiers) else None

    def resolve_r32_slot(slot: str, match_id: str) -> str | None:
        if slot.startswith("3"):
            return third_slot_assignments.get(match_id)
        return resolve_ko_slot(slot, standings, third_qualifiers, ko_picks)

    def ko_match_input(match_id, home_code, away_code, date, time_et, round_label):
        dt_jst = et_to_jst(date, time_et)
        existing = ko_picks.get(match_id, {})
        ai_pick = ai_ko.get(match_id, {})

        home_disp = team_label(home_code) if home_code else "（未確定）"
        away_disp = team_label(away_code) if away_code else "（未確定）"

        with st.container():
            hdr, ai_col = st.columns([5, 2])
            with hdr:
                st.markdown(f"**{match_id}** `{round_label}` — {format_jst(dt_jst)}")
            with ai_col:
                if ai_pick:
                    st.caption(
                        f"🤖 AI: {ai_pick.get('home','?')}-{ai_pick.get('away','?')}"
                        + (" (PK)" if ai_pick.get("pk") else " (ET)" if ai_pick.get("et") else "")
                    )

            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 3])
            with c1:
                st.markdown(f"**{home_disp}**")
            with c2:
                h_score = st.number_input(
                    "H", 0, 20,
                    value=int(existing.get("home") or 0),
                    key=f"ko_hs_{match_id}",
                    label_visibility="collapsed",
                )
            with c3:
                st.markdown(
                    "<div style='text-align:center;padding-top:8px'>-</div>",
                    unsafe_allow_html=True,
                )
            with c4:
                a_score = st.number_input(
                    "A", 0, 20,
                    value=int(existing.get("away") or 0),
                    key=f"ko_as_{match_id}",
                    label_visibility="collapsed",
                )
            with c5:
                st.markdown(f"**{away_disp}**")

            ec1, ec2 = st.columns(2)
            with ec1:
                et = st.checkbox("延長戦", value=bool(existing.get("et", False)), key=f"ko_et_{match_id}")
            with ec2:
                pk = st.checkbox("PK戦", value=bool(existing.get("pk", False)), key=f"ko_pk_{match_id}")

            ko_picks[match_id] = {
                "home_code": home_code,
                "away_code": away_code,
                "home": h_score,
                "away": a_score,
                "et": et,
                "pk": pk,
            }
        st.divider()

    # ── 決勝トーナメント ──
    st.markdown("---")
    st.subheader("決勝トーナメント")

    with st.expander("🔵 ラウンド32 — 16試合 (6/28〜7/3)", expanded=True):
        for match_id, slot_h, slot_a, date, time_et in R32_SLOTS:
            home_code = resolve_r32_slot(slot_h, match_id)
            away_code = resolve_r32_slot(slot_a, match_id)
            ko_match_input(match_id, home_code, away_code, date, time_et, "R32")

    with st.expander("🟡 ラウンド16 — 8試合 (7/5〜7/8)"):
        for match_id, src_h, src_a, date, time_et in R16_SLOTS:
            home_code = resolve_ko_slot(src_h, standings, third_qualifiers, ko_picks)
            away_code = resolve_ko_slot(src_a, standings, third_qualifiers, ko_picks)
            ko_match_input(match_id, home_code, away_code, date, time_et, "R16")

    with st.expander("🟠 準々決勝 — 4試合 (7/11〜7/12)"):
        for match_id, src_h, src_a, date, time_et in QF_SLOTS:
            home_code = resolve_ko_slot(src_h, standings, third_qualifiers, ko_picks)
            away_code = resolve_ko_slot(src_a, standings, third_qualifiers, ko_picks)
            ko_match_input(match_id, home_code, away_code, date, time_et, "QF")

    with st.expander("🔴 準決勝 — 2試合 (7/14〜7/15)"):
        for match_id, src_h, src_a, date, time_et in SF_SLOTS:
            home_code = resolve_ko_slot(src_h, standings, third_qualifiers, ko_picks)
            away_code = resolve_ko_slot(src_a, standings, third_qualifiers, ko_picks)
            ko_match_input(match_id, home_code, away_code, date, time_et, "SF")

    with st.expander("🥉🏆 3位決定戦 & 決勝 (7/18〜7/19)"):
        bronze_home = resolve_ko_slot("KO029_loser", standings, third_qualifiers, ko_picks)
        bronze_away = resolve_ko_slot("KO030_loser", standings, third_qualifiers, ko_picks)
        ko_match_input(BRONZE_SLOT[0], bronze_home, bronze_away, BRONZE_SLOT[3], BRONZE_SLOT[4], "3位決定戦")

        final_home = resolve_ko_slot("KO029", standings, third_qualifiers, ko_picks)
        final_away = resolve_ko_slot("KO030", standings, third_qualifiers, ko_picks)
        ko_match_input(FINAL_SLOT[0], final_home, final_away, FINAL_SLOT[3], FINAL_SLOT[4], "決勝")

    # ── 優勝予想 ──
    st.markdown("---")
    st.subheader("🏆 優勝予想")

    finalist_home = resolve_ko_slot("KO029", standings, third_qualifiers, ko_picks)
    finalist_away = resolve_ko_slot("KO030", standings, third_qualifiers, ko_picks)
    finalists = [c for c in [finalist_home, finalist_away] if c]
    if finalists:
        st.caption(f"決勝進出予想: {' vs '.join(team_label(c) for c in finalists)}")
    if ai_champion:
        st.caption(f"🤖 AIの優勝予想: {team_label(ai_champion)}")

    champion_opts = ["（未選択）"] + ALL_CODES
    cur_champ = bdata.get("champion") or "（未選択）"
    if cur_champ not in champion_opts:
        cur_champ = "（未選択）"

    champion = st.selectbox(
        "優勝すると思うチームは？",
        champion_opts,
        index=champion_opts.index(cur_champ),
        format_func=lambda c: team_label(c) if c != "（未選択）" else "（未選択）",
        key="champion_pick",
    )

    st.markdown("---")
    if st.button("💾 保存", type="primary"):
        bdata["ko_picks"] = ko_picks
        bdata["champion"] = champion if champion != "（未選択）" else None
        save_bracket_prediction(username, bdata)
        st.success("保存しました！")
        st.rerun()


def page_admin():
    st.title("🔐 結果入力 (管理者)")

    if "admin_auth" not in st.session_state:
        st.session_state["admin_auth"] = False

    if not st.session_state["admin_auth"]:
        pw = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pw == ADMIN_PASSWORD:
                st.session_state["admin_auth"] = True
                st.rerun()
            else:
                st.error("パスワードが違います。")
        return

    st.success("管理者としてログイン中")
    matches = load_schedule()
    results = load_results()
    matches_sorted = sorted(matches, key=lambda m: et_to_jst(m["date"], m["time_et"]))

    st.markdown("---")
    for m in matches_sorted:
        mid = m["match_id"]
        home_code = m["home"]
        away_code = m["away"]
        dt_jst = et_to_jst(m["date"], m["time_et"])
        existing = results.get(mid, {})

        with st.expander(
            f"{mid} | {flag(home_code)}{home_code} vs {flag(away_code)}{away_code} — {format_jst(dt_jst)}"
            + (" ✅" if match_has_result(mid, results) else ""),
            expanded=not match_has_result(mid, results),
        ):
            c1, c2, c3 = st.columns([2, 1, 2])
            with c1:
                h_val = st.number_input(
                    f"ホーム ({home_code})", 0, 20,
                    value=existing.get("home") or 0,
                    key=f"res_h_{mid}",
                )
            with c2:
                st.markdown("<div style='text-align:center;padding-top:28px'>-</div>", unsafe_allow_html=True)
            with c3:
                a_val = st.number_input(
                    f"アウェイ ({away_code})", 0, 20,
                    value=existing.get("away") or 0,
                    key=f"res_a_{mid}",
                )

            entry: dict = {"home": h_val, "away": a_val}
            if is_knockout(mid):
                et_val = st.checkbox("延長戦あり", value=existing.get("et", False), key=f"res_et_{mid}")
                pk_val = st.checkbox("PK戦あり", value=existing.get("pk", False), key=f"res_pk_{mid}")
                entry["et"] = et_val
                entry["pk"] = pk_val

            if st.button(f"保存: {mid}", key=f"save_{mid}"):
                results[mid] = entry
                save_results(results)
                st.success(f"{mid} の結果を保存しました。")
                st.rerun()


def page_ranking():
    st.title("🏅 ランキング")

    users = list_users()
    if not users:
        st.info("まだ参加者がいません。")
        return

    results = load_results()
    matches = load_schedule()
    match_map = {m["match_id"]: m for m in matches}
    ai_gs, ai_ko, ai_champion = load_ai_prediction()

    rows = []
    per_match_all = {}
    champion_picks = {}

    for u in users:
        data = load_prediction(u)
        preds = data.get("predictions", {})
        total = compute_total_score(preds, results)
        per_match = compute_per_match_scores(preds, results)
        bdata = load_bracket_prediction(u)
        champion_picks[u] = bdata.get("champion")
        rows.append({"参加者": u, "合計ポイント": total, "優勝予想": team_label(bdata.get("champion") or "")})
        per_match_all[u] = per_match

    df = pd.DataFrame(rows).sort_values("合計ポイント", ascending=False).reset_index(drop=True)
    df.index += 1

    def highlight_top3(row):
        idx = row.name
        if idx == 1:
            return ["background-color: gold; font-weight: bold"] * len(row)
        elif idx == 2:
            return ["background-color: silver; font-weight: bold"] * len(row)
        elif idx == 3:
            return ["background-color: #cd7f32; font-weight: bold"] * len(row)
        return [""] * len(row)

    st.dataframe(df.style.apply(highlight_top3, axis=1), use_container_width=True)

    if ai_champion:
        st.caption(f"🤖 AIの優勝予想: {team_label(ai_champion)}")

    st.markdown("---")
    st.subheader("試合別詳細")

    for _, row in df.iterrows():
        u = row["参加者"]
        with st.expander(f"{u} — {row['合計ポイント']}pt"):
            pm = per_match_all[u]
            if not pm:
                st.write("まだ結果のある試合はありません。")
                continue
            detail_rows = []
            for mid, pts in pm.items():
                m = match_map.get(mid, {})
                home = m.get("home", "?")
                away = m.get("away", "?")
                r = results.get(mid, {})
                detail_rows.append({
                    "試合": f"{team_ja(home)} vs {team_ja(away)}",
                    "結果": f"{r.get('home','?')}-{r.get('away','?')}",
                    "ポイント": pts,
                })
            st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)


def page_team_info():
    st.title("📋 チーム情報")

    player_files = sorted(PLAYERS_DIR.glob("*.json"))
    team_codes = [p.stem for p in player_files]

    if not team_codes:
        st.warning("選手データが見つかりません。")
        return

    selected = st.selectbox("チームを選択", team_codes, format_func=team_ja)

    with open(PLAYERS_DIR / f"{selected}.json") as f:
        team_data = json.load(f)

    st.subheader(f"{team_ja(selected)}")
    st.caption(f"グループ: {team_data.get('group', '?')}")

    # ── 選手情報 ──
    players = team_data.get("players", [])
    if players:
        overalls = [p["eafc26"]["overall"] for p in players if p.get("eafc26", {}).get("overall")]
        if overalls:
            st.metric("平均 OVR (EA FC 26)", f"{sum(overalls)/len(overalls):.1f}")

        top5 = sorted(
            [p for p in players if p.get("eafc26", {}).get("overall")],
            key=lambda p: p["eafc26"]["overall"],
            reverse=True,
        )[:5]

        st.subheader("トップ5選手")
        top5_rows = []
        for p in top5:
            e = p.get("eafc26", {})
            top5_rows.append({
                "Pos": p.get("pos", "?"),
                "名前": p.get("name", "?"),
                "OVR": e.get("overall", "?"),
                "PAC": e.get("pace") or "—",
                "SHO": e.get("shooting") or "—",
                "PAS": e.get("passing") or "—",
                "DRI": e.get("dribbling") or "—",
                "DEF": e.get("defending") or "—",
                "PHY": e.get("physicality") or "—",
            })
        st.dataframe(pd.DataFrame(top5_rows), use_container_width=True, hide_index=True)

        with st.expander("全選手を表示"):
            all_rows = []
            for p in sorted(players, key=lambda p: p.get("eafc26", {}).get("overall") or 0, reverse=True):
                e = p.get("eafc26", {})
                all_rows.append({
                    "Pos": p.get("pos", "?"),
                    "名前": p.get("name", "?"),
                    "OVR": e.get("overall") or "—",
                    "クラブ": p.get("club", "?"),
                })
            st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)

    # ── 戦術情報 ──
    st.markdown("---")
    st.subheader("⚽ 戦術プロファイル (StatsBomb分析)")

    tactics = load_tactics_data(selected)
    if tactics:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("主要フォーメーション", tactics.get("primary_formation", "?"))
            st.metric("分析試合数", tactics.get("matches_analyzed", 0))
        with col2:
            formations = tactics.get("formations", {})
            if formations:
                fmt_str = "　".join(
                    f"{k} ({v}試合)"
                    for k, v in sorted(formations.items(), key=lambda x: -x[1])
                )
                st.caption(f"使用フォーメーション:\n{fmt_str}")

        col_s, col_sub = st.columns(2)
        with col_s:
            if tactics.get("top_starters"):
                st.markdown("**先発常連選手**")
                for name in tactics["top_starters"][:11]:
                    st.markdown(f"- {name}")
        with col_sub:
            if tactics.get("top_subs"):
                st.markdown("**途中出場常連**")
                for name in tactics["top_subs"]:
                    st.markdown(f"- {name}")

        matches_hist = tactics.get("matches", [])
        if matches_hist:
            with st.expander("試合履歴 (StatsBomb)"):
                rows = []
                for mh in matches_hist:
                    rows.append({
                        "大会": mh.get("competition", "?"),
                        "対戦相手": mh.get("opponent", "?"),
                        "スコア": mh.get("score", "?"),
                        "フォーメーション": mh.get("formation", "?"),
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.info("この国の戦術データがありません（StatsBombの対象大会に出場していない可能性があります）。")

    # ── 詳細分析レポート ──
    report_path = ANALYSIS_DIR / f"{selected}.md"
    if report_path.exists():
        st.markdown("---")
        with st.expander("📄 詳細分析レポート (AI生成)"):
            with open(report_path) as f:
                st.markdown(f.read())


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="WC2026 予測アプリ",
        page_icon="🏆",
        layout="wide",
    )

    # Gate: show only login screen until user identifies themselves
    if "username" not in st.session_state:
        page_login()
        return

    username = st.session_state["username"]

    # One-time welcome banner after login
    welcome_msg = st.session_state.pop("welcome_msg", None)
    if welcome_msg:
        st.sidebar.success(welcome_msg)

    st.sidebar.title(f"👤 {username}")
    if st.sidebar.button("← 名前を変える"):
        del st.session_state["username"]
        st.rerun()

    st.sidebar.markdown("---")

    pages = {
        "⚽ 予測入力": page_predict,
        "🗓️ トーナメント予測": page_bracket,
        "🏅 ランキング": page_ranking,
        "📋 チーム情報": page_team_info,
        "🔐 結果入力": page_admin,
    }

    selection = st.sidebar.radio("ページを選択", list(pages.keys()))
    pages[selection]()


if __name__ == "__main__":
    main()
