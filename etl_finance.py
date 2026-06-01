import argparse
import os
from pathlib import Path
from typing import cast

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
_script_dir = Path(__file__).parent.resolve()
_env_path = _script_dir / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv() 

def build_database_url() -> URL:
    """Build a safe PostgreSQL URL without hand-escaping password characters."""
    return URL.create(
        "postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER", "myuser"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres_password"),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "mydatabase"),
    )

def parse_args() -> argparse.Namespace:
    default_tickers = os.getenv("TICKERS", "BTC-USD").split(",")

    parser = argparse.ArgumentParser(description="Load market prices into PostgreSQL.")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=[ticker.strip() for ticker in default_tickers if ticker.strip()],
        help="Ticker symbols to load, for example: BTC-USD AAPL MSFT",
    )
    parser.add_argument("--period", default=os.getenv("YFINANCE_PERIOD", "1mo"))
    parser.add_argument("--interval", default=os.getenv("YFINANCE_INTERVAL", "1d"))
    parser.add_argument("--table", default=os.getenv("TARGET_TABLE", "bitcoin_daily"))
    return parser.parse_args()

def extract_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    print(f"1. Extract: downloading {interval} data for {ticker} over {period}...")
    data = yf.download(ticker, period=period, interval=interval, progress=False)

    if data is None:
        raise RuntimeError(f"yfinance returned no data for ticker {ticker}")

    if data.empty:
        raise RuntimeError(f"yfinance returned no rows for ticker {ticker}")

    return cast(pd.DataFrame, data)

def transform_data(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    print("2. Transform: cleaning and formatting data...")

    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    required_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise RuntimeError(f"Missing expected columns from yfinance: {missing_columns}")

    df = df[required_columns]
    df.insert(0, "Ticker", ticker)
    df.columns = [
        "ticker",
        "date_id",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
    ]

    for column in ["open_price", "high_price", "low_price", "close_price"]:
        df[column] = df[column].round(2)

    return df

def ensure_schema(engine, table_name: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    ticker text NOT NULL,
                    date_id timestamp NOT NULL,
                    open_price double precision,
                    high_price double precision,
                    low_price double precision,
                    close_price double precision,
                    volume bigint
                )
                """
            )
        )
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS ticker text"))
        connection.execute(text(f"UPDATE {table_name} SET ticker = 'BTC-USD' WHERE ticker IS NULL"))
        connection.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN ticker SET NOT NULL"))
        connection.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN date_id SET NOT NULL"))
        connection.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS {table_name}_ticker_date_idx
                ON {table_name} (ticker, date_id)
                """
            )
        )

def create_analytics_view(engine, table_name: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE OR REPLACE VIEW {table_name}_analytics AS
                SELECT
                    ticker,
                    date_id,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    ROUND(
                        AVG(close_price) OVER (
                            PARTITION BY ticker
                            ORDER BY date_id
                            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                        )::numeric,
                        2
                    ) AS moving_avg_7,
                    ROUND(
                        AVG(close_price) OVER (
                            PARTITION BY ticker
                            ORDER BY date_id
                            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                        )::numeric,
                        2
                    ) AS moving_avg_30
                FROM {table_name}
                """
            )
        )

def load_data(engine, df: pd.DataFrame, table_name: str) -> None:
    print(f"3. Load: upserting data into table {table_name}...")
    staging_table = f"{table_name}_staging"

    ensure_schema(engine, table_name)

    df.to_sql(staging_table, engine, if_exists="replace", index=False)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table_name} (
                    ticker,
                    date_id,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                )
                SELECT
                    ticker,
                    date_id,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                FROM {staging_table}
                ON CONFLICT (ticker, date_id) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
                """
            )
        )
        connection.execute(text(f"DROP TABLE IF EXISTS {staging_table}"))

    create_analytics_view(engine, table_name)
    print("Loaded successfully.")

def run_pipeline(tickers: list[str], period: str, interval: str, table_name: str) -> None:
    engine = create_engine(build_database_url())

    for ticker_symbol in tickers:
        raw_df = extract_data(ticker_symbol, period, interval)
        clean_df = transform_data(raw_df, ticker_symbol)
        load_data(engine, clean_df, table_name)

if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.tickers, args.period, args.interval, args.table)
