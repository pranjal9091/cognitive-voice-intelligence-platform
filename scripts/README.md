# Utility Scripts

This folder contains command-line interface utilities to support development setup and database actions.

---

## 📁 File Summary

```
scripts/
├── README.md           # This documentation
├── setup_dev.sh        # Automates creation of virtual environments & dependencies installation
└── db_init.py          # Relational tables setup script using SQLAlchemy models
```

---

## 🚀 Script Usage

### 1. Developer Setup Script (`setup_dev.sh`)
This script initializes local environment parameters, validates dependencies, instantiates the python environment, and copies env templates.

```bash
# Make executable
chmod +x scripts/setup_dev.sh

# Run
./scripts/setup_dev.sh
```

### 2. Database Initialization (`db_init.py`)
This script uses the declarative configurations in `database/models/` to build empty relational structures in PostgreSQL. Make sure PostgreSQL is running and `DATABASE_URL` is defined in `.env` before running.

```bash
# Run
python scripts/db_init.py
```
