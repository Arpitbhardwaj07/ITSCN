"""Run repeatable localhost UDP trials and save the experiment CSV files."""

import argparse
import csv
import json
from pathlib import Path
import socket
import threading
import time

from csma_sim import simulate, write_csv as write_csma_csv
from linkstate_sim import LinkStateNetwork
from lossy_link import LossyUDPProxy
from rsu_controller import PacketStats


RESULTS = Path(__file__).resolve().parent / "results"
LOSSES = (0.0, 0.05, 0.10, 0.20)
VEHICLE_COUNTS = (1, 5, 10)


def udp_trial(loss: float, vehicles: int, packets: int, trial: int) -> dict:
    controller_port = 52000 + (trial % 500) * 2
    proxy_port = controller_port + 1
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.4", controller_port))
    receiver.settimeout(0.05)
    stop = threading.Event()
    stats = PacketStats()

    def receive() -> None:
        while not stop.is_set():
            try:
                payload, _ = receiver.recvfrom(4096)
                stats.add(payload)
            except socket.timeout:
                continue
            except OSError:
                break

    receiver_thread = threading.Thread(target=receive, daemon=True)
    receiver_thread.start()
    proxy = LossyUDPProxy("127.0.0.3", proxy_port, "127.0.0.4", controller_port,
                          loss=loss, delay_ms=1.5, jitter_ms=0.5, seed=trial)
    proxy.start()
    sent = 0
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.bind(("127.0.0.2", 0))
            for sequence in range(1, packets + 1):
                for vehicle in range(1, vehicles + 1):
                    message = {
                        "vehicle_id": f"car-{vehicle}", "speed": 35.0,
                        "position": [vehicle, sequence], "direction": "N",
                        "seq": sequence, "send_time": time.time(),
                    }
                    sender.sendto(json.dumps(message).encode(),
                                  ("127.0.0.3", proxy_port))
                    sent += 1
                    time.sleep(0.001)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            seen_by_proxy, _, _, pending = proxy.counts()
            if seen_by_proxy >= sent and pending == 0:
                break
            time.sleep(0.01)
        time.sleep(0.03)
    finally:
        proxy.stop()
        stop.set()
        receiver.close()
        receiver_thread.join(timeout=1.0)
    return stats.summary(packets, vehicles)


def route_measurements() -> tuple[float, float, float]:
    network = LinkStateNetwork()
    before = network.shortest_path("R1", "MON")[1]
    recovery = network.fail_link("R1", "R2")
    after = network.shortest_path("R1", "MON")[1]
    return before, after, recovery


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=5, help="minimum is five per setting")
    parser.add_argument("--packets", type=int, default=12, help="updates per vehicle per trial")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    if args.trials < 5 or args.packets < 1:
        parser.error("--trials must be at least 5 and --packets must be positive")

    RESULTS.mkdir(parents=True, exist_ok=True)
    fields = ["loss_probability", "vehicles", "trial", "scenario", "avg_delay_ms",
              "pdr", "loss_ratio", "route_recovery_time_ms",
              "report_delay_before_ms", "report_delay_after_ms"]
    rows = []
    trial_id = 0
    for loss in LOSSES:
        for vehicles in VEHICLE_COUNTS:
            for repetition in range(1, args.trials + 1):
                trial_id += 1
                metrics = udp_trial(loss, vehicles, args.packets, args.seed + trial_id)
                before, after, recovery = route_measurements()
                common = {
                    "loss_probability": loss, "vehicles": vehicles, "trial": repetition,
                    "avg_delay_ms": round(metrics["delay_ms"], 4),
                    "pdr": round(metrics["pdr"], 6),
                    "loss_ratio": round(metrics["loss_ratio"], 6),
                    "report_delay_before_ms": round(before, 2),
                }
                rows.append({**common, "scenario": "normal", "route_recovery_time_ms": 0.0,
                             "report_delay_after_ms": round(before, 2)})
                rows.append({**common, "scenario": "link_failure",
                             "route_recovery_time_ms": round(recovery, 6),
                             "report_delay_after_ms": round(after, 2)})
                print(f"loss={loss:.0%} vehicles={vehicles:2} trial={repetition} "
                      f"delay={metrics['delay_ms']:.2f} ms PDR={metrics['pdr']:.1%}")

    with (RESULTS / "experiments.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    csma_rows = simulate()
    write_csma_csv(csma_rows, RESULTS / "csma.csv")
    print(f"Saved {len(rows)} scenario rows to {RESULTS / 'experiments.csv'}")
    print(f"Saved {len(csma_rows)} CSMA/ALOHA rows to {RESULTS / 'csma.csv'}")


if __name__ == "__main__":
    main()
