from fastapi import FastAPI

app = FastAPI(
    title="NewsChecker API",
    description="Backend for the News Bias and Fake News Detection Platform",
    version="0.1.0",
)


@app.get("/")
def home():
    return {
        "message": "NewsChecker API is running!",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }