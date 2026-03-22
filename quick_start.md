# Quick Start

## First-time Setup

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Get login cookie

```bash
python cookie_auto_login.py
```

### 3) Run subtitle extraction

```bash
python subtitle_extractor.py
```

## Visual UI (recommended)

```bash
streamlit run app.py
```

Features in the UI:
- Single BVID extraction
- Batch extraction
- Manual JSON parsing

## Common commands

### Batch extract

```bash
python subtitle_extractor.py
# choose mode: 2
# input: BV1ZL411o7LZ BV1fT411B7od BV1Fk4y1v7fQ
```

### Refresh cookie

```bash
python cookie_auto_login.py
```

## Project files

- app.py
- subtitle_extractor.py
- cookie_auto_login.py
- requirements.txt
- README.md
- quick_start.md
- cookie.txt (local only, gitignored)

## Notes

- Do not commit cookie.txt.
- If cookie expires, run cookie_auto_login.py again.
- Please use responsibly and follow platform rules.
