import json
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).parent.parent
console = Console()


def load_matches(source: str = "prediction") -> list[dict]:
    path = ROOT / "data" / "matches" / "schedule.json"
    with open(path) as f:
        data = json.load(f)
    matches = []
    for m in data["group_stage"]:
        score = m["prediction"] if source == "prediction" else m["result"]
        if score["home_score"] is not None and score["away_score"] is not None:
            matches.append({
                "group": m["group"],
                "home": m["home"],
                "away": m["away"],
                "home_score": score["home_score"],
                "away_score": score["away_score"],
            })
    return matches


def compute_standings(matches: list[dict]) -> dict[str, list[dict]]:
    standings: dict[str, dict[str, dict]] = {}
    for m in matches:
        g = m["group"]
        for team in (m["home"], m["away"]):
            standings.setdefault(g, {}).setdefault(team, {"team": team, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0})

        hs, as_ = m["home_score"], m["away_score"]
        h, a = standings[g][m["home"]], standings[g][m["away"]]
        h["P"] += 1; a["P"] += 1
        h["GF"] += hs; h["GA"] += as_
        a["GF"] += as_; a["GA"] += hs

        if hs > as_:
            h["W"] += 1; h["Pts"] += 3; a["L"] += 1
        elif hs < as_:
            a["W"] += 1; a["Pts"] += 3; h["L"] += 1
        else:
            h["D"] += 1; h["Pts"] += 1; a["D"] += 1; a["Pts"] += 1

    result = {}
    for g, teams in standings.items():
        sorted_teams = sorted(teams.values(), key=lambda t: (-t["Pts"], -(t["GF"] - t["GA"]), -t["GF"]))
        for i, t in enumerate(sorted_teams):
            t["GD"] = t["GF"] - t["GA"]
        result[g] = sorted_teams
    return result


def print_standings(standings: dict[str, list[dict]]) -> None:
    for group in sorted(standings):
        table = Table(title=f"Group {group}", show_header=True, header_style="bold cyan")
        for col in ["#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]:
            table.add_column(col, justify="right" if col != "Team" else "left")
        for rank, t in enumerate(standings[group], 1):
            style = "bold green" if rank <= 2 else ("yellow" if rank == 3 else "")
            table.add_row(str(rank), t["team"], str(t["P"]), str(t["W"]), str(t["D"]), str(t["L"]),
                          str(t["GF"]), str(t["GA"]), str(t["GD"]), str(t["Pts"]), style=style)
        console.print(table)
        console.print()


def get_qualifiers(standings: dict[str, list[dict]]) -> dict[str, list[str]]:
    qualifiers = {}
    for g, teams in standings.items():
        qualifiers[g] = {"top2": [teams[0]["team"], teams[1]["team"]], "third": teams[2] if len(teams) > 2 else None}
    return qualifiers


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "prediction"
    matches = load_matches(source)
    if not matches:
        console.print("[yellow]No scored matches found. Add predictions or results to schedule.json.[/yellow]")
        sys.exit(0)
    standings = compute_standings(matches)
    print_standings(standings)
    qualifiers = get_qualifiers(standings)
    console.print("[bold]Top 2 qualifiers per group:[/bold]")
    for g in sorted(qualifiers):
        console.print(f"  Group {g}: {qualifiers[g]['top2'][0]}, {qualifiers[g]['top2'][1]}")
