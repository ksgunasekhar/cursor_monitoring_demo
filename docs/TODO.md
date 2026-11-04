# Implementation TODO

Local demo only. One step at a time. Do not add accounts, alerts, history, or remote deploy.

Source: [requirements.md](requirements.md).

## 1. Project initialization and basic UI

- [x] Add `requirements.txt` (`flask`, `bcrypt`, `paramiko`, `pytest`) and a Flask app that serves one page.
- [x] Add a base layout and a simple home page (title, short description, readable type and spacing).
- [x] Bind the dev server to `127.0.0.1:5000` only.
- [x] Security: add `.gitignore` for `.venv/`, `__pycache__/`, `config.json`, and the inventory file. No secrets in the repo.
- [x] Documentation: `README.md` with the four local-run steps from the PRD (venv, install, config, start).

## 2. Sign-in and unit tests

- [x] Add `config.json` generation: username `admin`, bcrypt hash of `monitor-demo`.
- [x] Add sign-in and sign-out. Wrong password stays on the form with one generic error.
- [x] Require a session for every page except sign-in.
- [x] Unit tests: valid login, invalid login, sign-out, and redirect when signed out.
- [x] Security: session cookie `HttpOnly` and `SameSite=Lax`. Secret key from the environment, not from source. Do not log the password. Compare with bcrypt only.
- [x] Documentation: README section for the demo username, password, and hash file.

## 3. GitHub Actions CI

- [x] Add `.github/workflows/ci.yml` to run `pytest` on push and pull request.
- [x] Security: the workflow installs dependencies and runs tests only. No secrets, no deploy job, no artifact upload of config or inventory.
- [x] Documentation: README note that CI runs tests, and the app is started locally on `127.0.0.1:5000`.

## 4. Empty app shell behind sign-in

- [x] After sign-in, show a header (app name, sign-out) and an empty server list page.
- [x] Security: list route returns redirect to sign-in when there is no session. Header has no remote-server actions.
- [x] Documentation: one line in the README for the page you see after sign-in.

## 5. Inventory file

- [x] Save and load servers as local JSON (name, host, port, username, password or key path).
- [x] Unit tests for save, load, and a missing file.
- [x] Security: inventory path is gitignored. Tests use a temp file. Do not put secrets in assertions or logs.
- [x] Documentation: README names the inventory file and says not to commit it.

## 6. Add-server form

- [x] Servers page: form for display name, host, SSH port (default 22), username, and password or key path.
- [x] Reject a missing name, host, or username, and reject a submit with neither password nor key path.
- [x] Unit tests for accept and reject cases.
- [x] Security: POST only, Flask CSRF on the form. Store secrets in the inventory file only. Do not echo the password back on the page.
- [x] Documentation: README field list, matching the PRD table.

## 7. Remove server

- [x] Each saved server has a remove button with a confirmation. Removal deletes the local entry only.
- [x] Unit test: remove drops that entry and leaves the others.
- [x] Security: POST only, CSRF, signed-in only. No SSH call on remove.
- [x] Documentation: README states remove does not change the remote host.

## 8. Server list without metrics

- [x] List page shows display name, host, and a link to a detail URL for each saved server.
- [x] Unit test: two servers render two links and no secret fields.
- [x] Security: do not render SSH password or key path.
- [x] Documentation: README describes the list columns.

## 9. Read-only SSH client

- [x] Add a client that connects with an about-8-second timeout and runs a fixed command list.
- [x] Unit tests with a fake SSH client: success, timeout, and authentication failure.
- [x] Security: commands are constants in code (`/proc/stat`, `/proc/meminfo`, `/proc/net/dev`, `ss -H -lntup`, fallback `ss -H -lntu`). Host and username are connection arguments, never shell-joined. No write, install, or restart commands.
- [x] Documentation: README lists the allowed commands.

## 10. Parse CPU

- [x] Parse two `/proc/stat` samples into one overall CPU percent.
- [x] Unit tests with fixed sample text, including a zero-delta case.
- [x] Security: parser accepts text only. It does not run commands.
- [x] Documentation: short comment in the parser module for the formula.

## 11. Parse memory

- [x] Parse `/proc/meminfo` into used, total, and percent. Used excludes cache and buffers when those fields exist.
- [x] Unit tests with a sample `meminfo`.
- [x] Security: parser accepts text only.
- [x] Documentation: note the used-memory rule in the parser module.

## 12. Parse network

- [x] Parse `/proc/net/dev` into per-interface rx/tx bytes, skip loopback, and compute rates from the previous sample.
- [x] Unit tests for one interface, loopback skipped, and the first sample (no rate yet).
- [x] Security: parser accepts text only.
- [x] Documentation: note that rates need two samples about 15 seconds apart.

## 13. Parse listening ports

- [x] Parse `ss` output into protocol, address, port, and process name when present.
- [x] Unit tests for TCP, UDP, a missing process name, and empty output.
- [x] Security: parser accepts text only. Do not show remote command stderr if it could contain secrets; show a fixed message instead.
- [x] Documentation: note the `ss -H -lntu` fallback.

## 14. Poll status

- [x] Poll one server and set status `ok`, `unreachable`, or `auth failed`. Keep the last good sample timestamp if a later poll fails.
- [x] Unit tests for all three statuses using the fake SSH client.
- [x] Security: map library exceptions to those three statuses. Do not put exception text that contains credentials on the page.
- [x] Documentation: README defines the three statuses.

## 15. Detail page

- [x] Detail page shows identity, status, CPU, memory, network rates, and listening ports.
- [x] Empty command output and a down host show a short message.
- [x] Unit test with fixture data for each block.
- [x] Security: signed-in only. Page is read-only. No shell, restart, or kill controls.
- [x] Documentation: README lists the detail fields.

## 16. Metrics on the list

- [x] List row adds status, CPU percent, memory percent, and last success time.
- [x] Unit test with one ok server and one failed server.
- [x] Security: a failed host does not stop the others from rendering.
- [x] Documentation: README updates the list columns.

## 17. Fifteen-second refresh

- [x] List and detail poll a JSON endpoint about every 15 seconds and update the page.
- [x] A full reload still shows the latest sample when JavaScript is off.
- [x] Unit test: the JSON endpoint requires a session and returns the same fields as the page.
- [x] Security: JSON includes metrics and status only. No SSH secrets. Same session check as the HTML pages.
- [x] Documentation: README states the 15-second refresh and the reload fallback.

## 18. Acceptance pass

- [x] Walk the PRD acceptance list on `http://127.0.0.1:5000` and check each item.
- [x] Security: confirm `config.json` and the inventory file are untracked, and the workflow has no deploy step.
- [x] Documentation: mark the acceptance checks in the README.
