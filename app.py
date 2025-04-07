import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from news_fetcher import fetch_security_news
from ai_analyzer import analyze_security_news, get_risk_level
import os
from dotenv import load_dotenv
import logging

# Configure logging to not show sensitive information
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # Remove potentially sensitive fields
    filters=[lambda record: 'api_key' not in record.getMessage().lower()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check if running in Streamlit Cloud
is_cloud = os.getenv('STREAMLIT_RUNTIME', '') == 'cloud'

# Page configuration
st.set_page_config(
    page_title="Security News Aggregator",
    page_icon="🔒",
    layout="wide"
)

# Initialize session state for news data
if 'news_data' not in st.session_state:
    st.session_state.news_data = pd.DataFrame()

# Database setup
def init_db_if_needed():
    """Initialize the database if it doesn't exist or is empty"""
    try:
        conn = sqlite3.connect('security_news.db')
        cursor = conn.cursor()
        
        # Check if the news table exists and has data
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS news
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 title TEXT,
                 summary TEXT,
                 source TEXT,
                 url TEXT UNIQUE,
                 date TEXT,
                 category TEXT,
                 ai_analysis TEXT,
                 risk_level TEXT)
            ''')
            conn.commit()
            logger.info("Database initialized - table created")
        
        # Check if table is empty
        cursor.execute("SELECT COUNT(*) FROM news")
        if cursor.fetchone()[0] == 0:
            logger.warning("Database is empty - may need to run update")
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
    finally:
        conn.close()

def get_stored_news():
    try:
        conn = sqlite3.connect('security_news.db')
        df = pd.read_sql_query("SELECT * FROM news ORDER BY date DESC", conn)
        logger.info(f"Retrieved {len(df)} news items from database")
        return df
    except Exception as e:
        logger.error(f"Error retrieving news from database: {str(e)}")
        st.error("Error retrieving news from database. Please check the logs.")
        return pd.DataFrame()
    finally:
        conn.close()

def store_news(news_items):
    if news_items.empty:
        logger.warning("No news items to store")
        return
    
    try:
        conn = sqlite3.connect('security_news.db')
        # Check for duplicates before storing
        existing_urls = pd.read_sql_query("SELECT url FROM news", conn)['url'].tolist()
        new_items = news_items[~news_items['url'].isin(existing_urls)]
        
        if not new_items.empty:
            new_items.to_sql('news', conn, if_exists='append', index=False)
            logger.info(f"Stored {len(new_items)} new news items")
        else:
            logger.info("No new news items to store")
    except Exception as e:
        logger.error(f"Error storing news in database: {str(e)}")
        st.error("Error storing news in database. Please check the logs.")
    finally:
        conn.close()

def display_news_item(row):
    with st.expander(f"{row['title']} - {row['date'].strftime('%Y-%m-%d')}"):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"**Source:** {row['source']}")
            st.markdown(f"**Category:** {row['category']}")
            risk_color = {
                'Critical': 'red',
                'High': 'orange',
                'Medium': 'yellow',
                'Low': 'green',
                'Unknown': 'gray'
            }.get(row['risk_level'], 'gray')
            st.markdown(f"**Risk Level:** :{risk_color}[{row['risk_level']}]")
            st.markdown(f"[Read more]({row['url']})")
        
        with col2:
            st.markdown("**Summary:**")
            st.markdown(row['summary'])
            st.markdown("**AI Analysis:**")
            st.markdown(row['ai_analysis'])

def display_critical_cves(news_df):
    st.subheader("🚨 Critical CVE Alerts")
    critical_cves = news_df[
        (news_df['risk_level'] == 'Critical') & 
        (news_df['title'].str.contains('CVE-', case=False, na=False) | 
         news_df['summary'].str.contains('CVE-', case=False, na=False))
    ]
    
    if not critical_cves.empty:
        for _, row in critical_cves.iterrows():
            with st.container():
                st.markdown(f"""
                <div style='padding: 10px; border-left: 5px solid red; background-color: #ffebee;'>
                    <h4 style='color: #c62828; margin: 0;'>{row['title']}</h4>
                    <p><strong>Date:</strong> {row['date'].strftime('%Y-%m-%d')}</p>
                    <p><strong>Summary:</strong> {row['summary']}</p>
                    <p><a href="{row['url']}" target="_blank">Read more →</a></p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("---")
    else:
        st.info("No critical CVEs found in the current time period.")

def paginate_dataframe(df, page_size, page_number):
    start_idx = page_number * page_size
    end_idx = start_idx + page_size
    return df.iloc[start_idx:end_idx]

# Main app
def main():
    st.title("🔒 Security News Aggregator")
    st.markdown("### Daily Security Updates for Security Teams")
    
    # Initialize database only once
    init_db_if_needed()
    
    # Initialize session state for pagination
    if 'archive_page' not in st.session_state:
        st.session_state.archive_page = 0
    
    # Sidebar for controls
    with st.sidebar:
        st.header("Controls")
        
        # Only show fetch button in local development
        if not is_cloud:
            if st.button("🔄 Fetch Latest News"):
                with st.spinner("Fetching latest security news..."):
                    try:
                        new_news = fetch_security_news()
                        if not new_news.empty:
                            new_news['ai_analysis'] = new_news.apply(
                                lambda row: analyze_security_news(row['title'], row['summary']), 
                                axis=1
                            )
                            new_news['risk_level'] = new_news['ai_analysis'].apply(get_risk_level)
                            store_news(new_news)
                            st.success("News updated successfully!")
                        else:
                            st.warning("No new news found.")
                    except Exception as e:
                        logger.error(f"Error fetching news: {type(e).__name__}")  # Log error type only
                        st.error("Error fetching news. Please check the logs.")
        else:
            st.info("News updates are automated and run daily. Manual updates are disabled in production.")
        
        st.markdown("---")
        st.header("Filter Options")
        
        # Calculate date ranges
        today = datetime.now().date()
        ninety_days_ago = today - timedelta(days=90)
        
        date_filter = st.date_input(
            "Show news from",
            value=ninety_days_ago,
            min_value=ninety_days_ago,
            max_value=today,
            help="Select a date to filter news (up to 90 days old)"
        )
        
        # Show date range info
        st.info(f"Showing news from {ninety_days_ago.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")
        
        category_filter = st.multiselect(
            "Filter by category",
            options=["Vulnerabilities", "Breaches", "Threat Intelligence", "Compliance", 
                    "Cloud Security", "Privacy", "Identity & Access", "All"],
            default=["All"]
        )
        
        risk_filter = st.multiselect(
            "Filter by risk level",
            options=["Critical", "High", "Medium", "Low", "Unknown", "All"],
            default=["All"]
        )
    
    # Get stored news
    news_df = get_stored_news()
    
    if not news_df.empty:
        # Convert date column to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(news_df['date']):
            news_df['date'] = pd.to_datetime(news_df['date'])
        
        # Filter by date (last 90 days)
        ninety_days_ago_dt = pd.to_datetime(ninety_days_ago)
        news_df = news_df[news_df['date'].dt.date >= ninety_days_ago_dt.date()]
        
        # Sort by date descending
        news_df = news_df.sort_values('date', ascending=False)
        
        # Create tabs for today's news and archive
        today_tab, archive_tab = st.tabs(["📰 Today's Security News", "🗄️ Security News Archive (90 Days)"])
        
        with today_tab:
            # Filter for today's news
            today_news = news_df[news_df['date'].dt.date == today]
            
            if not today_news.empty:
                # Display Critical CVEs first for today
                display_critical_cves(today_news)
                
                st.subheader("Today's Latest Security News")
                # Apply filters
                if "All" not in category_filter:
                    today_news = today_news[today_news['category'].isin(category_filter)]
                if "All" not in risk_filter:
                    today_news = today_news[today_news['risk_level'].isin(risk_filter)]
                
                # Display today's news
                for _, row in today_news.iterrows():
                    display_news_item(row)
            else:
                st.info("No news items found for today. Click 'Fetch Latest News' to check for updates.")
        
        with archive_tab:
            # Filter for archive news (excluding today)
            archive_news = news_df[news_df['date'].dt.date < today]
            
            if not archive_news.empty:
                # Display Critical CVEs first for archive
                display_critical_cves(archive_news)
                
                st.subheader(f"Security News Archive ({ninety_days_ago.strftime('%Y-%m-%d')} to {(today - timedelta(days=1)).strftime('%Y-%m-%d')})")
                # Apply filters
                if "All" not in category_filter:
                    archive_news = archive_news[archive_news['category'].isin(category_filter)]
                if "All" not in risk_filter:
                    archive_news = archive_news[archive_news['risk_level'].isin(risk_filter)]
                
                # Display archive news with pagination
                items_per_page = 20
                total_pages = len(archive_news) // items_per_page + (1 if len(archive_news) % items_per_page > 0 else 0)
                
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        page_number = st.number_input(
                            f"Page (1-{total_pages})", 
                            min_value=1, 
                            max_value=total_pages, 
                            value=st.session_state.archive_page + 1
                        ) - 1
                        st.session_state.archive_page = page_number
                
                # Display paginated archive news
                paginated_news = paginate_dataframe(archive_news, items_per_page, st.session_state.archive_page)
                for _, row in paginated_news.iterrows():
                    display_news_item(row)
                
                if total_pages > 1:
                    st.markdown(f"*Showing page {st.session_state.archive_page + 1} of {total_pages}*")
            else:
                st.info("No archived news items found in the selected date range.")
    else:
        st.info("No news items found. Click 'Fetch Latest News' to get started.")

if __name__ == "__main__":
    main() 
