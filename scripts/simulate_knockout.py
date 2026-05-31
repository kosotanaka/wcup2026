import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).parent.parent
KO_DIR = ROOT / "predictions" / "knockout"
console = Console()

ROUNDS = ["round_of_32", "round_of_16", "quarter_finals", "semi_finals", "final"]
ROUND_LABELS = {
    "round_of_32": "Round of 32",
    "round_of_16": "Round of 16",
    "quarter_finals": "Quarter-Finals",
    "semi_finals": "Semi-Finals",
    "final": "Final",
}


def load_round(round_name: str) -> list[dict]:
    path = KO_DIR / f"{round_name}.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_round(round_name: str, matches: list[dict]) -> None:
    KO_DIR.mkdir(parents=True, exist_ok=True)
    path = KO_DIR / f"{round_name}.json"
    with open(path, "w") as f:
        json.dump(matches, f, indent=2)
    console.print(f"[green]Saved {path}[/green]")


def get_winner(match: dict):
    p = match.get("prediction", {})
    if p.get("home_score") is None:
        return None
    hs, as_ = p["home_score"], p["away_score"]
    if hs > as_:
        return match["home"]
    elif as_ > hs:
        return match["away"]
    return p.get("penalty_winner")


def advance_round(current_round: str):
    idx = ROUNDS.index(current_round)
    return ROUNDS[idx + 1] if idx + 1 < len(ROUNDS) else None


def generate_next_round(current_round: str) -> None:
    matches = load_round(current_round)
    if not matches:
        console.print(f"[red]No data for {current_round}[/red]")
        return

    winners = []
    for m in matches:
        w = get_winner(m)
        if w is None:
            console.print(f"[yellow]Match {m.get('match_id')} has no result yet.[/yellow]")
            return
        winners.append(w)

    next_round = advance_round(current_round)
    if next_round is None:
        console.print(f"[bold green]Tournament winner: {winners[0]}[/bold green]")
        return

    next_matches = []
    for i in range(0, len(winners), 2):
        mid = f"{next_round.upper()[:2]}{i // 2 + 1:02d}"
        next_matches.append({
            "match_id": mid,
            "round": next_round,
            "home": winners[i],
            "away": winners[i + 1] if i + 1 < len(winners) else "TBD",
            "date": "TBD",
            "venue": "TBD",
            "prediction": {"home_score": None, "away_score": None, "penalty_winner": None},
        })

    save_round(next_round, next_matches)
    console.print(f"\n[bold]{ROUND_LABELS[next_round]} matchups:[/bold]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Match ID")
    table.add_column("Home")
    table.add_column("Away")
    for m in next_matches:
        table.add_row(m["match_id"], m["home"], m["away"])
    console.print(table)


def show_bracket() -> None:
    for r in ROUNDS:
        matches = load_round(r)
        if not matches:
            continue
        console.print(f"\n[bold underline]{ROUND_LABELS[r]}[/bold underline]")
        for m in matches:
            p = m.get("prediction", {})
            hs, as_ = p.get("home_score"), p.get("away_score")
            score = f"{hs} - {as_}" if hs is not None else "vs"
            console.print(f"  {m['home']} {score} {m['away']}")


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "bracket"
    if cmd == "bracket":
        show_bracket()
    elif cmd in ROUNDS:
        generate_next_round(cmd)
    else:
        console.print(f"Usage: simulate_knockout.py [bracket | {'|'.join(ROUNDS)}]")
