# SeeVees

SeeVees is a small assessment platform built for employers to create technical tests, send them to candidates, and review submissions. The app is intentionally focused on a simple setup with two main roles:

- Admin
- Employer

Candidates are not expected to create accounts and use the platform as a general product. They are invited by email, take the assessment, and later access their result through a submission link.

## What this project does

The service currently supports:

- employer sign-up and login
- admin and employer access control
- creating and managing tests
- assigning tests to candidates by email
- collecting answers and storing submissions
- reviewing submissions for a test
- basic result access for candidates

## Assumptions and decisions

This implementation was kept intentionally direct and practical:

- The platform is mainly for employers, so the app focuses on Admin and Employer roles.
- Candidates only need access to the assessment flow and submission result. They do not need their own account experience.
- The database is managed through Docker Compose for this project. A managed database would also work, but this was the simplest route.
- The app uses PostgreSQL and Redis, both started through Docker Compose.

## Requirements

Before you run the project, make sure you have:

- Docker Desktop installed and running
- Python 3.10+ installed
- pip available

## Setup

1. Open the project folder.
2. Make sure the environment file is present at the project root as `.env`.
3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Start the database services and API:

```bash
docker compose up --build
```

This will start:

- the FastAPI service on port `8080`
- PostgreSQL on port `5432`
- Redis on port `6380`

The app will create the database tables automatically when it starts.

## Running locally

If you already have the Docker services running, you can also run the API directly:

```bash
uvicorn main:app --reload
```

The app will be available at:

- http://localhost:8080/
- http://localhost:8080/docs


## Database setup

The project uses PostgreSQL and Redis.

### PostgreSQL

- container name: `postgres_container`
- default database: `seevees`
- default user: `postgres`

### Redis

- container name: `redis_container`

### Notes

- The database schema is created automatically on startup through SQLAlchemy metadata.
- If you need to change DB connection values, update the `.env` file before starting Docker Compose.

## Data model

The core models live under the models folder and are fairly simple. The schema is centered around employers creating tests, candidates being assigned to those tests, and submissions being stored once the assessment is completed.

```text
+------------------+        1      1..*        +------------------+
| User             |<----------------------->| Test             |
|------------------|                        |------------------|
| id               |                        | id               |
| email            |                        | created_by_id    |
| password_hash    |                        | title            |
| role             |                        | pass_score       |
| first_name       |                        | duration_minutes |
| last_name        |                        | deleted          |
| created_at       |                        | created_at       |
+------------------+                        +------------------+
        |                                      |
        | 1..*                                 | 1..*
        v                                      v
+------------------+                    +------------------+
| TestAssignment  |                    | Question         |
|------------------|                    |------------------|
| id               |                    | id               |
| test_id          |                    | test_id          |
| candidate_email  |                    | type             |
| unique_token     |                    | content          |
| status           |                    | options          |
| expires_at       |                    | test_cases       |
| created_at       |                    | correct_answer   |
+------------------+                    | points           |
        |                                | created_at       |
        | 0..1                           +------------------+
        v
+------------------+
| Submission      |
|------------------|
| id               |
| assignment_id    |
| candidate_email  |
| score            |
| is_passed        |
| answers          |
| submission_breakdown |
| submitted_at     |
+------------------+
```

In plain terms:

- one User can create many Tests
- one Test has many Questions
- one Test can have many TestAssignments
- one TestAssignment can have one Submission
- candidates are represented by their email address in assignments and submissions, not as separate User records

## API documentation

The project exposes a basic API structure under `/api/v1`.

### Authentication

Base path:

```text
/api/v1/auth
```

Endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

Example register request:

```bash
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "employer@example.com",
    "password": "strongpassword",
    "first_name": "Jane",
    "last_name": "Doe",
    "role": "EMPLOYER"
  }'
```

Example login request:

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "employer@example.com",
    "password": "strongpassword"
  }'
```

### Employer endpoints

Base path:

```text
/api/v1/employer
```

Common employer routes:

- `POST /api/v1/employer/tests/create`
- `POST /api/v1/employer/tests/assign`
- `GET /api/v1/employer/tests`
- `GET /api/v1/employer/tests/{test_id}`
- `GET /api/v1/employer/tests/{test_id}/submissions`
- `DELETE /api/v1/employer/tests/{test_id}`
- `PATCH /api/v1/employer/tests/{test_id}/questions`

Example create test request:

```bash
curl -X POST http://localhost:8080/api/v1/employer/tests/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Backend Assessment",
    "duration_minutes": 45,
    "pass_score": 70
  }'
```

### Candidate assessment endpoints

Base path:

```text
/api/v1/assessment
```

Routes:

- `POST /api/v1/assessment/instructions`
- `POST /api/v1/assessment/take`
- `POST /api/v1/assessment/save-draft`
- `POST /api/v1/assessment/submit`
- `GET /api/v1/assessment/result/{submission_id}`

Example take assessment request:

```bash
curl -X POST http://localhost:8080/api/v1/assessment/take \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<assignment-token>"
  }'
```

### Admin endpoints

Base path:

```text
/api/v1/admin
```

Routes:

- `GET /api/v1/admin/tests`
- `GET /api/v1/admin/submissions`

## Notes for development

- The app uses FastAPI and SQLAlchemy with async support.
- The service is structured around routers, services, models, and shared utilities.
- The startup flow creates database tables automatically and initializes Redis connectivity.

## Troubleshooting

If the app does not start:

- check that Docker is running
- confirm the `.env` file exists and has valid values
- check the container logs with:

```bash
docker compose logs -f
```
