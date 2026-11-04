"""Fixed command output for parser and page tests."""

STAT_FIRST = (
    "cpu  100 0 0 300 0 0 0 0 0 0\n"
    "cpu0 0 0 0 10 0 0 0 0 0 0\n"
)
STAT_SECOND = (
    "cpu  200 0 50 450 0 0 0 0 0 0\n"
    "cpu0 5 0 0 10 0 0 0 0 0 0\n"
)
MEMINFO = (
    "MemTotal:       2000000 kB\n"
    "MemFree:        1000000 kB\n"
    "MemAvailable:   1400000 kB\n"
    "Buffers:         200000 kB\n"
    "Cached:          300000 kB\n"
)
PORTS = (
    'tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=100,fd=3))\n'
    "udp UNCONN 0 0 0.0.0.0:53 0.0.0.0:*\n"
    "tcp LISTEN 0 128 [::]:443 [::]:* users:((\"nginx\",pid=3,fd=5))\n"
)


def netdev(rx, tx, lo_rx=777777, lo_tx=777777):
    return (
        "Inter-|   Receive                                                |  Transmit\n"
        " face |bytes    packets errs drop fifo frame compressed multicast|"
        "bytes    packets errs drop fifo colls carrier compressed\n"
        f"    lo: {lo_rx} 0 0 0 0 0 0 0 {lo_tx} 0 0 0 0 0 0 0\n"
        f"  eth0: {rx} 1 0 0 0 0 0 0 {tx} 1 0 0 0 0 0 0\n"
    )


def outputs(rx=4096, tx=2048):
    return {
        "stat_first": STAT_FIRST,
        "stat_second": STAT_SECOND,
        "meminfo": MEMINFO,
        "netdev": netdev(rx, tx),
        "ports": PORTS,
    }


class OkCollector:
    def __init__(self):
        self.calls = []

    def read(self, *, host, port, username, password, key_path):
        self.calls.append(host)
        return outputs()
