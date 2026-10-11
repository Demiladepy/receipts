"""Demo server. Vercel serves public/index.html at /, and this app answers /api."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from webapp import PAGE_PATH, case_payload, scenario_index

app = FastAPI(title="Receipts")


@app.get("/")
def home():
    return FileResponse(PAGE_PATH)


@app.get("/api/scenarios")
def scenarios():
    return scenario_index()


@app.get("/api/cases/{seed}")
def case(seed: int):
    payload = case_payload(seed)
    if payload is None:
        raise HTTPException(status_code=404, detail="No case with that seed.")
    return payload
