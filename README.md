\# Quantum Jobs Tracker



A data-driven intelligence tool for analyzing hiring trends across quantum computing companies.



\## Overview



The Quantum Jobs Tracker collects and analyzes job postings from leading quantum computing companies to provide insight into:



\- Company maturity and growth signals

\- Shifts in technical and operational priorities

\- Hiring trends across functions (engineering, research, product, etc.)

\- Market-wide dynamics in the quantum ecosystem



This project is designed as both:

1\. A \*\*quantitative research tool\*\* for analyzing emerging technology markets  

2\. A \*\*framework for competitive intelligence\*\* in frontier industries  



\---



\## Key Features



\- Automated data collection from job board APIs (Greenhouse, Lever, etc.)

\- Structured database of job postings over time

\- Snapshot-based tracking for temporal analysis

\- Visualization of hiring trends and role distribution

\- Modular architecture for adding new companies and data sources



\---



\## Project Structure

Quantum Jobs/

├── collectors/ # Source adapters (Greenhouse, Lever, etc.)

├── Quantum Jobs Collector.py # Main data collection script

├── migration\_utils.py # Database schema management

├── run\_migrations.py # Migration runner

├── query\_db.py # Query utilities

├── \*.ipynb # Analysis and visualization notebooks



\---



\## Data Model



The project maintains a historical snapshot of job postings, enabling:



\- Time-series analysis of hiring trends

\- Detection of organizational shifts

\- Comparison across companies and regions



\---



\## Use Cases



\- Competitive intelligence for quantum computing companies

\- Investment research and market analysis

\- Tracking industry maturity and technical focus areas

\- Evaluating hiring signals as proxies for strategic direction



\---



\## Future Enhancements



\- Expanded company coverage (D-Wave, Pasqal, QuEra, etc.)

\- Improved taxonomy for job classification

\- Automated dashboards and reporting

\- Cross-company comparative analytics

\- Integration with external data sources



\---



\## Notes



\- The database file is not included in the repository

\- Visual outputs and generated data are excluded from version control

\- This repository focuses on code and reproducibility



\---



\## Author



Jacob Fong  

Technology analyst with a focus on emerging technologies, data-driven research, and competitive intelligence.



\---



\## License



(Optional — add later if needed)

