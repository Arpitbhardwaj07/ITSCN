"""Receive UDP vehicle updates, summarize delivery, and report to a monitor."""

import argparse
from datetime import datetime
import json
import socket
import time

from linkstate_sim import LinkStateNetwork


class PacketStats:
    """Track unique sequence numbers and receive delays."""

    def __init__(self) -> None:
        self.sequences: dict[str, set[int]] = {}
        self.delays_ms: list[float] = []

    def add(self, payload: bytes) -> tuple[dict, float, bool, bool]:
        message = json.loads(payload.decode("utf-8"))
        vehicle = str(message["vehicle_id"])
        sequence = int(message["seq"])
        received = self.sequences.setdefault(vehicle, set())
        old_max = max(received, default=0)
        is_new = sequence not in received
        gap = sequence > old_max + 1
        received.add(sequence)
        delay_ms = max(0.0, (time.time() - float(message["send_time"])) * 1000)
        if is_new:
            self.delays_ms.append(delay_ms)
        return message, delay_ms, is_new, gap

    def summary(self, expected_per_vehicle: int | None = None,
                vehicle_count: int | None = None) -> dict:
        received = sum(len(sequences) for sequences in self.sequences.values())
        if expected_per_vehicle is None:
            expected = sum(max(sequences, default=0) for sequences in self.sequences.values())
        else:
            expected = expected_per_vehicle * max(vehicle_count or len(self.sequences), 1)
        expected = max(expected, received)
        pdr = received / expected if expected else 0.0
        return {
            "received": received,
            "expected": expected,
            "delay_ms": sum(self.delays_ms) / len(self.delays_ms) if self.delays_ms else 0.0,
            "pdr": pdr,
            "loss_ratio": 1.0 - pdr if expected else 0.0,
        }


def send_report(host: str, port: int, stats: PacketStats, network: LinkStateNetwork,
                expected: int | None, vehicles: int | None) -> tuple[float | None, float]:
    path, route_delay = network.shortest_path("R1", "MON")
    report = stats.summary(expected, vehicles)
    report.update({"route_path": path, "route_delay_ms": route_delay})
    started = time.perf_counter()
    time.sleep(route_delay / 1000.0)  # Apply the simulated link costs to this TCP report.
    try:
        with socket.create_connection((host, port), timeout=3.0) as connection:
            connection.settimeout(3.0)
            with connection.makefile("rwb") as channel:
                channel.write(json.dumps(report).encode("utf-8") + b"\n")
                channel.flush()
                reply = json.loads(channel.readline().decode("utf-8"))
        observed_ms = (time.perf_counter() - started) * 1000
        print(f"TCP report path={' -> '.join(path)} path_delay={route_delay:.2f} ms "
              f"observed_round_trip={observed_ms:.2f} ms")
        interval = reply.get("seconds") if reply.get("command") == "set_report_interval" else None
        return interval, observed_ms
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"TCP monitor report failed: {error}")
        return None, (time.perf_counter() - started) * 1000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.4")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--idle-timeout", type=float, default=2.0)
    parser.add_argument("--expected-per-vehicle", type=int)
    parser.add_argument("--vehicle-count", type=int)
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--monitor-host", default="127.0.0.5")
    parser.add_argument("--monitor-port", type=int, default=6000)
    parser.add_argument("--report-interval", type=float, default=1.0)
    parser.add_argument("--link-failure-after", type=int, default=0,
                        help="fail R1-R2 after this many TCP reports; 0 disables failure")
    args = parser.parse_args()
    stats = PacketStats()
    network = LinkStateNetwork()
    interval = max(args.report_interval, 0.1)
    start = last_packet = time.monotonic()
    next_report = start + interval
    report_count = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind((args.host, args.port))
        receiver.settimeout(0.1)
        print(f"RSU listening on UDP {args.host}:{args.port}")
        while True:
            try:
                payload, _ = receiver.recvfrom(4096)
                last_packet = time.monotonic()
                try:
                    message, delay, is_new, gap = stats.add(payload)
                    if is_new:
                        received_at = datetime.now().isoformat(timespec="milliseconds")
                        print(f"RX time={received_at} {message['vehicle_id']} "
                              f"seq={message['seq']} delay={delay:.2f} ms")
                    if gap:
                        print(f"Sequence gap observed for {message['vehicle_id']} before seq={message['seq']}")
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                    print(f"Ignored malformed UDP update: {error}")
            except socket.timeout:
                pass
            now = time.monotonic()
            if args.monitor and now >= next_report:
                interval_from_monitor, _ = send_report(
                    args.monitor_host, args.monitor_port, stats, network,
                    args.expected_per_vehicle, args.vehicle_count,
                )
                report_count += 1
                if interval_from_monitor is not None and interval_from_monitor > 0:
                    interval = float(interval_from_monitor)
                    print(f"Applied monitor config: report interval={interval:.2f} s")
                next_report = time.monotonic() + interval
                if args.link_failure_after and report_count == args.link_failure_after:
                    recovery_ms = network.fail_link("R1", "R2")
                    path, delay = network.shortest_path("R1", "MON")
                    print(f"Link R1-R2 failed; recomputation={recovery_ms:.4f} ms; "
                          f"new path={' -> '.join(path)} delay={delay:.2f} ms")
            if now - last_packet >= args.idle_timeout and now - start >= args.idle_timeout:
                break
    result = stats.summary(args.expected_per_vehicle, args.vehicle_count)
    print("Summary: received={received}/{expected} avg_delay={delay_ms:.2f} ms "
          "PDR={pdr:.1%} loss={loss_ratio:.1%}".format(**result))


if __name__ == "__main__":
    main()
