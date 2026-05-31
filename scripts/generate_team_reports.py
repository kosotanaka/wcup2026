"""
各国の選手データ(EAFC26) + 戦術データ(StatsBomb) を統合し、
analysis/teams/{CODE}.md に詳細分析レポートを生成する。
"""

import json
from pathlib import Path
from collections import Counter

PLAYERS_DIR = Path("data/players")

# チーム固有の注記（最新情報・負傷・特記事項）
TEAM_NOTES = {
    "JPN": [
        "三笘薫（OVR 82、Brighton）は負傷により今大会の代表から外れており、本データには未収録。WBの攻撃力に影響。",
        "鈴木彩艶（GK）はOVR 74ながらPOT **82** と伸びしろが大きく、今大会での成長が期待される。",
        "冨安健洋は長期負傷明けのためEAFC26未収録。コンディション次第では主力復帰の可能性あり。",
        "長友佑都（FC東京）はJリーグ所属のためEAFC26未収録。経験値は高いが年齢的にサブ起用が主体。",
        "久保建英はPOT **86** と将来性が高く、本大会が真のブレイクスルーになる可能性を持つ。",
    ],
}
TACTICS_DIR = Path("data/tactics")
OUT_DIR = Path("analysis/teams")
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open("data/groups/group_assignments.json") as f:
    raw = json.load(f)
GROUPS = raw["groups"]  # {"A": [{"name":..,"code":..}, ...], ...}

CODE_TO_GROUP = {}
for grp, teams in GROUPS.items():
    for t in teams:
        CODE_TO_GROUP[t["code"]] = grp

POS_ORDER = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}
POS_JP = {"GK": "GK", "DF": "DF", "MF": "MF", "FW": "FW"}

FORMATION_DESC = {
    "4-2-3-1": "守備的MF2枚を軸に、3列目に広さを持つバランス型。サイドアタックと中盤のプレス強度が高い。",
    "4-3-3":   "3トップで幅を使う攻撃的布陣。ウイングの突破力とボール保持率が鍵。",
    "4-4-2":   "縦2トップにコンパクトな2ラインを形成。ブロック守備とカウンターを軸とする。",
    "3-4-3":   "3バックで後方を固めつつWBが前後にダイナミックに動く。幅と深さを同時に使う攻撃が特徴。",
    "3-4-2-1": "3バックにインサイドハーフが内側に入る流動性の高い布陣。ポゼッション志向が強い。",
    "3-5-2":   "5人の中盤でピッチを制圧。5レーンすべてを使う幅広い攻撃とプレッシング強度が高い。",
    "4-1-2-1-2":"ダブルFWとトップ下を縦に並べた縦志向。ワンツーパスと積極的なプレスで速攻を狙う。",
    "4-5-1":   "5中盤で守備ブロックを構築。FWの孤立したポストプレーからチャンスを作る。",
}

def stars(val, max_val=99, width=10):
    if val is None:
        return "N/A"
    filled = round(val / max_val * width)
    return "█" * filled + "░" * (width - filled) + f" {val}"

def get_ovr_bar(val):
    if val is None:
        return "—"
    if val >= 88:
        tier = "★★★★★"
    elif val >= 84:
        tier = "★★★★☆"
    elif val >= 80:
        tier = "★★★☆☆"
    elif val >= 76:
        tier = "★★☆☆☆"
    else:
        tier = "★☆☆☆☆"
    return f"{tier} {val}"

