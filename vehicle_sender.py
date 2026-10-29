"""Send small JSON vehicle updates over UDP to an RSU or lossy proxy."""

import argparse
import json
import random
import socket
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.4")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--source", default="127.0.0.2")
    parser.add_argument("--vehicle-id", default="car-1")
    parser.add_argument("--rate", type=float, default=5.0, help="packets per second")
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()
    if args.rate <= 0 or args.count < 1:
        parser.error("--rate and --count must be positive")

    directions = ("N", "E", "S", "W")
    address = (args.host, args.port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.bind((args.source, 0))
        next_send = time.monotonic()
        for sequence in range(1, args.count + 1):
            message = {
                "vehicle_id": args.vehicle_id,
                "speed": round(random.uniform(15, 60), 1),
                "position": [round(random.uniform(0, 100), 1), round(random.uniform(0, 100), 1)],
                "direction": random.choice(directions),
                "seq": sequence,
                "send_time": time.time(),
            }
            sender.sendto(json.dumps(message).encode("utf-8"), address)
            next_send += 1.0 / args.rate
            time.sleep(max(0.0, next_send - time.monotonic()))
    print(f"Sent {args.count} updates for {args.vehicle_id} to {args.host}:{args.port}")


if __name__ == "__main__":
    main()
