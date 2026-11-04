"""Poll one server and keep the last good sample when a later poll fails."""

import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from parsers import parse_cpu, parse_meminfo, parse_netdev, parse_ports
from ssh_client import AuthFailed

AUTH_MESSAGE = "Authentication failed."
UNREACHABLE_MESSAGE = "The host could not be reached."


def poll_server(server, collector, previous, now):
    """Return a sample with status ok, unreachable, or auth failed.

    Library errors become one of those statuses. Exception text is dropped
    so a credential in a library message cannot reach the page.
    """
    try:
        raw = collector.read(
            host=server["host"],
            port=int(server["port"]),
            username=server["username"],
            password=server.get("password") or None,
            key_path=server.get("key_path") or None,
        )
    except AuthFailed:
        return _failed(server, previous, "auth failed", AUTH_MESSAGE)
    except Exception:
        return _failed(server, previous, "unreachable", UNREACHABLE_MESSAGE)

    elapsed = None
    prior_counters = None
    if previous and previous.get("_sampled_at") is not None:
        elapsed = now - previous["_sampled_at"]
        prior_counters = previous.get("_counters")

    counters, network = parse_netdev(raw.get("netdev", ""), prior_counters, elapsed)
    return {
        "id": server["id"],
        "name": server["name"],
        "host": server["host"],
        "status": "ok",
        "message": "",
        "cpu_percent": parse_cpu(raw.get("stat_first", ""), raw.get("stat_second", "")),
        "memory": parse_meminfo(raw.get("meminfo", "")),
        "network": network,
        "ports": parse_ports(raw.get("ports", "")),
        "last_success": _stamp(now),
        "_counters": counters,
        "_sampled_at": now,
    }


def refresh_servers(servers, collector, store, now):
    """Poll every server. One failure does not stop the others."""
    if not servers:
        return []

    def poll_one(server):
        previous = store.get(server["id"])
        return poll_server(server, collector, previous, now)

    results = {}
    workers = max(1, min(8, len(servers)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(poll_one, server): server["id"] for server in servers}
        for future in as_completed(futures):
            server_id = futures[future]
            results[server_id] = future.result()

    ordered = []
    known = set()
    for server in servers:
        sample = results[server["id"]]
        store[server["id"]] = sample
        ordered.append(sample)
        known.add(server["id"])
    for stale in list(store):
        if stale not in known:
            del store[stale]
    return ordered


def _failed(server, previous, status, message):
    if previous:
        sample = copy.deepcopy(previous)
    else:
        sample = {
            "id": server["id"],
            "name": server["name"],
            "host": server["host"],
            "status": status,
            "message": message,
            "cpu_percent": None,
            "memory": None,
            "network": [],
            "ports": [],
            "last_success": None,
            "_counters": None,
            "_sampled_at": None,
        }
    sample["id"] = server["id"]
    sample["name"] = server["name"]
    sample["host"] = server["host"]
    sample["status"] = status
    sample["message"] = message
    return sample


def _stamp(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
