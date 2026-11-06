"""Draw Figure 5 from results/orchestration.json. Needs matplotlib, an authoring-only tool."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "results/orchestration.json").read_text(encoding="utf-8"))["escalation"]
STYLE = {
    "elin": ("#2a78d6", "o", "Elin, innkeeper"),
    "iona": ("#eb6834", "s", "Iona, registrar"),
    "mira": ("#1baf7a", "^", "Mira, smith"),
    "daren": ("#eda100", "D", "Daren, guard"),
}
INK, MUTED = "#1f3a56", "#6b7280"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10})
fig, ax = plt.subplots(figsize=(5.0, 1.9), dpi=500)
ax.axhline(80, color=MUTED, linewidth=0.8, linestyle=(0, (4, 3)))
ax.text(6.3, 80, "Disengage threshold", color=MUTED, va="center", fontsize=8.5)
for name, (colour, marker, label) in STYLE.items():
    turns = [t for t in data[name]["turns"] if t["turn"] <= data[name]["disengaged_at"]]  # Conversation over after this.
    x = [0] + [t["turn"] for t in turns]
    y = [data[name]["start_irritation"]] + [t["irritation"] for t in turns]
    ax.plot(x, y, color=colour, linewidth=1.6, marker=marker, markersize=4.5, markeredgecolor="white", markeredgewidth=0.5,
            label=f"{label}, patience {data[name]['patience']:.2f}", clip_on=False)
ax.set_xlim(0, 6.2)
ax.set_ylim(0, 100)
ax.set_xlabel("Repeated insults", color=INK)
ax.set_ylabel("NPC irritation", color=INK)
ax.grid(axis="y", color="#e5e7eb", linewidth=0.6)
ax.set_axisbelow(True)
ax.tick_params(colors=INK, length=2)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color(MUTED)
ax.legend(frameon=False, fontsize=8.5, loc="center left", bbox_to_anchor=(1.01, 0.42), labelcolor=INK)
fig.savefig(HERE.parent / "figures/escalation.png", bbox_inches="tight", facecolor="white")
