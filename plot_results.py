"""Create the four requested experiment plots from the generated CSV files."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path(__file__).resolve().parent / "results")
    args = parser.parse_args()
    experiment_file, csma_file = args.results / "experiments.csv", args.results / "csma.csv"
    if not experiment_file.exists() or not csma_file.exists():
        parser.error("missing CSVs; run run_experiments.py first")
    rows = read_rows(experiment_file)
    normal = [row for row in rows if row["scenario"] == "normal"]
    losses = sorted({float(row["loss_probability"]) for row in normal})
    vehicle_counts = sorted({int(row["vehicles"]) for row in normal})

    fig, axis = plt.subplots(figsize=(7, 4.5))
    for vehicles in vehicle_counts:
        averages = [mean([float(r["avg_delay_ms"]) for r in normal
                          if int(r["vehicles"]) == vehicles
                          and float(r["loss_probability"]) == loss]) for loss in losses]
        axis.plot([loss * 100 for loss in losses], averages, marker="o", label=f"{vehicles} vehicles")
    axis.set(title="UDP average delay vs configured packet loss", xlabel="Configured loss (%)",
             ylabel="Average one-way delay (ms)")
    axis.grid(True, alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(args.results / "delay_vs_loss.png", dpi=160)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(7, 4.5))
    for vehicles in vehicle_counts:
        averages = [mean([float(r["pdr"]) for r in normal
                          if int(r["vehicles"]) == vehicles
                          and float(r["loss_probability"]) == loss]) for loss in losses]
        axis.plot([loss * 100 for loss in losses], [value * 100 for value in averages],
                  marker="o", label=f"{vehicles} vehicles")
    axis.set(title="Packet delivery ratio vs configured packet loss", xlabel="Configured loss (%)",
             ylabel="PDR (%)", ylim=(0, 105))
    axis.grid(True, alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(args.results / "pdr_vs_loss.png", dpi=160)
    plt.close(fig)

    csma = read_rows(csma_file)
    counts = [int(row["vehicles"]) for row in csma]
    fig, (throughput, collision) = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
    throughput.plot(counts, [float(r["aloha_throughput"]) for r in csma], label="Slotted ALOHA")
    throughput.plot(counts, [float(r["csma_throughput"]) for r in csma], label="CSMA")
    throughput.set(ylabel="Successful packets / slot", title="Slotted ALOHA vs CSMA")
    throughput.legend()
    collision.plot(counts, [float(r["aloha_collision_rate"]) * 100 for r in csma], label="Slotted ALOHA")
    collision.plot(counts, [float(r["csma_collision_rate"]) * 100 for r in csma], label="CSMA")
    collision.set(xlabel="Vehicles contending for one RSU channel", ylabel="Collision rate (%)")
    collision.legend()
    for axis in (throughput, collision):
        axis.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.results / "csma_vs_aloha.png", dpi=160)
    plt.close(fig)

    failed = [row for row in rows if row["scenario"] == "link_failure"]
    before = mean([float(row["report_delay_before_ms"]) for row in failed])
    after = mean([float(row["report_delay_after_ms"]) for row in failed])
    fig, axis = plt.subplots(figsize=(6, 4.5))
    axis.bar(["Before link failure", "After link failure"], [before, after],
             color=["#4c78a8", "#f58518"])
    axis.set(title="Modeled TCP report path delay", ylabel="Shortest-path cost (ms)")
    axis.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.results / "report_delay_link_failure.png", dpi=160)
    plt.close(fig)
    print("Created delay_vs_loss.png, pdr_vs_loss.png, csma_vs_aloha.png, "
          "report_delay_link_failure.png")


if __name__ == "__main__":
    main()
