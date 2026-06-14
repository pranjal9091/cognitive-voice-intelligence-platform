# Database Module

This module contains the schemas, configuration models, and migration scripts for the Cognitive Voice Intelligence Platform relational database.

---

## 📁 Folder Structure

```
database/
├── README.md               # This documentation
├── schema.sql              # Raw SQL definitions of tables and indices
├── alembic.ini             # Alembic migration settings (future tool configuration)
└── models/                 # SQLAlchemy models
    ├── __init__.py         # Package exports
    ├── session.py          # Session and workflow tables
    ├── audio.py            # Audio metadata file tracking
    ├── analytics.py        # Temporal & Linguistic analytics
    └── risk.py             # Calculated Cognitive Risk scores
```

---

## 🛠️ Schema Initialization

For local testing, you can execute the raw `schema.sql` directly:

```bash
psql -U postgres -d cognitive_voice_db -f database/schema.sql
```

For SQLAlchemy ORM applications, tables can be initialized programmatically using the developer helper script:

```bash
python scripts/db_init.py
```

For production environments, database updates must be managed using Alembic.
