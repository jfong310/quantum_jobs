from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def get_run_dates(db_path: str) -> set[str]:
    """Fetch all unique dates where the collector successfully ran."""
    if not Path(db_path).exists():
        return set()

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT DISTINCT pulled_date FROM job_snapshots").fetchall()
        return {r[0] for r in rows if r[0]}
    finally:
        conn.close()

def generate_run_history_heatmap(db_path: str, output_path: str, days: int = 90):
    """
    Generates a visual calendar heatmap showing runs over the last N days.
    """
    run_dates = get_run_dates(db_path)

    today = datetime.now().date()
    start_date = today - timedelta(days=days-1)

    # Create a range of dates
    date_range = [start_date + timedelta(days=i) for i in range(days)]

    # Prepare data for heatmap
    # We want a grid: Weeks (columns) x Days of week (rows)
    # 0 = Monday, 6 = Sunday

    # Adjust start_date to the beginning of that week (Monday)
    plot_start = start_date - timedelta(days=start_date.weekday())
    plot_end = today + timedelta(days=(6 - today.weekday()))

    num_days = (plot_end - plot_start).days + 1
    num_weeks = num_days // 7

    data = np.zeros((7, num_weeks))

    current = plot_start
    for w in range(num_weeks):
        for d in range(7):
            date_str = current.strftime("%Y-%m-%d")
            if date_str in run_dates:
                data[d, w] = 1
            elif current > today or current < start_date:
                data[d, w] = -1 # Out of range
            else:
                data[d, w] = 0 # No run
            current += timedelta(days=1)

    fig, ax = plt.subplots(figsize=(12, 3))

    cmap = mcolors.ListedColormap(['#eeeeee', '#ffffff', '#2ea44f']) # Out of range, Empty, Run
    bounds = [-1.5, -0.5, 0.5, 1.5]
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    im = ax.imshow(data, cmap=cmap, norm=norm, aspect='equal')

    # Add grid lines by showing minor ticks and drawing grid
    ax.set_xticks(np.arange(-.5, num_weeks, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 7, 1), minor=True)
    ax.grid(which='minor', color='white', linestyle='-', linewidth=2)

    # Labels
    ax.set_yticks(range(7))
    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])

    # X-axis labels (Months)
    month_labels = []
    current = plot_start
    for w in range(num_weeks):
        # If the month changes during this week, or this is the first week of a month
        if current.day <= 7 or (current + timedelta(days=6)).month != current.month:
            # But only label if we haven't labeled this month yet
            m_name = (current + timedelta(days=6) if current.day > 7 else current).strftime("%b")
            if not month_labels or month_labels[-1][1] != m_name:
                month_labels.append((w, m_name))
        current += timedelta(days=7)

    ax.set_xticks([m[0] for m in month_labels])
    ax.set_xticklabels([m[1] for m in month_labels])

    ax.set_title(f"Collector Run History (Last {days} days)")

    # Remove spines
    for edge, spine in ax.spines.items():
        spine.set_visible(False)

    ax.tick_params(which='both', length=0)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Run history visualization saved to: {output_path}")

def print_console_heatmap(db_path: str, weeks: int = 4):
    """
    Prints a compact Unicode heatmap of runs to the console.
    """
    run_dates = get_run_dates(db_path)
    today = datetime.now().date()

    # Start on a Monday
    start_date = today - timedelta(days=today.weekday() + (weeks - 1) * 7)

    print(f"\nRun History ({weeks} weeks):")
    print("      M T W T F S S")

    current = start_date
    for w in range(weeks):
        week_str = current.strftime("%b %d").ljust(6)
        line = [week_str]
        for d in range(7):
            date_str = current.strftime("%Y-%m-%d")
            if date_str in run_dates:
                line.append("█") # Run
            elif current > today:
                line.append(" ") # Future
            else:
                line.append("░") # Gap
            current += timedelta(days=1)
        print(" ".join(line))
    print("Legend: █ Run | ░ Gap\n")

if __name__ == "__main__":
    from .db.paths import DB_PATH
    generate_run_history_heatmap(str(DB_PATH), "run_history.png")
