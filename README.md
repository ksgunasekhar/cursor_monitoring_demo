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

3. `config.json` holds username `admin` and a bcrypt hash of `monitor-demo`. This page does not read that file yet. When you create it, keep `config.json` and the inventory file (`inventory.json`) on this machine. Both are listed in `.gitignore`.

4. Start Flask bound to `127.0.0.1` on port `5000`.

   ```bash
   python app.py
   ```

   Open `http://127.0.0.1:5000`.
