import warnings
import uvicorn
import secrets
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials


from core.config import ENVIRONMENT
from core.lifespan import lifespan
from core.middleware import monitor_traffic
from core.exceptions import global_exception_handler
from core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from routers import routers


warnings.filterwarnings("ignore")

print(f"\nAPPLICATION RUNNING ON {ENVIRONMENT} ENVIRONMENT\n")

security = HTTPBasic()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(monitor_traffic)
app.add_exception_handler(Exception, global_exception_handler)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def authenticate_docs(credentials: HTTPBasicCredentials = Depends(security)):
    if not (secrets.compare_digest(credentials.username, "user") and secrets.compare_digest(credentials.password, "pass")):
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})


@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint(auth: None = Depends(authenticate_docs)):
    return get_openapi(title=app.title, version=app.version, routes=app.routes)


@app.get("/docs", include_in_schema=False)
async def get_documentation(auth: None = Depends(authenticate_docs)):
    return get_swagger_ui_html(
        openapi_url="/openapi.json", 
        title="Secure Docs"
    )


@app.get("/", tags=["Health"])
@app.post("/", tags=["Health"])
def root():
    return {"message": "Welcome to SeeVees API"}


for router in routers:
    app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app)
