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

- [ ] Add `config.json` generation: username `admin`, bcrypt hash of `monitor-demo`.
- [ ] Add sign-in and sign-out. Wrong password stays on the form with one generic error.
- [ ] Require a session for every page except sign-in.
- [ ] Unit tests: valid login, invalid login, sign-out, and redirect when signed out.
- [ ] Security: session cookie `HttpOnly` and `SameSite=Lax`. Secret key from the environment, not from source. Do not log the password. Compare with bcrypt only.
- [ ] Documentation: README section for the demo username, password, and hash file.

## 3. GitHub Actions CI

- [ ] Add `.github/workflows/ci.yml` to run `pytest` on push and pull request.
- [ ] Security: the workflow installs dependencies and runs tests only. No secrets, no deploy job, no artifact upload of config or inventory.
- [ ] Documentation: README note that CI runs tests, and the app is started locally on `127.0.0.1:5000`.

## 4. Empty app shell behind sign-in

- [ ] After sign-in, show a header (app name, sign-out) and an empty server list page.
- [ ] Security: list route returns redirect to sign-in when there is no session. Header has no remote-server actions.
- [ ] Documentation: one line in the README for the page you see after sign-in.

## 5. Inventory file

- [ ] Save and load servers as local JSON (name, host, port, username, password or key path).
- [ ] Unit tests for save, load, and a missing file.
- [ ] Security: inventory path is gitignored. Tests use a temp file. Do not put secrets in assertions or logs.
- [ ] Documentation: README names the inventory file and says not to commit it.

## 6. Add-server form

- [ ] Servers page: form for display name, host, SSH port (default 22), username, and password or key path.
- [ ] Reject a missing name, host, or username, and reject a submit with neither password nor key path.
- [ ] Unit tests for accept and reject cases.
- [ ] Security: POST only, Flask CSRF on the form. Store secrets in the inventory file only. Do not echo the password back on the page.
- [ ] Documentation: README field list, matching the PRD table.

## 7. Remove server

- [ ] Each saved server has a remove button with a confirmation. Removal deletes the local entry only.
- [ ] Unit test: remove drops that entry and leaves the others.
- [ ] Security: POST only, CSRF, signed-in only. No SSH call on remove.
- [ ] Documentation: README states remove does not change the remote host.

## 8. Server list without metrics

- [ ] List page shows display name, host, and a link to a detail URL for each saved server.
- [ ] Unit test: two servers render two links and no secret fields.
- [ ] Security: do not render SSH password or key path.
- [ ] Documentation: README describes the list columns.

## 9. Read-only SSH client

- [ ] Add a client that connects with an about-8-second timeout and runs a fixed command list.
- [ ] Unit tests with a fake SSH client: success, timeout, and authentication failure.
- [ ] Security: commands are constants in code (`/proc/stat`, `/proc/meminfo`, `/proc/net/dev`, `ss -H -lntup`, fallback `ss -H -lntu`). Host and username are connection arguments, never shell-joined. No write, install, or restart commands.
- [ ] Documentation: README lists the allowed commands.

## 10. Parse CPU

- [ ] Parse two `/proc/stat` samples into one overall CPU percent.
- [ ] Unit tests with fixed sample text, including a zero-delta case.
- [ ] Security: parser accepts text only. It does not run commands.
- [ ] Documentation: short comment in the parser module for the formula.

## 11. Parse memory

- [ ] Parse `/proc/meminfo` into used, total, and percent. Used excludes cache and buffers when those fields exist.
- [ ] Unit tests with a sample `meminfo`.
- [ ] Security: parser accepts text only.
- [ ] Documentation: note the used-memory rule in the parser module.

## 12. Parse network

- [ ] Parse `/proc/net/dev` into per-interface rx/tx bytes, skip loopback, and compute rates from the previous sample.
- [ ] Unit tests for one interface, loopback skipped, and the first sample (no rate yet).
- [ ] Security: parser accepts text only.
- [ ] Documentation: note that rates need two samples about 15 seconds apart.

## 13. Parse listening ports

- [ ] Parse `ss` output into protocol, address, port, and process name when present.
- [ ] Unit tests for TCP, UDP, a missing process name, and empty output.
- [ ] Security: parser accepts text only. Do not show remote command stderr if it could contain secrets; show a fixed message instead.
- [ ] Documentation: note the `ss -H -lntu` fallback.

## 14. Poll status

- [ ] Poll one server and set status `ok`, `unreachable`, or `auth failed`. Keep the last good sample timestamp if a later poll fails.
- [ ] Unit tests for all three statuses using the fake SSH client.
- [ ] Security: map library exceptions to those three statuses. Do not put exception text that contains credentials on the page.
- [ ] Documentation: README defines the three statuses.

## 15. Detail page

- [ ] Detail page shows identity, status, CPU, memory, network rates, and listening ports.
- [ ] Empty command output and a down host show a short message.
- [ ] Unit test with fixture data for each block.
- [ ] Security: signed-in only. Page is read-only. No shell, restart, or kill controls.
- [ ] Documentation: README lists the detail fields.

## 16. Metrics on the list

- [ ] List row adds status, CPU percent, memory percent, and last success time.
- [ ] Unit test with one ok server and one failed server.
- [ ] Security: a failed host does not stop the others from rendering.
- [ ] Documentation: README updates the list columns.

## 17. Fifteen-second refresh

- [ ] List and detail poll a JSON endpoint about every 15 seconds and update the page.
- [ ] A full reload still shows the latest sample when JavaScript is off.
- [ ] Unit test: the JSON endpoint requires a session and returns the same fields as the page.
- [ ] Security: JSON includes metrics and status only. No SSH secrets. Same session check as the HTML pages.
- [ ] Documentation: README states the 15-second refresh and the reload fallback.

## 18. Acceptance pass

- [ ] Walk the PRD acceptance list on `http://127.0.0.1:5000` and check each item.
- [ ] Security: confirm `config.json` and the inventory file are untracked, and the workflow has no deploy step.
- [ ] Documentation: mark the acceptance checks in the README.
