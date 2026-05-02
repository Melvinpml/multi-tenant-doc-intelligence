# Project Structure

This project is currently a FastAPI backend scaffold for a multi-tenant document intelligence API.

```text
multi-tenant-doc-intelligence/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       └── __init__.py
│   ├── core/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── worker/
│       └── __init__.py
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── main.py
├── README.md
└── requirements.txt
```

## Directory Guide

| Path | Purpose |
| --- | --- |
| `app/` | Main application package. |
| `app/api/` | API routing layer. |
| `app/api/v1/` | Versioned API routes for version 1 endpoints. |
| `app/core/` | Core application configuration, settings, security, and shared infrastructure. |
| `app/models/` | Database models, likely SQLAlchemy models. |
| `app/schemas/` | Request and response schemas, likely Pydantic models. |
| `app/services/` | Business logic and service-layer code. |
| `app/worker/` | Background task or document processing worker code. |

## Root Files

| File | Purpose |
| --- | --- |
| `.env` | Local environment variables. This should not be committed. |
| `.env.example` | Example environment configuration for other developers. |
| `.gitignore` | Files and folders excluded from version control. |
| `docker-compose.yml` | Docker Compose services, expected to include the API and PostgreSQL later. |
| `Dockerfile` | Container image definition for the API service. |
| `main.py` | FastAPI application entry point. |
| `README.md` | Project overview and setup documentation. |
| `requirements.txt` | Python package dependencies. |

## Notes

- The `venv/` directory exists locally but is ignored from this structure because it is an environment artifact, not project source.
- Most files are currently empty placeholders, so this structure represents the intended architecture rather than a fully implemented application.
