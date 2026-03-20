# Pre-Open Scanner

Real-time stock market pre-open scanner backend (FastAPI).

## Project structure

```
pre-open-scanner/
├── backend/
│   ├── main.py          # FastAPI app entry, routes
│   ├── auth.py          # JWT / login
│   ├── fyers_feed.py    # Fyers WebSocket feed
│   ├── nifty500.py      # Nifty 500 universe
│   ├── config.py        # Config from .env + config.yaml
│   ├── models.py        # Pydantic models
│   └── requirements.txt
├── .env                 # Secrets (not committed)
├── config.yaml          # App config
└── README.md
```

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   cd pre-open-scanner/backend
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` (or create `.env` from the placeholder) and set Fyers credentials, Redis URL, and JWT secret.

3. Edit `config.yaml` for scanner timing and options.

## Run

From the `backend` directory:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

## TODO

- Implement auth (login, JWT, protected routes).
- Wire Fyers feed in `fyers_feed.py` and expose WebSocket.
- Load Nifty 500 symbols in `nifty500.py` and integrate with scanner.
- Load settings in `config.py` from `.env` and `config.yaml`.
