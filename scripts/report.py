import json
import sys
from pathlib import Path
from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel

ROOT = Path(__file__).parent.parent
console = Console()

sys.path.insert(0, str(Path(__file__).parent))
from calc_standings import load_matches, compute_standings, print_standings
from third_place import select_best_third_place
from simulate_knockout import ROUNDS, ROUND_LABELS, load_round


def print_knockout_summary() -> None:
    console.print(Rule("[bold]Knockout Stage[/bold]"))
    found_any = False
    for r in ROUNDS:
        matches = load_round(r)
        if not matches:
            continue
        found_any = True
        console.print(f"\n[bold underline]{ROUND_LABELS[r]}[/bold underline]")
        for m in matches:
            p = m.get("prediction", {})
            hs, as_ = p.get("home_score"), p.get("away_score")
            if hs is not None:
                pen = f" (pen: {p['penalty_winner']})" if p.get("penalty_winner") else ""
                result = f"{hs} - {as_}{pen}"
            else:
                result = "TBD"
            console.print(f"  {m['home']} {result} {m['away']}")
    if not found_any:
        console.print("[yellow]No knockout data found. Run simulate_knockout.py to generate rounds.[/yellow]")


def print_final_ranking() -> None:
    path = ROOT / "predictions" / "final_ranking.md"
    if path.exists():
        console.print(Rule("[bold]Final Ranking Prediction[/bold]"))
        console.print(path.read_text())


def generate_markdown_report(source: str = "prediction") -> None:
    matches = load_matches(source)
    lines = ["# FIFA World Cup 2026 - Prediction Report\n"]

    if matches:
        standings = compute_standings(matches)
        lines.append("## Group Stage Standings\n")
        for g in sorted(standings):
            lines.append(f"### Group {g}\n")
            lines.append("| # | Team | P | W | D | L | GF | GA | GD | Pts |")
            lines.append("|---|------|---|---|---|---|----|----|----|----|")
            for rank, t in enumerate(standings[g], 1):
                lines.append(f"| {rank} | {t['team']} | {t['P']} | {t['W']} | {t['D']} | {t['L']} | {t['GF']} | {t['GA']} | {t['GF']-t['GA']} | {t['Pts']} |")
            lines.append("")

        thirds = select_best_third_place(standings)
        lines.append("## Best Third-Place Teams\n")
        lines.append("| Rank | Group | Team | Pts |")
        lines.append("|------|-------|------|-----|")
        for i, t in enumerate(thirds, 1):
            lines.append(f"| {i} | {t['group']} | {t['team']} | {t['Pts']} |")
        lines.append("")

    lines.append("## Knockout Stage\n")
    for r in ROUNDS:
        ko_matches = load_round(r)
        if not ko_matches:
            continue
        lines.append(f"### {ROUND_LABELS[r]}\n")
        for m in ko_matches:
            p = m.get("prediction", {})
            hs, as_ = p.get("home_score"), p.get("away_score")
            score = f"{hs} - {as_}" if hs is not None else "TBD"
            lines.append(f"- {m['home']} **{score}** {m['away']}")
        lines.append("")

    out_path = ROOT / "predictions" / "report.md"
    out_path.write_text("\n".join(lines))
    console.print(f"[green]Report written to {out_path}[/green]")


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "prediction"
    md_flag = "--md" in sys.argv

    console.print(Panel("[bold cyan]FIFA World Cup 2026 Prediction Report[/bold cyan]", expand=False))

    matches = load_matches(source)
    if matches:
        console.print(Rule("[bold]Group Stage Standings[/bold]"))
        standings = compute_standings(matches)
        print_standings(standings)

        thirds = select_best_third_place(standings)
        console.print(Rule("[bold]Best Third-Place Teams[/bold]"))
        from third_place import print_third_place
        print_third_place(thirds)
    else:
        console.print("[yellow]No scored matches found for group stage.[/yellow]")

    print_knockout_summary()
    print_final_ranking()

    if md_flag:
        generate_markdown_report(source)
