"""
FIFA World Cup 2026 Multi-player Prediction App
"""

import json
import os
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
PREDICTIONS_DIR = DATA / "predictions"
RESULTS_FILE = DATA / "results.json"

PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_PASSWORD = "wcup2026admin"

# ── Flag emoji map ──────────────────────────────────────────────────────────
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


# ── Data helpers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_schedule():
    with open(SCHEDULE_FILE) as f:
        data = json.load(f)
    matches = data.get("group_stage", [])
    return matches


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
    return sorted([p.stem for p in PREDICTIONS_DIR.glob("*.json") if not p.stem.endswith("_bracket")])


def et_to_jst(date_str: str, time_str: str):
    """Convert ET date+time to JST (ET+13h). Returns datetime."""
    dt_str = f"{date_str} {time_str}"
    dt_et = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    dt_jst = dt_et + timedelta(hours=13)
    return dt_jst


def format_jst(dt_jst: datetime) -> str:
    wd = WEEKDAYS_JA[dt_jst.weekday()]
    return dt_jst.strftime(f"%-m/%-d ({wd}) %H:%M JST")


def flag(code: str) -> str:
    return FLAGS.get(code, "🏳")


def match_has_result(match_id: str, results: dict) -> bool:
    r = results.get(match_id, {})
    return r.get("home") is not None and r.get("away") is not None


def is_knockout(match_id: str) -> bool:
    return not match_id.startswith("GS")


# ── Pages ───────────────────────────────────────────────────────────────────

def page_home():
    st.title("🏆 FIFA ワールドカップ 2026 予測アプリ")
    st.markdown("---")

    st.subheader("現在のフェーズ")
    st.info("🟢 グループステージ進行中")

    st.subheader("次の試合まで")
    matches = load_schedule()
    results = load_results()
    now_jst = datetime.utcnow() + timedelta(hours=9)

    upcoming = []
    for m in matches:
        if not match_has_result(m["match_id"], results):
            dt_jst = et_to_jst(m["date"], m["time_et"])
            if dt_jst > now_jst:
                upcoming.append((dt_jst, m))

    if upcoming:
        upcoming.sort(key=lambda x: x[0])
        next_dt, next_match = upcoming[0]
        delta = next_dt - now_jst
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes = rem // 60
        st.metric(
            label=f"{flag(next_match['home'])} {next_match['home']}  vs  {flag(next_match['away'])} {next_match['away']}",
            value=format_jst(next_dt),
            delta=f"あと {hours}時間 {minutes}分",
        )
    else:
        st.write("未来の試合情報がありません。")

    st.markdown("---")
    st.markdown(
        "**ナビゲーション**: 左のサイドバーからページを選択してください。\n\n"
        "- 参加者登録 → 名前を登録\n"
        "- 予測入力 → スコアを予測\n"
        "- ランキング → 順位を確認\n"
        "- チーム情報 → 各チームの選手情報"
    )


def page_register():
    st.title("👤 参加者登録")
    st.markdown("名前を入力して参加登録してください。")

    name = st.text_input("ニックネーム（英数字・日本語可）", max_chars=30)
    if st.button("登録する"):
        name = name.strip()
        if not name:
            st.error("名前を入力してください。")
        else:
            path = PREDICTIONS_DIR / f"{name}.json"
            if path.exists():
                st.warning(f"「{name}」はすでに登録済みです。")
            else:
                save_prediction(name, {"username": name, "predictions": {}})
                st.success(f"「{name}」を登録しました！予測入力ページへ移動してください。")
                st.session_state["username"] = name


