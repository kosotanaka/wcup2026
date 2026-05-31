import json
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).parent.parent
console = Console()

sys.path.insert(0, str(Path(__file__).parent))
from calc_standings import load_matches, compute_standings


def select_best_third_place(standings: dict[str, list[dict]], n: int = 8) -> list[dict]:
    thirds = []
    for g, teams in standings.items():
        if len(teams) >= 3:
            t = dict(teams[2])
            t["group"] = g
            thirds.append(t)

    thirds.sort(key=lambda t: (-t["Pts"], -(t["GF"] - t["GA"]), -t["GF"], t["group"]))
    return thirds[:n]


def print_third_place(selected: list[dict]) -> None:
    table = Table(title=f"Best Third-Place Teams (Top {len(selected)})", header_style="bold magenta")
    for col in ["Rank", "Group", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]:
        table.add_column(col, justify="right" if col not in ("Group", "Team") else "left")
    for rank, t in enumerate(selected, 1):
        table.add_row(str(rank), t["group"], t["team"], str(t["P"]), str(t["W"]), str(t["D"]),
                      str(t["L"]), str(t["GF"]), str(t["GA"]), str(t["GF"] - t["GA"]), str(t["Pts"]))
    console.print(table)


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "prediction"
    matches = load_matches(source)
    if not matches:
        console.print("[yellow]No scored matches found.[/yellow]")
        sys.exit(0)
    standings = compute_standings(matches)
    selected = select_best_third_place(standings, n=8)
    print_third_place(selected)
    console.print("\n[bold]Qualified third-place teams:[/bold]")
    for t in selected:
        console.print(f"  Group {t['group']}: {t['team']} ({t['Pts']} pts)")
