from fastapi import FastAPI

app = FastAPI()

@app.get("/rate")
def rate(source: str, destination: str):
    return {"rate": 1.1}