def page_predict():
    st.title("⚽ 予測入力")

    users = list_users()
    if not users:
        st.warning("まず「参加者登録」ページで名前を登録してください。")
        return

    default_idx = 0
    if "username" in st.session_state and st.session_state["username"] in users:
        default_idx = users.index(st.session_state["username"])

    username = st.selectbox("参加者を選択", users, index=default_idx)
    st.session_state["username"] = username

    user_data = load_prediction(username)
    preds = user_data.get("predictions", {})
    matches = load_schedule()
    results = load_results()

    # Sort matches by JST datetime
    def sort_key(m):
        return et_to_jst(m["date"], m["time_et"])

    matches_sorted = sorted(matches, key=sort_key)

    # Group by JST date
    from itertools import groupby
    def jst_date_str(m):
        dt = et_to_jst(m["date"], m["time_et"])
        wd = WEEKDAYS_JA[dt.weekday()]
        return dt.strftime(f"%-m月%-d日 ({wd})")

    st.markdown("---")
    changed = {}

    current_date = None
    for m in matches_sorted:
        date_label = jst_date_str(m)
        if date_label != current_date:
            current_date = date_label
            st.subheader(f"📅 {date_label}")

        mid = m["match_id"]
        home_code = m["home"]
        away_code = m["away"]
        group = m["group"]
        dt_jst = et_to_jst(m["date"], m["time_et"])
        locked = match_has_result(mid, results)

        existing = preds.get(mid, {})
        existing_home = existing.get("home", 0) if existing.get("home") is not None else 0
        existing_away = existing.get("away", 0) if existing.get("away") is not None else 0

        with st.container():
            col_info, col_scores, col_status = st.columns([3, 3, 2])

            with col_info:
                st.markdown(
                    f"**{flag(home_code)} {home_code}** vs **{flag(away_code)} {away_code}**  \n"
                    f"グループ {group}　{format_jst(dt_jst)}"
                )

            with col_scores:
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
                            f"{home_code}", min_value=0, max_value=9,
                            value=existing_home,
                            key=f"h_{mid}",
                            label_visibility="collapsed"
                        )
                    with c2:
                        st.markdown("<div style='text-align:center;padding-top:8px'>vs</div>", unsafe_allow_html=True)
                    with c3:
                        a_val = st.number_input(
                            f"{away_code}", min_value=0, max_value=9,
                            value=existing_away,
                            key=f"a_{mid}",
                            label_visibility="collapsed"
                        )

                    entry = {"home": h_val, "away": a_val}

                    if is_knockout(mid):
                        et_val = st.checkbox("延長戦", value=existing.get("et", False), key=f"et_{mid}")
                        pk_val = st.checkbox("PK戦", value=existing.get("pk", False), key=f"pk_{mid}")
                        entry["et"] = et_val
                        entry["pk"] = pk_val

                    changed[mid] = entry

            with col_status:
                if locked:
                    pts = score_match(mid, existing, results[mid])
                    st.markdown(f"🔒 **{pts}pt**")
                else:
                    st.markdown("✏️ 入力中")

        st.divider()

    if changed:
        if st.button("💾 すべての予測を保存", type="primary"):
            for mid, entry in changed.items():
                if not match_has_result(mid, results):
                    preds[mid] = entry
            user_data["predictions"] = preds
            save_prediction(username, user_data)
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

    # Sort matches
    matches_sorted = sorted(matches, key=lambda m: et_to_jst(m["date"], m["time_et"]))

    st.markdown("---")
    updated = {}

    for m in matches_sorted:
        mid = m["match_id"]
        home_code = m["home"]
        away_code = m["away"]
        dt_jst = et_to_jst(m["date"], m["time_et"])
        existing = results.get(mid, {})

        with st.expander(
            f"{mid} | {flag(home_code)}{home_code} vs {flag(away_code)}{away_code} — {format_jst(dt_jst)}"
            + (" ✅" if match_has_result(mid, results) else ""),
            expanded=not match_has_result(mid, results)
        ):
            c1, c2, c3 = st.columns([2, 1, 2])
            with c1:
                h_val = st.number_input(
                    f"ホーム ({home_code})", min_value=0, max_value=20,
                    value=existing.get("home") or 0,
                    key=f"res_h_{mid}"
                )
            with c2:
                st.markdown("<div style='text-align:center;padding-top:28px'>-</div>", unsafe_allow_html=True)
            with c3:
                a_val = st.number_input(
                    f"アウェイ ({away_code})", min_value=0, max_value=20,
                    value=existing.get("away") or 0,
                    key=f"res_a_{mid}"
                )

            entry = {"home": h_val, "away": a_val}

            if is_knockout(mid):
                et_val = st.checkbox("延長戦あり", value=existing.get("et", False), key=f"res_et_{mid}")
                pk_val = st.checkbox("PK戦あり", value=existing.get("pk", False), key=f"res_pk_{mid}")
                entry["et"] = et_val
                entry["pk"] = pk_val

            updated[mid] = entry

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

    rows = []
    per_match_all = {}
    for u in users:
        data = load_prediction(u)
        preds = data.get("predictions", {})
        total = compute_total_score(preds, results)
        per_match = compute_per_match_scores(preds, results)
        rows.append({"参加者": u, "合計ポイント": total})
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
                    "試合": f"{flag(home)}{home} vs {flag(away)}{away}",
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

    selected = st.selectbox("チームを選択", team_codes, format_func=lambda c: f"{flag(c)} {c}")

    with open(PLAYERS_DIR / f"{selected}.json") as f:
        team_data = json.load(f)

    st.subheader(f"{flag(selected)} {team_data.get('name', selected)}")
    st.caption(f"グループ: {team_data.get('group', '?')}")

    players = team_data.get("players", [])
    if not players:
        st.info("選手データがありません。")
        return

    # Compute avg OVR
    overalls = [p["eafc26"]["overall"] for p in players if p.get("eafc26", {}).get("overall")]
    if overalls:
        avg_ovr = sum(overalls) / len(overalls)
        st.metric("平均 OVR (EA FC 26)", f"{avg_ovr:.1f}")

    # Top 5 by OVR
    top5 = sorted(
        [p for p in players if p.get("eafc26", {}).get("overall")],
        key=lambda p: p["eafc26"]["overall"],
        reverse=True
    )[:5]

    st.subheader("トップ5選手")
    top5_rows = []
    for p in top5:
        eafc = p.get("eafc26", {})
        top5_rows.append({
            "ポジション": p.get("pos", "?"),
            "名前": p.get("name", "?"),
            "OVR": eafc.get("overall", "?"),
        })
    st.dataframe(pd.DataFrame(top5_rows), use_container_width=True, hide_index=True)

    # All players
    with st.expander("全選手を表示"):
        all_rows = []
        for p in players:
            eafc = p.get("eafc26", {})
            all_rows.append({
                "ポジション": p.get("pos", "?"),
                "名前": p.get("name", "?"),
                "OVR": eafc.get("overall", "?"),
                "クラブ": p.get("club", "?"),
            })
        st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)


