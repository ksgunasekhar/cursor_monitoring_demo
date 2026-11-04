"""Parsers for read-only Linux stats.

Each function accepts command output as text. None of them run commands.
"""

import re

# users:(("sshd",pid=1,fd=3))
_PROCESS = re.compile(r'users:\(\("([^"]*)"')


def parse_cpu(first, second):
    """Overall CPU percent from two aggregate /proc/stat samples.

    percent = 100 * (total_delta - idle_delta) / total_delta

    idle is idle plus iowait. total is user, nice, system, idle, iowait,
    irq, softirq, and steal. Guest counts are left out because they are
    already included in user and nice. A zero total delta returns 0.0.
    """
    before = _cpu_fields(first)
    after = _cpu_fields(second)
    if before is None or after is None:
        return None
    total_before, idle_before = before
    total_after, idle_after = after
    total_delta = total_after - total_before
    if total_delta <= 0:
        return 0.0
    busy = total_delta - (idle_after - idle_before)
    if busy < 0:
        busy = 0
    if busy > total_delta:
        busy = total_delta
    return round(100.0 * busy / total_delta, 1)


def _cpu_fields(text):
    if not isinstance(text, str):
        return None
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0] != "cpu":
            continue
        numbers = []
        for item in parts[1:]:
            try:
                numbers.append(int(item))
            except ValueError:
                return None
        if len(numbers) < 4:
            return None
        padded = numbers + [0] * 8
        user, nice, system, idle, iowait, irq, softirq, steal = padded[:8]
        total = user + nice + system + idle + iowait + irq + softirq + steal
        return total, idle + iowait
    return None


def parse_meminfo(text):
    """Parse /proc/meminfo into used bytes, total bytes, and percent.

    used = MemTotal - MemFree - Buffers - Cached when Buffers and Cached
    are present, so disk cache is not counted as used. A missing cache
    field is left out of that subtraction. meminfo numbers are kibibytes.
    """
    if not isinstance(text, str):
        return None
    fields = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        bits = rest.split()
        if not bits:
            continue
        try:
            fields[key.strip()] = int(bits[0])
        except ValueError:
            continue
    if "MemTotal" not in fields or "MemFree" not in fields:
        return None
    total = fields["MemTotal"]
    if total <= 0:
        return None
    used = total - fields["MemFree"]
    if "Buffers" in fields:
        used -= fields["Buffers"]
    if "Cached" in fields:
        used -= fields["Cached"]
    if used < 0:
        used = 0
    return {
        "used_bytes": used * 1024,
        "total_bytes": total * 1024,
        "percent": round(100.0 * used / total, 1),
    }


def parse_netdev(text, previous=None, elapsed=None):
    """Parse /proc/net/dev into per-interface receive and transmit bytes.

    Loopback (lo) is skipped. Rates need two samples about 15 seconds
    apart. Pass the previous counters and the elapsed seconds to fill
    rx_rate and tx_rate. The first sample leaves those rates as None.
    """
    counters = {}
    if isinstance(text, str):
        for line in text.splitlines():
            if ":" not in line:
                continue
            name, rest = line.split(":", 1)
            name = name.strip()
            if not name:
                continue
            numbers = []
            valid = True
            for item in rest.split():
                try:
                    numbers.append(int(item))
                except ValueError:
                    valid = False
                    break
            if not valid or len(numbers) < 9:
                continue
            counters[name] = {"rx": numbers[0], "tx": numbers[8]}

    previous = previous or {}
    interfaces = []
    kept = {}
    for name, counts in counters.items():
        if name == "lo":
            continue
        kept[name] = counts
        rx_rate = None
        tx_rate = None
        prior = previous.get(name)
        if elapsed and elapsed > 0 and isinstance(prior, dict):
            rx_rate = _rate(counts["rx"], prior.get("rx"), elapsed)
            tx_rate = _rate(counts["tx"], prior.get("tx"), elapsed)
        interfaces.append(
            {
                "name": name,
                "rx_bytes": counts["rx"],
                "tx_bytes": counts["tx"],
                "rx_rate": rx_rate,
                "tx_rate": tx_rate,
            }
        )
    return kept, interfaces


def _rate(current, prior, elapsed):
    if not isinstance(prior, int) or not isinstance(current, int):
        return None
    delta = current - prior
    if delta < 0:
        return None
    return round(delta / elapsed, 1)


def parse_ports(text):
    """Parse ss output into protocol, address, port, and process name.

    The collector prefers `ss -H -lntup` and falls back to `ss -H -lntu`
    when process names are not permitted. A missing process name is None.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    ports = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 5:
            continue
        raw_protocol = parts[0].lower()
        if raw_protocol.startswith("tcp"):
            protocol = "tcp"
        elif raw_protocol.startswith("udp"):
            protocol = "udp"
        else:
            continue
        located = _split_address(parts[4])
        if located is None:
            continue
        address, port = located
        match = _PROCESS.search(stripped)
        process = match.group(1) if match and match.group(1) else None
        ports.append(
            {
                "protocol": protocol,
                "address": address,
                "port": port,
                "process": process,
            }
        )
    return ports


def _split_address(local):
    if local.startswith("["):
        end = local.find("]")
        if end < 0 or not local[end:].startswith("]:"):
            return None
        address = local[1:end]
        port_text = local[end + 2 :]
    else:
        if ":" not in local:
            return None
        address, port_text = local.rsplit(":", 1)
    try:
        port = int(port_text)
    except ValueError:
        return None
    if port < 0 or port > 65535 or address == "":
        return None
    return address, port
