import streamlit as st
import pandas as pd
import os
import sqlite3
import matplotlib.pyplot as plt
import plotly.express as px

st.set_page_config(layout="wide")

# Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("", ["News Analytics Dashboard", "Database", "About This Project"])

def load_data():
    """Load data from the SQLite database."""
    db_path = os.path.join(os.getcwd()[:-4], "shared", "news_data.db")
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM news"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def display_statistics(df):
    """Display dataset statistics at the top of the dashboard."""
    num_rows = len(df)
    num_unique_authors = df['author'].nunique()
    num_queries = df['query'].nunique() if 'query' in df.columns else 'N/A'
    date_range = f"{df['date'].min()} to {df['date'].max()}"

    st.header("Dataset Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Articles", value=num_rows)
    with col2:
        st.metric(label="Unique Authors", value=num_unique_authors)
    with col3:
        st.metric(label="Queries", value=num_queries)
    st.write(f"**Date Range:** {date_range}")

def filter_data_by_query(df):
    """Filter the dataset based on selected queries."""
    query_options = ["All"] + list(df['query'].unique())
    selected_queries = st.multiselect("Select one or more queries", query_options, default="All")

    if "All" in selected_queries or not selected_queries:
        return df
    else:
        return df[df['query'].isin(selected_queries)]

def plot_sentiment_distribution(df):
    """Plot sentiment distribution by query as a pie chart."""
    st.subheader('Sentiment Distribution by Query')

    sentiment_by_class = df.groupby('predicted_class').size().reset_index(name='counts')
    sentiment_by_class['sentiment'] = sentiment_by_class['predicted_class'].map({
        0: 'Negative',
        1: 'Neutral',
        2: 'Positive'
    })

    color_map = {
        'Negative': 'firebrick',
        'Neutral': 'lightgray',
        'Positive': 'mediumseagreen'
    }

    fig_pie = px.pie(
        sentiment_by_class, 
        values='counts', 
        names='sentiment',
        title='Sentiment Distribution for Selected Queries',
        color='sentiment',
        color_discrete_map=color_map
    )
    
    st.plotly_chart(fig_pie)

def plot_sentiment_by_author(df, top_n=10):
    """Plot sentiment distribution by top N authors."""
    st.subheader(f'Sentiment Distribution by Top {top_n} Authors')

    top_authors = df['author'].value_counts().nlargest(top_n).index

    filtered_df = df[df['author'].isin(top_authors)]

    filtered_df['sentiment'] = filtered_df['predicted_class'].map({
    0: 'Negative',
    1: 'Neutral',
    2: 'Positive'
})
    color_map = {
        'Negative': 'firebrick',
        'Neutral': 'lightgray',
        'Positive': 'mediumseagreen'
    }
    sentiment_by_author = filtered_df.groupby(['author', 'sentiment']).size().unstack(fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 6))
    sentiment_by_author.plot(kind='bar', stacked=True, ax=ax, color=[color_map.get(x) for x in sentiment_by_author.columns])
    ax.set_title(f'Sentiment Distribution by Top {top_n} Authors')
    ax.set_xlabel('Author')
    ax.set_ylabel('Number of Articles')
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)

def display_dashboard():
    """Display the News Analytics Dashboard."""
    st.markdown("<h1 style='text-align: center;'>News Database Analytics Dashboard</h1>", unsafe_allow_html=True)
    
    df = load_data()
    display_statistics(df)
    filtered_df = filter_data_by_query(df)

    col1, col2 = st.columns(2)
    with col1:
        plot_sentiment_distribution(filtered_df)
    with col2:
        top_n = st.slider("Number of authors to display", min_value=5, max_value=20, value=10)
        plot_sentiment_by_author(filtered_df, top_n=top_n)

def display_database():
    """Display the database content."""
    st.title("Database")
    df = load_data()
    st.dataframe(df, height=1000, hide_index=True)

def display_about():
    """Display information about the project."""
    st.title("About This Project")
    
    about_file_path = os.path.join(os.getcwd(), "about_this_project.txt")

    with open(about_file_path, 'r') as file:
        about_text = file.read()
    st.markdown(about_text)

if page == "News Analytics Dashboard":
    display_dashboard()
elif page == "Database":
    display_database()
elif page == "About This Project":
    display_about()