# ── R32ブラケット定義 ──────────────────────────────────────────────────────────
# 公式FIFA WC2026 R32 固定対戦カード (グループスロット表記)
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

# R16以降のブラケット: (match_id, winner_of_1, winner_of_2, date, time_et)
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
FINAL_SLOT  = ("KO032", "KO029", "KO030", "2026-07-19", "20:00")

ALL_CODES = [
    "MEX","RSA","KOR","CZE","CAN","BIH","QAT","SUI","BRA","MAR","HAI","SCO",
    "USA","PAR","AUS","TUR","GER","CUW","CIV","ECU","NED","JPN","SWE","TUN",
    "BEL","EGY","IRN","NZL","ESP","CPV","KSA","URU","FRA","SEN","IRQ","NOR",
    "ARG","ALG","AUT","JOR","POR","COD","UZB","COL","ENG","CRO","GHA","PAN",
]

# 3rd-place slot assignment order for R32 (position in this list = index into third_qualifiers)
THIRD_SLOT_ORDER = ["KO001", "KO002", "KO007", "KO008", "KO011", "KO012", "KO015", "KO016"]


# ── Bracket helper functions ──────────────────────────────────────────────────

def compute_standings_from_predictions(
    user_preds: dict, schedule_matches: list
) -> dict:
    """
    Compute group standings from the user's group-stage predictions.

    Returns dict mapping group letter -> list of (code, pts, gd, gf) tuples,
    sorted best->worst (pts DESC, gd DESC, gf DESC, with head-to-head tiebreak).
    """
    # initialise per-group team stats
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

        # head-to-head tiebreaker within equal groups
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
    """
    Pick the best 8 third-place teams across all 12 groups.
    Sorted by pts DESC -> gd DESC -> gf DESC.
    Returns list of up to 8 team codes, best first.
    """
    thirds = []
    for grp in sorted(standings.keys()):
        grp_standing = standings[grp]
        if len(grp_standing) >= 3:
            thirds.append(grp_standing[2])  # (code, pts, gd, gf)

    thirds.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    return [t[0] for t in thirds[:8]]


