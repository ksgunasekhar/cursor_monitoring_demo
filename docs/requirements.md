# Demo Server Monitoring — Requirements

## 1. Purpose

Local demo for internal teams who today sign in to Linux servers to check CPU, memory, network, and listening ports. The app collects those stats over SSH and shows them in a read-only web UI. It runs on the machine where this project is open. It is not a production monitoring system.

## 2. Users

L1, L2, and L3 teams in infrastructure and application development. For this demo they share one login. There are no separate roles.

## 3. In scope

- Sign in and sign out for a single user.
- Add and remove Linux servers that the demo should poll.
- A server list and a per-server detail page.
- Live CPU, memory, network, and listening-port data over SSH.
- Refresh about every 15 seconds.
- Clear status when a host cannot be polled.

## 4. Out of scope

- Windows or other operating systems.
- Alerts, thresholds, paging, or tickets.
- Charts or stored history. The screen shows the latest sample only.
- Any change on the remote server (no installs, restarts, file edits, or package changes).
- Extra user accounts, teams, or permissions.
- HTTPS, a public hostname, or a multi-host deployment.

## 5. Tech stack

- Python 3 and Flask.
- Server-rendered pages (Jinja templates), with plain CSS and a small amount of JavaScript for refresh.
- Paramiko (or an equivalent SSH library) for read-only SSH.
- Local JSON files for the app config and the server inventory. No database.

## 6. Sign in

- Default username: `admin`.
- The password is stored only as a bcrypt hash in a local config file (`config.json` in the project directory).
- The app compares the submitted password to that hash. It never stores or logs the plain password.
- A successful sign-in creates a Flask session cookie. Unauthenticated requests to any page except the sign-in page redirect to sign-in.
- The header includes a sign-out action that clears the session.
- Demo password for local use: `monitor-demo`. Setup writes the bcrypt hash of that password into `config.json`. Change the hash before sharing the machine.

## 7. Servers

Metrics pages are view-only. A separate **Servers** page can add and remove inventory entries. Removing a server only deletes it from the local list. It does not connect to change the host.

**Add server** fields:

| Field | Required | Notes |
| --- | --- | --- |
| Display name | Yes | Shown in the list |
| Hostname or IP | Yes | SSH target |
| SSH port | No | Default 22 |
| SSH username | Yes | Account used only to read stats |
| Auth | Yes | Password or a path to a private key on this machine |

SSH secrets are saved in the local inventory file so the poller can reconnect. They cannot be bcrypt-hashed, because the app must present them to SSH. Do not commit `config.json` or the inventory file.

The remote account needs permission to read CPU, memory, network counters, and listening sockets. It does not need root if those reads work as the chosen user.

## 8. Screens

### Sign in

Username, password, and a submit button. Failed attempts stay on the page and show a short error. Do not say which field was wrong.

### Server list

Shown after sign-in. One row or card per server:

- Display name and hostname
- Status: `ok`, `unreachable`, or `auth failed`
- CPU percent and memory percent from the latest sample
- Time of the last successful sample
- Link to the detail page
- Link to the Servers page

The list asks the app for new numbers about every 15 seconds and updates without a full reload.

### Server detail

- Same identity and status as the list
- **CPU:** overall use percent
- **Memory:** used, total, and percent (exclude disk cache from “used” when `/proc/meminfo` is available)
- **Network:** for each non-loopback interface, receive and transmit bytes and the rate since the previous sample
- **Ports:** listening TCP and UDP sockets, with port, address, protocol, and process name when the remote user can see it
- A short message when a command returns nothing or the host is down
- Same 15-second refresh as the list

### Servers (inventory)

- Form to add a server
- List of saved servers with a remove action and a confirmation
- Validation errors for a missing name, host, or username, or when neither a password nor a key path is provided

## 9. Collection

On each 15-second cycle the app opens SSH to each saved server and runs read-only commands only. It must not send shell input that writes, installs, or restarts anything.

Use these sources:

- CPU: `/proc/stat` sampled twice over a short gap (about one second), then converted to overall percent
- Memory: `/proc/meminfo`
- Network: `/proc/net/dev`
- Listening ports: `ss -H -lntup` (fall back to `ss -H -lntu` if process names are not permitted)

Per host, use a short connect and command timeout (about 8 seconds). One failed host must not block the others. Show the previous good sample’s timestamp and the current error if a later poll fails.

## 10. UI

- Readable on a laptop browser: clear type, spacing, and a simple layout.
- Status is visible as text, not only by color.
- No controls that imply operating the remote server (no restart, kill, or shell).
- Pages work if JavaScript fails to refresh: a manual reload still shows the latest sample.

## 11. Local run

From the project directory, on the machine where Cursor is running:

1. Create a virtual environment and install dependencies (`flask`, `bcrypt`, `paramiko`).
2. Generate `config.json` with username `admin` and a bcrypt hash of `monitor-demo`.
3. Start Flask bound to `127.0.0.1` on port `5000`.
4. Open `http://127.0.0.1:5000`, sign in, add a Linux host, and confirm the detail page updates about every 15 seconds.

`config.json` and the inventory file stay on this machine and are listed in `.gitignore`.

## 12. Acceptance

- A visitor who is not signed in cannot open the list, detail, or Servers pages.
- `admin` / `monitor-demo` signs in when the stored hash matches. A wrong password does not.
- Sign-out returns the user to the sign-in page.
- An added Linux server appears on the list. After a successful poll, detail shows CPU, memory, per-interface network rates, and listening ports with process names when available.
- A bad host or bad SSH login shows `unreachable` or `auth failed` and the rest of the list still loads.
- Removing a server drops it from the UI only.
- SSH sessions are used only for the reads in section 9.
