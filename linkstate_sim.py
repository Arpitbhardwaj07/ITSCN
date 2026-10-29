"""Small OSPF-style link-state simulation using delay costs and Dijkstra."""

import time


class LinkStateNetwork:
    def __init__(self) -> None:
        # Each node advertises its directly connected links in this LSDB.
        self.lsdb = {
            "R1": {"R2": 10.0, "R3": 20.0},
            "R2": {"R1": 10.0, "R3": 10.0, "MON": 2.0},
            "R3": {"R1": 20.0, "R2": 10.0},
            "MON": {"R2": 2.0},
        }
        self.routes: dict[str, tuple[dict[str, float], dict[str, str]]] = {}
        self.recompute_all()

    def dijkstra(self, source: str) -> tuple[dict[str, float], dict[str, str]]:
        costs = {node: float("inf") for node in self.lsdb}
        previous: dict[str, str] = {}
        costs[source] = 0.0
        pending = set(self.lsdb)
        while pending:
            current = min(pending, key=lambda node: costs[node])
            pending.remove(current)
            if costs[current] == float("inf"):
                break
            for neighbor, edge_cost in self.lsdb[current].items():
                candidate = costs[current] + edge_cost
                if candidate < costs[neighbor]:
                    costs[neighbor] = candidate
                    previous[neighbor] = current
        return costs, previous

    def recompute_all(self) -> None:
        self.routes = {router: self.dijkstra(router) for router in self.lsdb}

    def shortest_path(self, source: str, destination: str) -> tuple[list[str], float]:
        costs, previous = self.dijkstra(source)
        if costs[destination] == float("inf"):
            return [], float("inf")
        path = [destination]
        while path[-1] != source:
            path.append(previous[path[-1]])
        path.reverse()
        return path, costs[destination]

    def fail_link(self, first: str, second: str) -> float:
        self.lsdb[first].pop(second, None)
        self.lsdb[second].pop(first, None)
        started = time.perf_counter()
        self.recompute_all()
        return (time.perf_counter() - started) * 1000

    def print_tables(self, title: str) -> None:
        print(f"\n{title}")
        for router in ("R1", "R2", "R3"):
            costs, previous = self.routes[router]
            print(f"{router} routing table")
            print("Destination | Next hop | Cost (ms) | Path")
            for destination in ("R1", "R2", "R3", "MON"):
                if destination == router:
                    path, next_hop = router, "-"
                elif costs[destination] == float("inf"):
                    path, next_hop = "unreachable", "-"
                else:
                    path_nodes = [destination]
                    while path_nodes[-1] != router:
                        path_nodes.append(previous[path_nodes[-1]])
                    path_nodes.reverse()
                    path, next_hop = " -> ".join(path_nodes), path_nodes[1]
                cost = costs[destination]
                cost_text = "-" if cost == 0 else ("inf" if cost == float("inf") else f"{cost:.1f}")
                print(f"{destination:11} | {next_hop:8} | {cost_text:9} | {path}")


def main() -> None:
    network = LinkStateNetwork()
    network.print_tables("Before link failure")
    old_path, old_cost = network.shortest_path("R1", "MON")
    recovery_ms = network.fail_link("R1", "R2")
    network.print_tables("After link failure R1-R2")
    new_path, new_cost = network.shortest_path("R1", "MON")
    print(f"Changed path: {' -> '.join(old_path)} ({old_cost:.1f} ms) -> "
          f"{' -> '.join(new_path)} ({new_cost:.1f} ms)")
    print(f"Route recomputation time: {recovery_ms:.4f} ms")
    print("This is an OSPF-style link-state simulation, not real router convergence.")


if __name__ == "__main__":
    main()
