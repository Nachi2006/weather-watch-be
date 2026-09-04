from fastapi import FastAPI
app=FastAPI()

@app.get("/test")
def test_route():
    return {"test":"wassup gng"}