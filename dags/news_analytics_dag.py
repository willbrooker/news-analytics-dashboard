from datetime import datetime, timedelta
import logging
import pandas as pd
import ast
from sqlalchemy import create_engine, inspect, Table, Column, Integer, String, MetaData, JSON
from sqlalchemy.exc import SQLAlchemyError
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator # type: ignore

import news
from sentiment_analysis import analyze_sentiment

#Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

#Database Engine Creation
engine = create_engine('sqlite:////opt/airflow/shared/news_data.db')

#Default Dag Arguments
default_args = {
    "owner" : "user",
    "depends_on_past" : False,
    "email_on_failure" : False,
    "email_on_retry" : False,
    "retries" : 1,
    "retry_delay" : timedelta(minutes = 1)
}

#Dag Definition
dag = DAG(
    "news_analytics",
    default_args=default_args,
    description= "DAG for news analytics database and dashboard",
    schedule = "@hourly",
    start_date = datetime(2024, 8, 1),
    catchup= False
)

#Task Definitions
def scrape_news_task(**kwargs):
    """Scrapes news articles based on the provided query and page size."""
    query = kwargs["query"]
    page_size = kwargs["page_size"]
    api_key = kwargs["api_key"]
    df = news.scrape_news(query, page_size, api_key)
    df.to_csv('/opt/airflow/shared/news_data.csv', index=False)

def process_data_task():
    """Processes the scraped news data by cleaning and transforming it."""
    df = pd.read_csv('/opt/airflow/shared/news_data.csv')
    df.source = df.source.apply(lambda x : ast.literal_eval(x)["name"])
    df.drop(["urlToImage"], axis = 1, inplace = True)
    df.rename(columns={'publishedAt': 'date'}, inplace=True)
    df.date = df.date.apply(lambda x: x[:10])
    df.drop_duplicates(inplace=True)
    df.dropna(subset=['content', 'author'], inplace=True)
    df.to_csv('/opt/airflow/shared/processed_news_data.csv', index=False)

def analyze_data_task():
    """Analyzes sentiment in the processed news data with pretrained transformer model from cardiffnlp"""
    df = pd.read_csv('/opt/airflow/shared/processed_news_data.csv')
    def analyze_sentiment_row(row):
        predicted_class, probabilities = analyze_sentiment(row["content"])
        return pd.Series([predicted_class, probabilities])
    df[['predicted_class', 'probabilities']] = df.apply(analyze_sentiment_row, axis=1)
    df.to_csv('/opt/airflow/shared/processed_news_data_with_sentiment.csv', index=False)

def check_table_exists():
    """Checks if the 'news' table exists in the database."""
    inspector = inspect(engine)
    if inspector.has_table("news"):
        return "skip_create_table"
    else:
        return "create_table"

def create_table():
    """Creates the 'news' table in the database if it doesn't exist."""
    metadata = MetaData()
    news_table = Table("news", metadata,
                       Column("id", Integer, primary_key = True),
                       Column("source", String),
                       Column("author", String),
                       Column("title", String),
                       Column("description", String),
                       Column("url", String),
                       Column("date", String),
                       Column("content", String),
                       Column("predicted_class", Integer),
                       Column("probabilities", JSON),
                       Column("query", String)
    )
    metadata.create_all(engine)

def store_data_task():
    """Stores the processed news data with sentiment analysis into the database."""
    try:
        df = pd.read_csv('/opt/airflow/shared/processed_news_data_with_sentiment.csv')
        conn = engine.connect()
        existing_df = pd.read_sql("SELECT title FROM news", conn)
        new_data = df[~df['title'].isin(existing_df['title'])]
        if not new_data.empty:
            new_data.to_sql("news", con=conn, if_exists="append", index=False)
        else:
            logging.info("No new data to insert.")
        conn.close()
    except SQLAlchemyError as e:
        logging.error(f"Error storing data in the SQLite database: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise


#Task Definitions in DAG
scrape_task = PythonOperator(
    task_id = "scrape_news",
    python_callable = scrape_news_task,
    op_kwargs = {"query": ["artificial intelligence", "election", "stock market", "tech", "economy"], "page_size": 100, "api_key" : "your-actual-api-key"},
    dag=dag
)

process_task = PythonOperator(
    task_id = "process_data",
    python_callable = process_data_task,
    dag=dag
)

analyze_task = PythonOperator(
    task_id = "analyze_data_task",
    python_callable = analyze_data_task,
    dag=dag
)

check_table_exists_task = BranchPythonOperator(
    task_id = "check_table_exists",
    python_callable = check_table_exists,
    dag=dag
)

create_table_task = PythonOperator(
    task_id = "create_table",
    python_callable = create_table,
    dag=dag
)

skip_create_table_task = DummyOperator(
    task_id = "skip_create_table",
    dag=dag
)

join_task = DummyOperator(
    task_id='join', 
    dag=dag, 
    trigger_rule='none_failed_min_one_success')

store_task = PythonOperator(
    task_id = "store_data",
    python_callable = store_data_task,
    dag=dag
)

#Task Dependencies
scrape_task >> process_task >> analyze_task >> check_table_exists_task
check_table_exists_task >> create_table_task >> join_task
check_table_exists_task >> skip_create_table_task >> join_task
join_task >> store_task