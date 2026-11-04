from parsers import parse_cpu, parse_meminfo, parse_netdev, parse_ports
from tests.samples import MEMINFO, PORTS, STAT_FIRST, STAT_SECOND, netdev


def test_cpu_percent_and_zero_delta():
    assert parse_cpu(STAT_FIRST, STAT_SECOND) == 50.0
    assert parse_cpu(STAT_FIRST, STAT_FIRST) == 0.0
    assert parse_cpu("not stats", STAT_SECOND) is None


def test_memory_excludes_buffers_and_cache():
    parsed = parse_meminfo(MEMINFO)
    assert parsed["used_bytes"] == 500000 * 1024
    assert parsed["total_bytes"] == 2000000 * 1024
    assert parsed["percent"] == 25.0
    assert parse_meminfo("") is None


def test_network_skips_loopback_and_rates_need_a_previous_sample():
    counters, interfaces = parse_netdev(netdev(1000, 2000))
    assert list(counters) == ["eth0"]
    assert interfaces[0]["name"] == "eth0"
    assert interfaces[0]["rx_bytes"] == 1000
    assert interfaces[0]["tx_bytes"] == 2000
    assert interfaces[0]["rx_rate"] is None
    assert interfaces[0]["tx_rate"] is None

    _counters, again = parse_netdev(netdev(4000, 5000), previous=counters, elapsed=15)
    assert again[0]["rx_rate"] == 200.0
    assert again[0]["tx_rate"] == 200.0


def test_ports_tcp_udp_missing_process_and_empty():
    ports = parse_ports(PORTS)
    assert ports[0] == {
        "protocol": "tcp",
        "address": "0.0.0.0",
        "port": 22,
        "process": "sshd",
    }
    assert ports[1]["protocol"] == "udp"
    assert ports[1]["port"] == 53
    assert ports[1]["process"] is None
    assert ports[2]["address"] == "::"
    assert ports[2]["port"] == 443
    assert ports[2]["process"] == "nginx"
    assert parse_ports("") == []
    assert parse_ports("   \n") == []
