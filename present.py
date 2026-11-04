"""Display fields shared by the HTML pages and the JSON endpoints.

SSH passwords and key paths are not part of these dicts.
"""


def present_detail(sample):
    memory = sample.get("memory")
    return {
        "id": sample["id"],
        "name": sample["name"],
        "host": sample["host"],
        "status": sample["status"],
        "message": sample.get("message") or "",
        "cpu_percent": sample.get("cpu_percent"),
        "cpu_text": _cpu_text(sample.get("cpu_percent")),
        "memory": _present_memory(memory),
        "memory_text": _memory_text(memory),
        "network": [_present_iface(item) for item in sample.get("network") or []],
        "ports": [_present_port(item) for item in sample.get("ports") or []],
        "last_success": sample.get("last_success"),
        "last_success_text": format_time(sample.get("last_success")),
    }


def present_list_row(sample):
    detail = present_detail(sample)
    memory = detail["memory"]
    if memory is None:
        memory_percent = None
        memory_text = "—"
    else:
        memory_percent = memory["percent"]
        memory_text = memory["percent_text"]
    return {
        "id": detail["id"],
        "name": detail["name"],
        "host": detail["host"],
        "status": detail["status"],
        "message": detail["message"],
        "cpu_percent": detail["cpu_percent"],
        "cpu_text": detail["cpu_text"],
        "memory_percent": memory_percent,
        "memory_text": memory_text,
        "last_success": detail["last_success"],
        "last_success_text": detail["last_success_text"],
    }


def _present_memory(memory):
    if not memory:
        return None
    return {
        "used_bytes": memory["used_bytes"],
        "total_bytes": memory["total_bytes"],
        "percent": memory["percent"],
        "used_text": format_bytes(memory["used_bytes"]),
        "total_text": format_bytes(memory["total_bytes"]),
        "percent_text": format_percent(memory["percent"]),
    }


def _present_iface(item):
    return {
        "name": item["name"],
        "rx_bytes": item["rx_bytes"],
        "tx_bytes": item["tx_bytes"],
        "rx_rate": item["rx_rate"],
        "tx_rate": item["tx_rate"],
        "rx_text": format_bytes(item["rx_bytes"]),
        "tx_text": format_bytes(item["tx_bytes"]),
        "rx_rate_text": format_rate(item["rx_rate"]),
        "tx_rate_text": format_rate(item["tx_rate"]),
    }


def _present_port(item):
    process = item.get("process")
    return {
        "protocol": item["protocol"],
        "address": item["address"],
        "port": item["port"],
        "process": process,
        "process_text": process if process else "—",
    }


def _cpu_text(value):
    if value is None:
        return "No CPU data."
    return format_percent(value)


def _memory_text(memory):
    if not memory:
        return "No memory data."
    presented = _present_memory(memory)
    return (
        f"{presented['used_text']} used of {presented['total_text']} "
        f"({presented['percent_text']})"
    )


def format_percent(value):
    if value is None:
        return "—"
    return f"{float(value):.1f}%"


def format_time(value):
    if not value:
        return "—"
    if isinstance(value, str) and value.endswith("Z"):
        return value[:-1].replace("T", " ") + " UTC"
    return str(value)


def format_bytes(value):
    if value is None:
        return "—"
    size = float(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for unit in units:
        if size < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def format_rate(value):
    if value is None:
        return "—"
    return format_bytes(value) + "/s"
