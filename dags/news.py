import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Union, List

def scrape_news(query : Union[str, List[str]] , page_size = 100, api_key = "your-actual-api-key") -> pd.DataFrame:
    """
    Fetches news articles based on a search query and returns them as a pandas DataFrame.

    Parameters:
    query (str or list of str): Search term(s) for the articles.
    page_size (int): Maximum number of articles to retrieve (up to 100).
    api_key (str): NewsAPI key.

    Returns:
    pandas.DataFrame: DataFrame with columns: source, author, description, url, date, and content.

    Example:
    >>> df = scrape_news("climate change", 50, "your_api_key")
    """
    url = "https://newsapi.org/v2/everything"
    date_from = (datetime.now() - timedelta(days=31)).strftime('%Y-%m-%d')
    date_to = datetime.now().strftime('%Y-%m-%d')

    params = {
        "from": date_from,
        "to": date_to,
        "pageSize": page_size,
        "apiKey": api_key
    }

    def scrape_query(q):
        params["q"] = q
        response = requests.get(url, params)
        data = response.json()
        articles_df = pd.DataFrame(data["articles"])
        articles_df["query"] = q
        return articles_df

    if isinstance(query, str):
        return scrape_query(query)
    
    elif isinstance(query, list):
        final_df = pd.DataFrame()
        for q in query:
            query_df = scrape_query(q)
            final_df = pd.concat([final_df, query_df], ignore_index=True)
        return final_df