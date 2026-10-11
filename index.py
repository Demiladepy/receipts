"""Demo server. Vercel serves public/index.html at /, and this app answers /api."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

import webapp_runs
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


@app.get("/api/runs/summary")
def runs_summary():
    return {"metrics": webapp_runs.summary(), "taxonomy": webapp_runs.taxonomy(),
            "flagged": webapp_runs.flagged_seeds()}


@app.get("/api/runs/{seed}")
def runs_case(seed: int, rep: int = 1):
    payload = webapp_runs.case(seed, rep)
    if payload is None:
        raise HTTPException(status_code=404, detail="No case with that seed.")
    return payload
