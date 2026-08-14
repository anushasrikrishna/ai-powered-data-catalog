# ai-powered-data-catalog
A generic framework that connects to SQL Server, PostgreSQL and Snowflake, automatically documents datasets, helps users discover relevant tables, runs data-quality checks and explains the results using a locally hosted AI model.

## Phase 2 connectors (Person 1)

This phase implements backend connectors for SQL Server and PostgreSQL using a shared connector interface.

### SQL Server
- SQLAlchemy 2.x
- pyodbc DBAPI
- Microsoft ODBC Driver 18 for SQL Server (installed on the local machine)

### PostgreSQL
- SQLAlchemy 2.x
- psycopg 3 DBAPI

### Required environment variables

SQL Server:
- `SQLSERVER_SERVER`
- `SQLSERVER_PORT` (default: `1433`)
- `SQLSERVER_DATABASE`
- `SQLSERVER_USERNAME`
- `SQLSERVER_PASSWORD`
- `SQLSERVER_DRIVER` (default: `ODBC Driver 18 for SQL Server`)
- `SQLSERVER_ENCRYPT`
- `SQLSERVER_TRUST_SERVER_CERTIFICATE`

PostgreSQL:
- `POSTGRES_HOST`
- `POSTGRES_PORT` (default: `5432`)
- `POSTGRES_DATABASE`
- `POSTGRES_USERNAME`
- `POSTGRES_PASSWORD`

### Running connector tests

Run unit tests:

```bash
python -m unittest discover -s tests -p "test_*connector.py" -v
```

Optional integration smoke tests (only when local databases are available):

```bash
# Windows cmd example
set RUN_SQLSERVER_INTEGRATION_TESTS=1
set RUN_POSTGRES_INTEGRATION_TESTS=1
python -m unittest discover -s tests -p "test_*connector.py" -v
```

## Phase 4 documentation backend (Person 1)

The deterministic documentation backend consumes Phase 3 `TableMetadata` objects and produces structured table summaries, profile passthrough fields, and rule-based possible column categories. It requires no database connection or AI service. The supported categories are `Identifier`, `Contact Information`, `Date/Time`, `Financial/Measure`, `Quantity/Measure`, `Boolean/Flag`, `Name`, `Location`, `Text/Description`, and `Other`.
