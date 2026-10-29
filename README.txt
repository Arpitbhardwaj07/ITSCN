ITSCN - Intelligent Traffic Signal Communication Network
========================================================

Small localhost simulation for selected Computer Networks topics. Run the
commands below from the workspace folder that contains the itscn directory.

REQUIREMENTS
------------
Python 3 and matplotlib. The other modules use only the Python standard library.

    python -m pip install matplotlib

All live sockets use 127.0.0.x loopback addresses on this same computer:
vehicle 127.0.0.2, lossy proxy 127.0.0.3, RSU/controller 127.0.0.4, monitor
127.0.0.5. Ports distinguish the UDP and TCP services. The private subnet plan
printed by subnet_planner.py is a logical addressing exercise; Windows does not
configure those LANs or route packets between physical machines.

RUN THE PROGRAMS
----------------
Transport choice: UDP carries frequent vehicle updates because low delay is
useful and sequence numbers let the controller measure missing updates. TCP
carries monitor reports and configuration commands because those messages need
reliable, ordered delivery and a reply.

1. Print the IPv4 subnet plan:

    python itscn/subnet_planner.py

2. Direct UDP demonstration. Start the controller in one terminal:

    python itscn/rsu_controller.py --expected-per-vehicle 15 --vehicle-count 1 --idle-timeout 1

   In a second terminal, send 15 updates:

    python itscn/vehicle_sender.py --count 15 --rate 5

   The controller prints received sequence numbers and delays, then a final
   PDR (received/expected) and loss ratio. Set expected-per-vehicle to match
   the sender count for accurate tail-loss accounting.

3. UDP through the lossy proxy. Start the controller as above, then in another
   terminal start the proxy:

    python itscn/lossy_link.py --loss 0.10 --delay-ms 20 --jitter-ms 5

   Send through the proxy:

    python itscn/vehicle_sender.py --host 127.0.0.3 --port 5001 --count 15 --rate 5

   Stop the proxy with Ctrl+C after the sender and controller finish.

4. TCP monitor and changing report path. Start the monitor first:

    python itscn/monitor_server.py --new-interval 2

   Then start the controller in another terminal:

    python itscn/rsu_controller.py --monitor --report-interval 1 --expected-per-vehicle 30 --vehicle-count 1 --link-failure-after 1 --idle-timeout 5

   Start a sender in a third terminal:

    python itscn/vehicle_sender.py --count 30 --rate 5

   The monitor replies over TCP with a new reporting interval. After the first
   report, R1-R2 fails in the OSPF-style link-state simulation. The next report
   shows the new path delay computed from the remaining link costs. Ctrl+C stops
   the monitor.

5. Print routing tables, fail a link, and recompute routes:

    python itscn/linkstate_sim.py

   The output includes each router table before and after failure, the changed
   R1-to-monitor path, and measured in-process recomputation time.

6. Run the slotted channel comparison by itself:

    python itscn/csma_sim.py

7. Run repeated UDP trials (5 trials minimum per loss/vehicle setting) and the
   CSMA model, then create the PNG graphs:

    python itscn/run_experiments.py
    python itscn/plot_results.py

   Results are written to itscn/results/experiments.csv, csma.csv,
   delay_vs_loss.png, pdr_vs_loss.png, csma_vs_aloha.png, and
   report_delay_link_failure.png. Trial settings can be increased with
   --trials 8, or shortened for exploration with --packets 6. At least five
   trials are enforced. Each traffic trial is paired with normal and
   link_failure route rows; UDP metrics match because the modeled failure
   changes only the controller-to-monitor report path.

FILES AND VIVA NOTES
--------------------
subnet_planner.py: ipaddress-based CIDR subnetting, network masks, host ranges,
broadcast addresses, and a first-usable gateway convention.
vehicle_sender.py: JSON vehicle updates over UDP with sequence numbers and send
timestamps.
lossy_link.py: UDP proxy that independently drops, delays, and jitters datagrams.
rsu_controller.py: UDP receive statistics, sequence-gap notices, PDR/loss
calculation, periodic TCP reports/config updates, and modeled route delay.
monitor_server.py: TCP server that reads one ordered JSON report and replies
with a report-interval command.
linkstate_sim.py: link-state database, Dijkstra shortest paths, route tables,
one link failure, and recomputation timing. This is an OSPF-style link-state
simulation, not real OSPF or real router convergence.
csma_sim.py: simplified slotted ALOHA and CSMA contention with collision rate
and successful packets per slot.
run_experiments.py: repeated localhost UDP proxy trials and CSV generation.
plot_results.py: reads the generated CSV files and writes four PNG graphs.

LIMITATIONS
-----------
All packet exchange is on one computer through loopback. The UDP proxy is a
software model, not a radio or a real wireless channel. The CSMA model is a
small slotted random-backoff approximation, not a full MAC implementation.
Routing and link-failure recovery are computed in Python; no OSPF packets,
routers, or physical convergence are present. The report's modeled one-way
path delay is the sum of configured link costs; the printed observed TCP
round-trip also includes local Python, socket, and scheduling overhead. Results
are demonstrations from this simulator, not claims about a real city network.