def resolve_ko_slot(
    slot: str,
    standings: dict,
    third_qualifiers: list,
    ko_picks: dict,
) -> str | None:
    """
    Resolve a bracket slot string to a team code.

    Slot formats:
    - "1A"          -> 1st place Group A
    - "2B"          -> 2nd place Group B
    - "3ABCDF"      -> handled externally via third_qualifiers positional assignment
    - "KO001"       -> winner of that KO match
    - "KO029_loser" -> loser of KO029
    """
    if len(slot) == 2 and slot[0] in ("1", "2"):
        rank = int(slot[0]) - 1
        grp = slot[1]
        grp_standing = standings.get(grp, [])
        if len(grp_standing) > rank:
            return grp_standing[rank][0]
        return None

    if slot.startswith("3"):
        return None  # resolved by caller using positional third_qualifiers

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
            # tied at 90min: home wins PK by default, away is loser
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
            # tied at 90min: home wins PK by default
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
    return f"{flag(code)} {code}" if code else "—"


def page_bracket():
    st.title("🗓️ トーナメント事前予測")

    users = list_users()
    if not users:
        st.warning("まず「参加者登録」ページで名前を登録してください。")
        return

    default_idx = 0
    if "username" in st.session_state and st.session_state["username"] in users:
        default_idx = users.index(st.session_state["username"])
    username = st.selectbox("参加者を選択", users, index=default_idx, key="bracket_user")
    st.session_state["username"] = username

    st.info("ℹ️ グループステージの予測を入力すると、自動で対戦カードが決まります")

    # ── Load data ──
    schedule_matches = load_schedule()
    user_data = load_prediction(username)
    user_preds = user_data.get("predictions", {})
    bdata = load_bracket_prediction(username)
    ko_picks = bdata.get("ko_picks", {})

    # ── Compute standings from group-stage predictions ──
    standings = compute_standings_from_predictions(user_preds, schedule_matches)
    third_qualifiers = get_third_place_qualifiers(standings)

    # ── グループ通過チーム（自動計算） ──
    st.markdown("---")
    st.subheader("グループ通過チーム（自動計算）")

    groups_data = load_groups()
    all_groups = sorted(groups_data.keys())

    # Build summary table
    table_rows = []
    for grp in all_groups:
        ranked = standings.get(grp, [])
        first  = ranked[0][0] if len(ranked) > 0 else "—"
        second = ranked[1][0] if len(ranked) > 1 else "—"
        if len(ranked) >= 3:
            third_code, third_pts, third_gd, third_gf = ranked[2]
            third_qualified = third_code in third_qualifiers
            third_str = f"{team_label(third_code)} ({third_pts}pts, GD{third_gd:+d})"
        else:
            third_str = "—"
            third_qualified = False

        table_rows.append({
            "グループ": grp,
            "1位": team_label(first) if first != "—" else "—",
            "2位": team_label(second) if second != "—" else "—",
            "3位 (ポイント/GD)": third_str,
            "3位通過?": "✅" if third_qualified else "",
        })

    if table_rows:
        st.dataframe(
            pd.DataFrame(table_rows),
            use_container_width=True,
            hide_index=True,
        )

        if len(third_qualifiers) < 8:
            remaining = 8 - len(third_qualifiers)
            st.caption(
                f"※ グループステージの予測が不足しています。現在 {len(third_qualifiers)}/8 チームが算出済み。"
                f"あと {remaining} グループの予測が必要です。"
            )
    else:
        st.caption("グループステージの予測を「③ 予測入力」ページで入力すると、ここに自動表示されます。")

    # ── Build R32 team assignments (resolve all slots) ──
    # For 3rd-place slots, assign in THIRD_SLOT_ORDER positional order
    third_slot_assignments: dict[str, str | None] = {}
    for i, ko_mid in enumerate(THIRD_SLOT_ORDER):
        third_slot_assignments[ko_mid] = third_qualifiers[i] if i < len(third_qualifiers) else None

    def get_r32_teams(match_id: str, slot_h: str, slot_a: str) -> tuple:
        """Return (home_code, away_code) for an R32 match."""
        if slot_h.startswith("3"):
            hc = third_slot_assignments.get(match_id)
        else:
            hc = resolve_ko_slot(slot_h, standings, third_qualifiers, ko_picks)
        if slot_a.startswith("3"):
            ac = third_slot_assignments.get(match_id)
            # slot_a is always "3xxx", so use the same match_id key but we need home vs away:
            # For each R32 match that has a 3rd-place slot, it's always the away slot.
            # The home slot is the away position in the 3rd-place dict — but both slots of the
            # same match can't both be 3rd-place.  slot_a for this match_id is different.
            # Re-derive: the "away" 3rd slot is the same positional index as the match_id.
            ac = third_slot_assignments.get(match_id)
        else:
            ac = resolve_ko_slot(slot_a, standings, third_qualifiers, ko_picks)
        return hc, ac

    # Actually, home and away from the same match cannot both be 3rd-place slots.
    # All R32 3rd-place slots are in the away position.  Rewrite cleanly:
    def resolve_r32_slot(slot: str, match_id: str) -> str | None:
        if slot.startswith("3"):
            return third_slot_assignments.get(match_id)
        return resolve_ko_slot(slot, standings, third_qualifiers, ko_picks)

    # ── Helper: render a KO match input row ──
    def ko_match_input(
        match_id: str,
        home_code: str | None,
        away_code: str | None,
        date: str,
        time_et: str,
        round_label: str,
    ):
        dt_jst = et_to_jst(date, time_et)
        existing = ko_picks.get(match_id, {})

        home_disp = team_label(home_code) if home_code else "（未確定）"
        away_disp = team_label(away_code) if away_code else "（未確定）"

        with st.container():
            header_col, _ = st.columns([6, 1])
            with header_col:
                st.markdown(f"**{match_id}** `{round_label}` — {format_jst(dt_jst)}")

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

            # Persist to ko_picks (in-memory, saved on button press)
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

    # ── R32 ──
    with st.expander("🔵 ラウンド32 — 16試合 (6/28〜7/3)", expanded=True):
        for match_id, slot_h, slot_a, date, time_et in R32_SLOTS:
            home_code = resolve_r32_slot(slot_h, match_id)
            away_code = resolve_r32_slot(slot_a, match_id)
            ko_match_input(match_id, home_code, away_code, date, time_et, "R32")

    # ── R16 — teams come from R32 winners ──
    with st.expander("🟡 ラウンド16 — 8試合 (7/5〜7/8)"):
        for match_id, src_h, src_a, date, time_et in R16_SLOTS:
            home_code = resolve_ko_slot(src_h, standings, third_qualifiers, ko_picks)
            away_code = resolve_ko_slot(src_a, standings, third_qualifiers, ko_picks)
            ko_match_input(match_id, home_code, away_code, date, time_et, "R16")

    # ── QF ──
    with st.expander("🟠 準々決勝 — 4試合 (7/11〜7/12)"):
        for match_id, src_h, src_a, date, time_et in QF_SLOTS:
            home_code = resolve_ko_slot(src_h, standings, third_qualifiers, ko_picks)
            away_code = resolve_ko_slot(src_a, standings, third_qualifiers, ko_picks)
            ko_match_input(match_id, home_code, away_code, date, time_et, "QF")

    # ── SF ──
    with st.expander("🔴 準決勝 — 2試合 (7/14〜7/15)"):
        for match_id, src_h, src_a, date, time_et in SF_SLOTS:
            home_code = resolve_ko_slot(src_h, standings, third_qualifiers, ko_picks)
            away_code = resolve_ko_slot(src_a, standings, third_qualifiers, ko_picks)
            ko_match_input(match_id, home_code, away_code, date, time_et, "SF")

    # ── Bronze + Final ──
    with st.expander("🥉🏆 3位決定戦 & 決勝 (7/18〜7/19)"):
        # Bronze: losers of two SF matches
        bronze_home = resolve_ko_slot("KO029_loser", standings, third_qualifiers, ko_picks)
        bronze_away = resolve_ko_slot("KO030_loser", standings, third_qualifiers, ko_picks)
        ko_match_input(BRONZE_SLOT[0], bronze_home, bronze_away, BRONZE_SLOT[3], BRONZE_SLOT[4], "3位決定戦")

        # Final: winners of two SF matches
        final_home = resolve_ko_slot("KO029", standings, third_qualifiers, ko_picks)
        final_away = resolve_ko_slot("KO030", standings, third_qualifiers, ko_picks)
        ko_match_input(FINAL_SLOT[0], final_home, final_away, FINAL_SLOT[3], FINAL_SLOT[4], "決勝")

    # ── 優勝予想 ──
    st.markdown("---")
    st.subheader("🏆 優勝予想")

    # Auto-derive finalists from SF predictions if available
    finalist_home = resolve_ko_slot("KO029", standings, third_qualifiers, ko_picks)
    finalist_away = resolve_ko_slot("KO030", standings, third_qualifiers, ko_picks)

    finalists = [c for c in [finalist_home, finalist_away] if c]
    if finalists:
        st.caption(f"決勝進出予想: {' vs '.join(team_label(c) for c in finalists)}")

    champion_opts = ["（未選択）"] + ALL_CODES
    cur_champ = bdata.get("champion") or "（未選択）"
    if cur_champ not in champion_opts:
        cur_champ = "（未選択）"

    # If exactly one finalist is determinable, pre-select sensibly; otherwise keep saved value
    champion_default_idx = champion_opts.index(cur_champ)

    champion = st.selectbox(
        "優勝すると思うチームは？",
        champion_opts,
        index=champion_default_idx,
        format_func=lambda c: team_label(c) if c != "（未選択）" else "（未選択）",
        key="champion_pick",
    )

    # ── 保存ボタン ──
    st.markdown("---")
    if st.button("💾 保存", type="primary"):
        bdata["ko_picks"] = ko_picks
        if champion != "（未選択）":
            bdata["champion"] = champion
        else:
            bdata["champion"] = None
        save_bracket_prediction(username, bdata)
        st.success("保存しました！")
        st.rerun()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="WC2026 予測アプリ",
        page_icon="🏆",
        layout="wide",
    )

    pages = {
        "① ホーム": page_home,
        "② 参加者登録": page_register,
        "③ 予測入力（試合別）": page_predict,
        "④ トーナメント事前予測": page_bracket,
        "⑤ 結果入力": page_admin,
        "⑥ ランキング": page_ranking,
        "⑦ チーム情報": page_team_info,
    }

    st.sidebar.title("📍 ナビゲーション")
    selection = st.sidebar.radio("ページを選択", list(pages.keys()))
    pages[selection]()


if __name__ == "__main__":
    main()
