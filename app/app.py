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
    return sorted([p.stem for p in PREDICTIONS_DIR.glob("*.json")])


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
        "③ 予測入力": page_predict,
        "④ 結果入力": page_admin,
        "⑤ ランキング": page_ranking,
        "⑥ チーム情報": page_team_info,
    }

    st.sidebar.title("📍 ナビゲーション")
    selection = st.sidebar.radio("ページを選択", list(pages.keys()))
    pages[selection]()


if __name__ == "__main__":
    main()
