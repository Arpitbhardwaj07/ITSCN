"""TCP monitor that receives ordered reports and returns an interval command."""

import argparse
import json
import socket


def serve(host: str, port: int, new_interval: float) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        print(f"Monitor listening on TCP {host}:{port}; config interval={new_interval:.2f} s")
        while True:
            connection, address = server.accept()
            with connection:
                connection.settimeout(3.0)
                with connection.makefile("rwb") as channel:
                    try:
                        report = json.loads(channel.readline().decode("utf-8"))
                        print(f"Report from {address[0]}: received={report.get('received')}/"
                              f"{report.get('expected')} PDR={report.get('pdr', 0):.1%} "
                              f"route={report.get('route_path')} "
                              f"path_delay={report.get('route_delay_ms', 0):.2f} ms")
                        command = {"command": "set_report_interval", "seconds": new_interval}
                        channel.write(json.dumps(command).encode("utf-8") + b"\n")
                        channel.flush()
                    except (OSError, ValueError, json.JSONDecodeError) as error:
                        print(f"Ignored invalid TCP report: {error}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.5")
    parser.add_argument("--port", type=int, default=6000)
    parser.add_argument("--new-interval", type=float, default=2.0)
    args = parser.parse_args()
    if args.new_interval <= 0:
        parser.error("--new-interval must be positive")
    try:
        serve(args.host, args.port, args.new_interval)
    except KeyboardInterrupt:
        print("Monitor stopped")


if __name__ == "__main__":
    main()
