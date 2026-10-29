"""Compare slotted ALOHA and a simple slotted CSMA contention model."""

import argparse
import csv
from pathlib import Path
import random


def simulate(vehicle_counts=range(2, 31), slots: int = 3000,
             attempt_probability: float = 0.1, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for vehicles in vehicle_counts:
        aloha_success = aloha_collisions = aloha_busy = 0
        csma_success = csma_collisions = csma_busy = 0
        for _ in range(slots):
            attempts = [i for i in range(vehicles) if rng.random() < attempt_probability]
            if len(attempts) == 1:
                aloha_success += 1
                aloha_busy += 1
            elif attempts:
                aloha_collisions += 1
                aloha_busy += 1

            # CSMA senses the channel and uses a small random backoff on idle slots.
            contenders = [i for i in range(vehicles) if rng.random() < attempt_probability]
            if contenders:
                csma_busy += 1
                backoffs = {node: rng.randint(0, 3) for node in contenders}
                earliest = min(backoffs.values())
                winners = [node for node, delay in backoffs.items() if delay == earliest]
                if len(winners) == 1:
                    csma_success += 1
                else:
                    csma_collisions += 1
        rows.append({
            "vehicles": vehicles,
            "aloha_collision_rate": aloha_collisions / aloha_busy if aloha_busy else 0.0,
            "aloha_throughput": aloha_success / slots,
            "csma_collision_rate": csma_collisions / csma_busy if csma_busy else 0.0,
            "csma_throughput": csma_success / slots,
        })
    return rows


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slots", type=int, default=3000)
    args = parser.parse_args()
    rows = simulate(slots=args.slots)
    output = Path(__file__).resolve().parent / "results" / "csma.csv"
    write_csv(rows, output)
    print("Vehicles | ALOHA collision | ALOHA throughput | CSMA collision | CSMA throughput")
    for row in rows:
        print(f"{row['vehicles']:8} | {row['aloha_collision_rate']:15.1%} | "
              f"{row['aloha_throughput']:16.3f} | {row['csma_collision_rate']:14.1%} | "
              f"{row['csma_throughput']:15.3f}")
    print(f"Saved {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
