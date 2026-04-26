# Technical Analysis: Quantum Jobs Tracker Data Pipeline

## 1. Architecture Overview
The Quantum Jobs Tracker is built using a modular **Collector-Adapter** architecture. This design pattern separates the high-level orchestration of the data pipeline from the low-level details of interacting with various job board APIs.

### Core Components
*   **Orchestrator (`quantum_jobs/collector.py`)**: This is the heart of the system. It manages the lifecycle of a collection run: initializing the database, running migrations, iterating through job sources, and managing the state transitions (snapshots → changes → current).
*   **Source Adapters (`quantum_jobs/sources/`)**: These are platform-specific classes (e.g., `GreenhouseBoardSource`, `LeverPostingsSource`) that handle API communication and data normalization. They follow a common protocol, making it easy to plug in new sources.
*   **Canonical Data Model (`quantum_jobs/models.py`)**: The `NormalizedJob` dataclass defines the standard format for job data within the pipeline. This abstraction layer ensures that the storage and analysis logic remains decoupled from the source API's JSON structure.
*   **Database Schema (`quantum_jobs/db/`)**: The system uses SQLite with a schema designed for longitudinal analysis:
    *   `job_snapshots`: A full historical record of every job seen in every pull.
    *   `job_changes`: A ledger of every job addition, removal, or update detected between pulls.
    *   `job_current`: A "live" view of currently active job postings.

## 2. Data Flow
Data flows through the system in a strictly linear pipeline:

1.  **Trigger**: The process is initiated via `scripts/run_collector.py`.
2.  **Extraction**: The orchestrator triggers each source. Adapters use the `requests` library to fetch raw JSON from public, unauthenticated career site APIs (Greenhouse/Lever).
3.  **Normalization**: Raw JSON is mapped into `NormalizedJob` objects. This step includes data cleaning (whitespace stripping, standardizing nulls) and extracting metadata like "Workplace Type" or "Department" from nested structures.
4.  **Historical Archiving**: Every job in the current fetch is saved into `job_snapshots`.
5.  **Differential Analysis**: The orchestrator fetches the *previous* snapshot for the company and compares it to the *new* fetch.
    *   It identifies **Added** (new IDs), **Removed** (missing IDs), and **Changed** (updated metadata) jobs.
    *   These events are recorded in `job_changes` with a timestamp and a JSON blob of the diff.
6.  **State Update**: The `job_current` table is updated via an `UPSERT` operation, ensuring it always reflects the most recent state.
7.  **Analysis**: Researchers use the SQL queries in `analysis/sql/` and Jupyter notebooks in `analysis/notebooks/` to transform these raw logs into strategic insights.

## 3. Dependency Analysis
*   **Runtime**:
    *   `sqlite3`: Chosen for its zero-configuration setup and portability, perfectly suited for a solo/research project.
    *   `requests`: Used for robust HTTP communication with job board APIs.
*   **Analysis**:
    *   `pandas`: Used for data manipulation and "canonicalizing" daily counts (handling multiple pulls per day).
    *   `matplotlib` & `plotly`: Used for trend visualization and stackplots of hiring by department.
*   **Maintenance**:
    *   `pytest`: The project maintains a high-quality test suite covering database logic, migrations, and model normalization.

---

## 4. Evaluation

### Functionality: **Strong**
The system excels at its primary goal: generating longitudinal data. Unlike a simple scraper that only shows "what is live now," this system's change-detection engine allows for tracking the "velocity" of hiring—how fast roles are opened and closed—which is a much stronger strategic signal.

### Adaptability: **High**
The codebase is exceptionally easy to extend. Adding a new company on a supported platform is a one-line change in `collector.py`. The "Phase 5" refactor has removed all legacy shims, leaving a clean, package-first structure that is easy to modify without side effects.

### Usability: **Excellent (Technical)**
For a technical user or data scientist, the system is a pleasure to use. It features:
*   Canonical entry points (CLI tools).
*   A robust migration system that handles schema evolution.
*   Well-commented analysis queries that account for data "noise" (like duplicate daily pulls).

### Risk: **Moderate**
*   **External Fragility**: The system relies on "shadow" APIs. If Greenhouse or Lever changes their public endpoint structure, the adapters will require updates.
*   **Scalability**: While SQLite is efficient, the `job_snapshots` table grows linearly with every pull. Over years of daily pulls for hundreds of companies, this may eventually require a transition to a more scalable backend like PostgreSQL.

### Commercialization Potential
This project is an ideal MVP for a Quantum Research & Intelligence platform. To take it to market, I recommend:
1.  **AI Layer**: Use an LLM to categorize jobs by "Qubit Modality" (e.g., Ion Trap vs. Neutral Atom) by scanning the full job description in `raw_json`.
2.  **Alerting**: Implement a notification engine (Slack/Email) that alerts subscribers when competitors post "Leadership" or "Strategic" roles.
3.  **Cloud Native**: Move from local execution to a scheduled cloud function (e.g., AWS Lambda) with a simple web dashboard for non-technical subscribers.

---

*Note: During this analysis, a critical bug was identified and fixed in `collector.py` where migrations were being triggered before the database schema was initialized. This fix is included in the submitted code.*
