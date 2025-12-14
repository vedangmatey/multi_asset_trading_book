# Deployment Notes

## Local Deployment
```bash
streamlit run app.py
```

## Secrets Management
Refinitiv credentials are stored in:
```
.streamlit/secrets.toml
```

Never hard-code API keys.

## Cloud Deployment (Streamlit Cloud)
- Add secrets via the Streamlit UI
- Ensure `requirements.txt` includes `refinitiv-data`
- Disable unsupported features if Refinitiv Desktop is unavailable

## Known Constraints
- Some Refinitiv endpoints require Desktop or RDP entitlement
- Rate fields vary by instrument and permissions
