# market-data-etl-pipeline

A compact, well-documented dataset and supporting SQL for a sample financial data warehouse used for learning and prototyping data engineering, analytics, and BI workflows.

## Contents

- `schema/` - SQL schema and table definitions (DDL).
- `data/` - Sample CSV or Parquet files with mock transactions, accounts, customers, and reference data.
- `etl/` - Example extract-transform-load scripts (Python / SQL / Airflow dags) to populate the data warehouse.
- `analytics/` - Example queries, views, and dashboards (Looker/Metabase/Power BI) for analysis.
- `docs/` - Design notes, ER diagrams, and data dictionary.

## Purpose

This repository is intended to:

- Provide a realistic but small-scale financial dataset for learning data engineering practices.
- Demonstrate best practices in schema design, data modelling (star schema / dimensional modelling), and ETL patterns.
- Offer reusable examples for ingestion, transformation, testing, and analytics.

## Quick start

1. Clone the repo:

	git clone <repo-url>

2. Inspect schema and sample data:

	- Open `schema/` to view table definitions.
	- Open `data/` to preview sample CSVs or Parquet files.

3. Load sample data (example using PostgreSQL):

	- Create a database and user.
	- Run the SQL in `schema/create_tables.sql`.
	- Use `COPY` or `psql` to import CSVs from `data/` into the tables.

4. Run ETL scripts:

	- See `etl/README.md` for commands to execute example pipelines.

5. Run example analytics:

	- Example queries are in `analytics/queries.sql` and can be run from your SQL client.

## Data model

The dataset models a simple transactional financial system with these core entities:

- customers — customer profile and contact data.
- accounts — financial accounts belonging to customers.
- transactions — transactional events (debits, credits) with timestamps and amounts.
- merchants — counterparty data for transactions.
- reference — currencies, transaction types, and other lookup tables.

The analytical model is provided as a set of dimension tables and a fact_transactions table to support common metrics: balance over time, revenue, spend by category, customer LTV, churn, and cohort analysis.

## ETL & Transformation

- Raw ingestion: land raw files in a staging area (S3, local `data/raw/`, or database schema `staging`).
- Transformation: normalize, type-cast, deduplicate, and apply business rules to produce curated tables in `warehouse/` schema.
- Testing: use data quality checks (row counts, null checks, uniqueness, referential integrity) before promoting data.

See `etl/` for ready-to-run examples and Airflow DAGs demonstrating scheduling, retries, and monitoring.

## Examples of queries

- Daily active customers and transaction counts
- Monthly revenue and growth
- Top merchants by spend
- Cohort retention and LTV estimates

Examples live in `analytics/queries.sql` and `analytics/notebooks/`.

## Contributing

Contributions are welcome. Please follow the repository conventions:

- Open an issue to discuss proposed changes.
- Submit a pull request with tests or sample outputs when applicable.
- Keep sample data small and anonymized.

## Licensing

MIT License
