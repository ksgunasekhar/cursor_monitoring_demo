# Demo Server Monitoring

Local demo for checking CPU, memory, network, and listening ports on Linux servers. It runs on this machine only.

## Local run

From the project directory:

1. Create a virtual environment.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies (`flask`, `bcrypt`, `paramiko`).

   ```bash
   pip install -r requirements.txt
   ```

3. Set a session secret in the environment. The app reads `FLASK_SECRET_KEY` from the environment and does not keep a secret in source.

   ```bash
   export FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```

   Starting the app writes `config.json` when that file is missing. The file holds username `admin` and a bcrypt hash of `monitor-demo`. The plain password is not stored in the file. `inventory.json` is the local server list (name, host, port, username, and password or key path). Keep `config.json` and `inventory.json` on this machine. Both are listed in `.gitignore`. Do not commit them.

4. Start Flask bound to `127.0.0.1` on port `5000`.

   ```bash
   python app.py
   ```

   Open `http://127.0.0.1:5000`.

GitHub Actions runs `pytest` on push and pull request. The workflow installs dependencies and runs tests. The app itself is started locally on `127.0.0.1:5000`.

## Sign in

Demo username: `admin`. Demo password: `monitor-demo`. The bcrypt hash lives in `config.json`. Change that hash before sharing the machine.

A failed sign-in stays on the form and shows one generic error. After sign-in you see the server list. The header has the app name and a sign-out action.

## Servers

`inventory.json` stores the saved servers. Do not commit it. Removing a server deletes that local entry only. It does not change the remote host.

Add-server fields:

| Field | Required | Notes |
| --- | --- | --- |
| Display name | Yes | Shown in the list |
| Hostname or IP | Yes | SSH target |
| SSH port | No | Default 22 |
| SSH username | Yes | Account used only to read stats |
| Auth | Yes | Password or a path to a private key on this machine |

## Server list

Columns: display name, host, status, CPU percent, memory percent, and last successful sample. The name links to the detail page. The page also links to Servers.

Status is one of:

- `ok` — the last poll connected and read the commands
- `unreachable` — the host did not answer, or the attempt timed out
- `auth failed` — SSH rejected the username, password, or key

A failed host does not stop the others from loading. If a later poll fails, the list keeps the last successful sample time.

## Server detail

The detail page shows:

- Display name, host, and status
- CPU: overall use percent
- Memory: used, total, and percent (cache and buffers are left out of used when `/proc/meminfo` has those fields)
- Network: receive and transmit bytes per non-loopback interface, plus the rate since the previous sample
- Listening ports: protocol, address, port, and process name when the remote user can see it
- A short message when a command returns nothing or the host is down

The page is read-only. It has no shell, restart, or kill controls.

## Collection

The poller connects with about an 8 second timeout and runs only these commands:

- `cat /proc/stat` (twice, about one second apart)
- `cat /proc/meminfo`
- `cat /proc/net/dev`
- `ss -H -lntup`
- `ss -H -lntu` when process names are not permitted

Network rates need two samples about 15 seconds apart. The first sample shows byte counters only.

The list and the detail page ask for new numbers about every 15 seconds and update without a full reload. With JavaScript off, reload the page to see the latest sample.

## Acceptance

- [x] A visitor who is not signed in cannot open the list, detail, or Servers pages.
- [x] `admin` / `monitor-demo` signs in when the stored hash matches. A wrong password does not.
- [x] Sign-out returns the user to the sign-in page.
- [x] An added server appears on the list. After a successful poll, detail shows CPU, memory, per-interface network rates, and listening ports with process names when available. The success sample is covered by the fixture tests. A closed local port shows `unreachable` instead.
- [x] A bad host or bad SSH login shows `unreachable` or `auth failed` and the rest of the list still loads.
- [x] Removing a server drops it from the UI only.
- [x] SSH sessions are used only for the reads in the collection section.
- [x] `config.json` and `inventory.json` are untracked, and the workflow has no deploy step.
