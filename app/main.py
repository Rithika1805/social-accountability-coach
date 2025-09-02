from fastapi import FastAPI

app = FastAPI(title="Accountability Coach API")

@app.get("/health")
def health():
    return {"status": "ok"}
