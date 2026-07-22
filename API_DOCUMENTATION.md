# API Documentation

This file gives a simple reference for the main API routes in SeeVees, explaining their roles, inputs, and behaviors.

## Base URL

```text
eg: http://seevees.api.com
```

## Authentication

Most employer and admin endpoints require a bearer token. Tokens are returned by the auth login and register endpoints.

### Register
Registers a new platform user with administrative or employer privileges. Candidate accounts do not exist on the platform.

```http
POST /api/v1/auth/register
Content-Type: application/json
```

Example body:

```json
{
  "email": "employer@example.com",
  "password": "strongpassword",
  "first_name": "Jane",
  "last_name": "Doe",
  "role": "EMPLOYER"
}
```

### Login
Authenticates an existing user and returns a temporary JWT access token required for subsequent authorized calls.

```http
POST /api/v1/auth/login
Content-Type: application/json
```

Example body:

```json
{
  "email": "employer@example.com",
  "password": "strongpassword"
}
```

## Employer routes

### Create test
Creates a new test profile record. This defines core constraints such as test duration limits and passing scores.

```http
POST /api/v1/employer/tests/create
Authorization: Bearer <token>
Content-Type: application/json
```

Example body:

```json
{
  "title": "Backend Assessment",
  "duration_minutes": 45,
  "pass_score": 70
}
```

### Assign test to candidate
Creates a unique, temporary assessment assignment token linked to a candidate's email. Triggers a background process that emails the candidate an invitation with their unique link.

```http
POST /api/v1/employer/tests/assign
Authorization: Bearer <token>
Content-Type: application/json
```

Example body:

```json
{
  "test_id": 1,
  "candidate_email": "candidate@example.com",
  "expires_in_hours": 48
}
```

### List employer tests
Retrieves a paginated list of all test profiles created by the authenticated employer.

```http
GET /api/v1/employer/tests
Authorization: Bearer <token>
```

### Get one test
Retrieves a detailed view of a specific test profile (including questions) owned by the authenticated employer.

```http
GET /api/v1/employer/tests/{test_id}
Authorization: Bearer <token>
```

### Get submissions for one test
Fetches a paginated summary of all candidate scores and submissions associated with a specific test profile.

```http
GET /api/v1/employer/tests/{test_id}/submissions
Authorization: Bearer <token>
```

Query params:

- `start` (optional, default `0`)
- `limit` (optional, default `10`)

### Update test questions
Overwrites or inserts questions (multiple choice or coding) associated with an active test.

```http
PATCH /api/v1/employer/tests/{test_id}/questions
Authorization: Bearer <token>
Content-Type: application/json
```

Example body:

```json
{
  "questions": [
    {
      "type": "MCQ",
      "content": "Which option is correct?",
      "correct_answer": "A",
      "points": 10,
      "options": {
        "A": "Option A",
        "B": "Option B"
      }
    }
  ]
}
```

### Delete test
Soft-deletes a test by marking it as deleted and invalidates all pending candidate assignment tokens.

```http
DELETE /api/v1/employer/tests/{test_id}
Authorization: Bearer <token>
```

## Candidate assessment routes
*Note: No authentication headers are required for candidate routes. The assignment token acts as the access credential.*

### Get instructions
Loads test metadata (test title, duration, deadline, candidate email) using the unique token. Allows the client to show instructions before starting the test timer.

```http
POST /api/v1/assessment/instructions
Content-Type: application/json
```

Example body:

```json
{
  "token": "<assignment-token>"
}
```

### Take assessment
Begins the test session. It marks the assignment status as `STARTED`, initializes the session timer in Redis, and returns the questions (with answers/test cases stripped out to prevent cheating).

```http
POST /api/v1/assessment/take
Content-Type: application/json
```

Example body:

```json
{
  "token": "<assignment-token>"
}
```

### Save progress draft
Saves the candidate's intermediate answers to the database telemetry table. Protects against browser crashes or network drops.

```http
POST /api/v1/assessment/save-draft
Content-Type: application/json
```

Example body:

```json
{
  "token": "<assignment-token>",
  "answers": {
    "q1": "B",
    "q2": "Draft text content"
  }
}
```

### Submit assessment
Finalizes and grades the assessment. Calculates scores, inserts a graded `Submission` record, marks the assignment as `SUBMITTED`, clears draft telemetry. Sends a permanent results link email to the candidate in the background.

```http
POST /api/v1/assessment/submit
Content-Type: application/json
```

Example body:

```json
{
  "token": "<assignment-token>",
  "answers": {
    "q1": "B",
    "q2": "Python"
  }
}
```

### View submission result
Retrieves the final score and question-by-question scoring breakdown. This is a public view accessible by anyone with the submission UUID (e.g. from the emailed link).

```http
GET /api/v1/assessment/result/{submission_id}
```

## Admin routes

### List all tests
Retrieves a paginated list of all test profiles created across the entire platform.

```http
GET /api/v1/admin/tests
Authorization: Bearer <token>
```

### List all submissions
Retrieves a paginated list of all candidate test submissions recorded across the entire platform.

```http
GET /api/v1/admin/submissions
Authorization: Bearer <token>
```
