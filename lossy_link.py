"""A configurable one-way UDP proxy that drops and delays datagrams."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import random
import socket
import threading
import time


class LossyUDPProxy:
    def __init__(self, listen_host: str, listen_port: int, target_host: str,
                 target_port: int, loss: float = 0.0, delay_ms: float = 0.0,
                 jitter_ms: float = 0.0, seed: int | None = None) -> None:
        self.address = (listen_host, listen_port)
        self.target = (target_host, target_port)
        self.loss, self.delay_ms, self.jitter_ms = loss, delay_ms, jitter_ms
        self.random = random.Random(seed)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.pending = self.received = self.forwarded = self.dropped = 0
        self.executor = ThreadPoolExecutor(max_workers=16)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.address)
        self.socket.settimeout(0.1)
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _forward(self, payload: bytes, delay: float) -> None:
        try:
            if delay > 0:
                time.sleep(delay)
            if not self.stop_event.is_set():
                self.socket.sendto(payload, self.target)
                with self.lock:
                    self.forwarded += 1
        except OSError:
            pass
        finally:
            with self.lock:
                self.pending -= 1

    def _serve(self) -> None:
        while not self.stop_event.is_set():
            try:
                payload, _ = self.socket.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            with self.lock:
                self.pending += 1
                self.received += 1
            if self.random.random() < self.loss:
                with self.lock:
                    self.dropped += 1
                    self.pending -= 1
                continue
            jitter = self.random.uniform(-self.jitter_ms, self.jitter_ms)
            delay = max(0.0, self.delay_ms + jitter) / 1000.0
            self.executor.submit(self._forward, payload, delay)

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=1.0)
        self.socket.close()
        self.executor.shutdown(wait=True)

    def counts(self) -> tuple[int, int, int, int]:
        with self.lock:
            return self.received, self.forwarded, self.dropped, self.pending


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen-host", default="127.0.0.3")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--controller-host", default="127.0.0.4")
    parser.add_argument("--controller-port", type=int, default=5000)
    parser.add_argument("--loss", type=float, default=0.0, help="probability from 0 to 1")
    parser.add_argument("--delay-ms", type=float, default=0.0)
    parser.add_argument("--jitter-ms", type=float, default=0.0)
    args = parser.parse_args()
    if not 0 <= args.loss <= 1 or args.delay_ms < 0 or args.jitter_ms < 0:
        parser.error("loss must be 0..1 and delay/jitter must be non-negative")
    proxy = LossyUDPProxy(args.listen_host, args.port, args.controller_host,
                          args.controller_port, args.loss, args.delay_ms, args.jitter_ms)
    proxy.start()
    print(f"UDP proxy {args.listen_host}:{args.port} -> "
          f"{args.controller_host}:{args.controller_port} loss={args.loss:.0%} "
          f"delay={args.delay_ms}±{args.jitter_ms} ms (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        proxy.stop()
    received, forwarded, dropped, _ = proxy.counts()
    print(f"Proxy totals: received={received}, forwarded={forwarded}, dropped={dropped}")


if __name__ == "__main__":
    main()