def build_report(code: str) -> str:
    # --- データ読み込み ---
    pp = PLAYERS_DIR / f"{code}.json"
    if not pp.exists():
        return ""
    with open(pp) as f:
        pdata = json.load(f)

    tp = TACTICS_DIR / f"{code}.json"
    tdata = json.load(open(tp)) if tp.exists() else {}

    players = pdata["players"]
    nation = pdata["name"]
    group = CODE_TO_GROUP.get(code, "?")

    # --- EAFC26 統計 ---
    rated = [p for p in players if p.get("eafc26", {}).get("overall")]
    ovrs = sorted([p["eafc26"]["overall"] for p in rated], reverse=True)
    avg_ovr = round(sum(ovrs) / len(ovrs), 1) if ovrs else None
    top_ovr = ovrs[0] if ovrs else None

    # ポジション別に分ける
    by_pos = {"GK": [], "DF": [], "MF": [], "FW": []}
    for p in players:
        pos = p.get("pos", "MF")
        if pos not in by_pos:
            pos = "MF"
        by_pos[pos].append(p)

    # キープレーヤー (OVR上位5名)
    key_players = sorted(rated, key=lambda p: p["eafc26"]["overall"], reverse=True)[:5]

    # --- 戦術データ ---
    primary_form = tdata.get("primary_formation")
    formations = tdata.get("formations", {})
    matches_analyzed = tdata.get("matches_analyzed", 0)
    top_starters = tdata.get("top_starters", [])[:11]
    top_subs = tdata.get("top_subs", [])[:6]
    match_records = tdata.get("matches", [])

    # --- 有利/不利の戦術的判断 ---
    advantages, disadvantages = build_tactical_analysis(
        code, primary_form, avg_ovr, by_pos, rated
    )

    # ===== Markdown 生成 =====
    lines = []
    lines.append(f"# {nation} ({code}) — チーム分析レポート")
    lines.append(f"")
    lines.append(f"> **グループ {group}** ｜ 主戦フォーメーション: `{primary_form or '不明'}`"
                 f" ｜ 平均OVR: **{avg_ovr}** ｜ 分析試合数: {matches_analyzed}試合 (StatsBomb)")
    lines.append("")

    # --- 1. 選手層 ---
    lines.append("---")
    lines.append("## 1. 選手層")
    lines.append("")

    for pos in ["GK", "DF", "MF", "FW"]:
        group_players = sorted(
            by_pos[pos],
            key=lambda p: p.get("eafc26", {}).get("overall", 0),
            reverse=True
        )
        if not group_players:
            continue
        label = {"GK": "ゴールキーパー", "DF": "ディフェンダー",
                 "MF": "ミッドフィールダー", "FW": "フォワード"}[pos]
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| 選手名 | クラブ | OVR | POT | ↑ | PAC | SHO | PAS | DRI | DEF | PHY |")
        lines.append("|--------|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
        for p in group_players:
            e = p.get("eafc26", {})
            ovr = e.get("overall")
            pot = e.get("potential")
            ovr_str = f"**{ovr}**" if ovr else "—"
            pot_str = str(pot) if pot else "—"
            gap = (pot - ovr) if (pot and ovr) else None
            gap_str = f"+{gap}" if gap and gap > 0 else ("—" if not gap else "")
            captain = " 🅲" if p.get("captain") else ""
            row = (f"| {p['name']}{captain} | {p.get('club','—')} "
                   f"| {ovr_str} "
                   f"| {pot_str} "
                   f"| {gap_str} "
                   f"| {e.get('pace') or '—'} "
                   f"| {e.get('shooting') or '—'} "
                   f"| {e.get('passing') or '—'} "
                   f"| {e.get('dribbling') or '—'} "
                   f"| {e.get('defending') or '—'} "
                   f"| {e.get('physicality') or '—'} |")
            lines.append(row)
        lines.append("")

    # --- 2. キープレーヤー ---
    lines.append("---")
    lines.append("## 2. キープレーヤー")
    lines.append("")
    for p in key_players:
        e = p.get("eafc26", {})
        ovr = e.get("overall", "?")
        pot = e.get("potential")
        pot_str = f" → POT **{pot}**" if pot and pot != ovr else ""
        lines.append(f"### {p['name']} (OVR {ovr}{pot_str})")
        lines.append(f"- **ポジション**: {p.get('pos','?')}  |  **クラブ**: {p.get('club','?')}")
        lines.append(f"- **年齢**: {calc_age(p.get('dob',''))}  |  **代表キャップ**: {p.get('caps','?')}  |  **代表得点**: {p.get('goals','?')}")
        lines.append(f"- **能力値**: PAC {e.get('pace','—')} / SHO {e.get('shooting','—')} / PAS {e.get('passing','—')} / DRI {e.get('dribbling','—')} / DEF {e.get('defending','—')} / PHY {e.get('physicality','—')}")
        lines.append("")

    # --- 3. 戦術的特徴 ---
    lines.append("---")
    lines.append("## 3. 戦術的特徴")
    lines.append("")

    if primary_form:
        desc = FORMATION_DESC.get(primary_form, "")
        lines.append(f"### 主フォーメーション: {primary_form}")
        if desc:
            lines.append(f"> {desc}")
        lines.append("")
        if formations:
            lines.append("**使用フォーメーション分布:**")
            for f_name, cnt in sorted(formations.items(), key=lambda x: -x[1]):
                lines.append(f"- `{f_name}` : {cnt}回")
            lines.append("")
    else:
        lines.append("_StatsBombデータなし。近年の大会に出場歴がないか、データ未収録。_")
        lines.append("")

    if top_starters:
        lines.append("### 主な先発メンバー（StatsBomb実績）")
        lines.append("")
        for name in top_starters:
            lines.append(f"- {name}")
        lines.append("")

    if top_subs:
        lines.append("### よく途中出場する選手")
        lines.append("")
        for name in top_subs:
            lines.append(f"- {name}")
        lines.append("")

    if match_records:
        lines.append("### 近年の主な試合結果")
        lines.append("")
        lines.append("| 大会 | 対戦相手 | スコア | フォーメーション |")
        lines.append("|------|----------|:------:|:---------------:|")
        for m in match_records[-8:]:
            lines.append(f"| {m.get('competition','?')} | {m.get('opponent','?')} | {m.get('score','?')} | {m.get('formation','?')} |")
        lines.append("")

    # --- 4. 有利・不利な状況 ---
    lines.append("---")
    lines.append("## 4. 試合展開の有利・不利")
    lines.append("")
    lines.append("### ✅ 有利になりやすい状況")
    lines.append("")
    for adv in advantages:
        lines.append(f"- {adv}")
    lines.append("")
    lines.append("### ⚠️ 不利になりやすい状況")
    lines.append("")
    for dis in disadvantages:
        lines.append(f"- {dis}")
    lines.append("")

    # --- 5. グループ展望 ---
    lines.append("---")
    lines.append("## 5. グループステージ展望")
    lines.append("")
    grp_teams = GROUPS.get(group, [])
    opponents = [t for t in grp_teams if t["code"] != code]
    lines.append(f"グループ **{group}** の対戦相手: {', '.join(t['name'] for t in opponents)}")
    lines.append("")

    # チーム固有の注記
    notes = TEAM_NOTES.get(code, [])
    if notes:
        lines.append("### 📝 注記・最新情報")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.append("_（予測スコアは schedule.json 入力後に更新予定）_")
    lines.append("")

    return "\n".join(lines)


def calc_age(dob: str) -> str:
    if not dob:
        return "?"
    try:
        from datetime import date
        birth = date.fromisoformat(dob)
        today = date(2026, 6, 1)
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return str(age)
    except Exception:
        return "?"


def build_tactical_analysis(code, formation, avg_ovr, by_pos, rated):
    """フォーメーション・選手層から有利/不利を生成"""
    adv = []
    dis = []

    # OVRベースの強さ判断
    if avg_ovr:
        if avg_ovr >= 82:
            adv.append("選手個人のクオリティが高く、格下相手には個人能力差で試合を支配しやすい")
        elif avg_ovr <= 70:
            dis.append("格上相手との個人能力差は大きく、ブロック守備と組織力で補う必要がある")

    # フォーメーション別の特性
    if formation == "4-2-3-1":
        adv.append("2ボランチによる守備的な安定感があり、ボール奪取後の素早い縦パスでカウンターを発動しやすい")
        adv.append("3列目の横幅を使い、サイドチェンジで相手ブロックをこじ開けることができる")
        dis.append("相手が5バックを敷くと中盤が窮屈になり、ビルドアップが詰まりやすい")
        dis.append("1トップの孤立が起きると前線の起点が失われ、攻撃が停滞する")
    elif formation == "4-3-3":
        adv.append("3トップのプレス強度が高く、相手のビルドアップを高い位置で潰せる")
        adv.append("両ウイングの突破力があれば、サイドを起点に連続してゴールチャンスを作れる")
        dis.append("ウイングが守備に戻らないと、サイドの背後に大きなスペースができ相手SBに使われる")
        dis.append("中盤が1枚少ない構造のため、相手が中盤を厚くしてくると数的不利になりやすい")
    elif formation == "4-4-2":
        adv.append("2ラインのコンパクトなブロックで守備が安定し、ロングカウンターを得意とする")
        adv.append("2トップが前線でタメを作ることで、中盤の飛び出しとの連携が生まれやすい")
        dis.append("ポゼッション型チームに中盤を制圧されると、自陣に押し込まれる展開になりやすい")
        dis.append("4バックと4MFの間のライン間スペースを使われると、崩されやすい")
    elif formation == "3-4-3":
        adv.append("WBが高い位置を取ることでサイドの幅が生まれ、相手を横に引き伸ばして中央にスペースを作れる")
        adv.append("3バックの数的優位でDFラインからのビルドアップが安定し、GKも積極的に絡める")
        dis.append("相手が3トップで WBの裏を狙うと、3バックが数的同数になりCBが孤立しやすい")
        dis.append("WBの運動量が落ちた終盤、サイドのカバーが手薄になる")
    elif formation == "3-4-2-1":
        adv.append("インサイドハーフが内側に入ることで中盤の三角形が複数でき、狭いスペースでのパス回しに強い")
        adv.append("ボール保持率を高める設計で、相手の守備ブロックを動かし続けることができる")
        dis.append("縦に速いカウンターを仕掛けてくる相手には、守備トランジションが遅く危険")
        dis.append("WBへのロングボールで簡単にサイドを変えられると、ポジションバランスが崩れやすい")
    elif formation == "3-5-2":
        adv.append("5中盤でピッチ全幅をカバーし、どの位置でもボールを奪いやすい")
        adv.append("2CFが競り合いに強ければ、前線でタメを作りつつ中盤の飛び出しを引き出せる")
        dis.append("相手の3バックに対し、2トップの枚数が足りず前線プレスが機能しない場面がある")
        dis.append("サイドに引っ張り出されると、DF3枚の横スライドに限界が生じる")
    elif formation == "4-1-2-1-2":
        adv.append("1ボランチを軸に前後左右へのサポートが速く、素早いパス交換でプレスを回避できる")
        adv.append("2トップのコンビネーションがはまると、ペナルティエリア内での崩しが鋭い")
        dis.append("アンカー脇のスペースを突かれると中盤がこじ開けられ、DF裏への一発が通りやすい")
        dis.append("両SBが攻撃参加した際のサイドカバーが薄くなり、失点リスクが高まる")
    else:
        adv.append("組織的な守備ブロックから相手の隙をついたカウンターが有効")
        dis.append("格上相手のポゼッションサッカーに対し、自陣深くに押し込まれやすい")

    # 選手層特性
    gk_ovrs = [p.get("eafc26", {}).get("overall", 0) for p in by_pos["GK"] if p.get("eafc26")]
    df_ovrs = [p.get("eafc26", {}).get("overall", 0) for p in by_pos["DF"] if p.get("eafc26")]
    mf_ovrs = [p.get("eafc26", {}).get("overall", 0) for p in by_pos["MF"] if p.get("eafc26")]
    fw_ovrs = [p.get("eafc26", {}).get("overall", 0) for p in by_pos["FW"] if p.get("eafc26")]

    if gk_ovrs and max(gk_ovrs) >= 85:
        adv.append(f"GK陣のクオリティが高く（最高OVR {max(gk_ovrs)}）、セービングでチームを救える場面が多い")
    if df_ovrs and sum(df_ovrs)/len(df_ovrs) >= 82:
        adv.append("DF陣の平均値が高く、空中戦・対人守備ともに信頼できる")
    if fw_ovrs and max(fw_ovrs) >= 87:
        adv.append(f"FW陣に個人打開できる選手（最高OVR {max(fw_ovrs)}）がおり、1対1でも差を作れる")

    if df_ovrs and sum(df_ovrs)/len(df_ovrs) < 72:
        dis.append("DF陣の能力値が低めで、スピードのある相手FWに裏を取られる危険性がある")
    if gk_ovrs and max(gk_ovrs) < 75:
        dis.append("GKのクオリティに不安があり、ミドルシュートやセットプレーで失点しやすい")

    return adv[:5], dis[:5]


def main():
    all_codes = sorted([p.stem for p in PLAYERS_DIR.glob("*.json")])
    print(f"Generating reports for {len(all_codes)} teams...")

    for code in all_codes:
        md = build_report(code)
        if not md:
            print(f"  [SKIP] {code}")
            continue
        out_path = OUT_DIR / f"{code}.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"  [OK] {code} → {out_path}")

    print(f"\nDone. {len(all_codes)} reports in {OUT_DIR}/")


if __name__ == "__main__":
    main()
