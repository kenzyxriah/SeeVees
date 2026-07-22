from routers.auth_api import router as auth_router
from routers.user_api import router as user_router
from routers.admin_api import router as admin_router
from routers.employer_api import router as employer_router
from routers.candidate_api import router as candidate_router

routers = [auth_router, user_router, admin_router, employer_router, candidate_router]



