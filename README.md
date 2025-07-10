# Music ETL Pipeline

A comprehensive ETL pipeline for ingesting, processing, and analyzing music streaming data from Spotify, YouTube, and other platforms.

## Architecture

- **Bronze Layer**: Raw data from APIs stored in S3
- **Silver Layer**: Cleaned and standardized data
- **Gold Layer**: Aggregated analytics and insights

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Run tests: `pytest`
5. Start ingestion: `python ingestion/scripts/spotify_ingester.py`

## Development

See [docs/](docs/) for detailed documentation.