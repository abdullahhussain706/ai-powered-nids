# AI-Powered Network Intrusion Detection System

A desktop-based Network Intrusion Detection System (NIDS) for real-time packet capture, flow extraction, signature-based detection, alert storage, and security monitoring through a PySide6 dashboard.

## Features

- Live packet capture using `tshark`
- PCAP storage for captured traffic
- Packet parsing and flow building
- Flow-based feature extraction
- Signature/rule-based detection using JSON rules
- Alert deduplication and persistence
- SQLite alert database
- JSONL alert logging
- Dashboard with packets/sec, flows/sec, timeline graph, alerts, and host stats
- Alerts view with severity stats, filters, pagination, and CSV export
- Logs view with level filtering and pagination
- Settings view with rule management
- Cross-platform path handling for Windows and Ubuntu Linux

## Screenshots

Add real screenshots from your running project in `docs/screenshots/` and keep these names:

```text
docs/screenshots/dashboard.png
docs/screenshots/alerts.png
docs/screenshots/logs.png
docs/screenshots/settings.png
```

When screenshots exist, they will render here:

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### Alerts
![Alerts](docs/screenshots/alerts.png)

### Logs
![Logs](docs/screenshots/logs.png)

### Settings
![Settings](docs/screenshots/settings.png)

## Project Structure

```text
core/        Backend IDS pipeline: capture, parsing, flows, features, rules, alerts
ui/          PySide6 desktop interface
database/    SQLite schema and database helpers
rule/        Active JSON detection rules
rules/       Extended/alternate rule corpus
logs/        Runtime logs, ignored from git
data/        Runtime captures and processed data
ml/          ML placeholders/pipeline files
services/    Service placeholders
docs/        Documentation and screenshots
tests/       Test placeholders
```

## Main Data Flow

```text
Network Interface
  -> tshark capture
  -> data/raw_packets/*.pcap
  -> packet parser
  -> flow builder
  -> feature engine
  -> signature engine + rule/*.json
  -> alert manager
  -> database/ids.db + logs/alerts.jsonl
  -> desktop UI
```

## Requirements

- Python 3.10+
- Wireshark/tshark installed and available in PATH
- Administrator/root permissions may be required for live packet capture
- Windows or Ubuntu Linux

Python dependencies are listed in:

```bash
requirements.txt
```

## Setup

### Ubuntu Linux

```bash
sudo apt update
sudo apt install tshark python3 python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows

1. Install Wireshark and include `tshark` in PATH.
2. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Run

### Ubuntu Linux

```bash
./run.py
```

or:

```bash
python run.py
```

### Windows

```powershell
python run.py
```

`run.py` starts both:

- Backend capture pipeline: `core/packet_capture.py`
- Frontend desktop UI: `ui.main_window`

## Capture Interface

By default, the system tries to select the first interface reported by `tshark -D`.

To manually set an interface:

### Ubuntu Linux

```bash
IDS_INTERFACE=wlan0 python run.py
```

### Windows PowerShell

```powershell
$env:IDS_INTERFACE="1"
python run.py
```

## Environment Variables

```text
IDS_INTERFACE        Capture interface name or tshark interface number
IDS_PACKET_LIMIT     Packets per capture cycle, default 500
IDS_DELAY            Delay between capture cycles, default 1
IDS_MAX_FILES        Max retained pcap files, default 50
IDS_TSHARK_TIMEOUT   Capture timeout in seconds, default 120
```

## Runtime Files

These files are generated locally and should not be committed:

```text
database/*.db
logs/
data/raw_packets/
*.pcap
*.pcapng
```

They are ignored through `.gitignore`.

## Important Notes

- `rule/` contains the active rules used by the current signature engine.
- `rules/` contains an extended/alternate rule corpus and is not the primary runtime rule path.
- The current operational detection path is signature/rule based.
- ML/anomaly/fusion modules are present as project extension areas.

## License

MIT License

## Authors

Muhammad Abdullah  
Faizan Ali
