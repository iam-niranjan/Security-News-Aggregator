#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from news_fetcher import fetch_security_news
from ai_analyzer import analyze_security_news, get_risk_level
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database if it doesn't exist"""
    try:
        conn = sqlite3.connect('security_news.db')
        c = conn.cursor()
        c.execute('''
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
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def store_news(news_items):
    """Store news items in the database, avoiding duplicates"""
    try:
        conn = sqlite3.connect('security_news.db')
        cursor = conn.cursor()

        # Track statistics
        new_items_count = 0
        existing_items_count = 0
        error_items_count = 0

        logger.info(f"Processing {len(news_items)} news items for database storage")

        for _, row in news_items.iterrows():
            try:
                # Check if URL already exists
                cursor.execute("SELECT url FROM news WHERE url = ?", (row['url'],))
                if cursor.fetchone() is None:
                    # Add AI analysis
                    ai_analysis = analyze_security_news(row['title'], row['summary'])
                    risk_level = get_risk_level(ai_analysis)

                    # Ensure date is in correct format (YYYY-MM-DD)
                    # If date is already a string, use it directly
                    if isinstance(row['date'], str):
                        date_str = row['date']
                    else:
                        # If it's a datetime object, format it
                        date_str = row['date'].strftime('%Y-%m-%d')

                    logger.info(f"Storing article with date: {date_str}")

                    # Insert new item
                    cursor.execute('''
                        INSERT INTO news (title, summary, source, url, date, category, ai_analysis, risk_level)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['title'],
                        row['summary'],
                        row['source'],
                        row['url'],
                        date_str,
                        row['category'],
                        ai_analysis,
                        risk_level
                    ))
                    new_items_count += 1
                    logger.info(f"Added new article: {row['title']} from {row['source']} with date {date_str}")
                else:
                    existing_items_count += 1
                    logger.debug(f"Skipping existing article: {row['title']} from {row['source']}")
            except Exception as e:
                error_items_count += 1
                logger.error(f"Error processing article {row['title']}: {str(e)}")
                continue

        conn.commit()
        logger.info(f"News database updated: {new_items_count} new articles added, {existing_items_count} existing articles skipped, {error_items_count} errors")
    except Exception as e:
        logger.error(f"Error storing news: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def cleanup_old_news():
    """Remove news items older than 90 days"""
    try:
        conn = sqlite3.connect('security_news.db')
        cursor = conn.cursor()

        # Delete items older than 90 days
        cursor.execute("""
            DELETE FROM news
            WHERE date < date('now', '-90 days')
        """)

        deleted_count = cursor.rowcount
        conn.commit()
        logger.info(f"Removed {deleted_count} old news items")
    except Exception as e:
        logger.error(f"Error cleaning up old news: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def update_article_dates():
    """Update article dates to ensure consistency"""
    try:
        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')

        conn = sqlite3.connect('security_news.db')
        cursor = conn.cursor()

        # Check for articles with yesterday's date that should be today
        # Use LIKE to match partial date strings (handles both '2025-04-06' and '2025-04-06 00:00:00' formats)
        cursor.execute("""
            SELECT id, title, source, date FROM news
            WHERE date LIKE ? AND source = 'The Hacker News'
        """, (f"{yesterday_str}%",))

        yesterday_articles = cursor.fetchall()
        updated_count = 0

        if yesterday_articles:
            logger.info(f"Found {len(yesterday_articles)} articles with yesterday's date that might need updating")

            for article_id, title, source, date in yesterday_articles:
                # Update to today's date (preserve time part if it exists)
                if ' ' in date:  # Has time component
                    new_date = f"{today_str} {date.split(' ')[1]}"
                else:
                    new_date = today_str

                cursor.execute("UPDATE news SET date = ? WHERE id = ?", (new_date, article_id))
                updated_count += 1
                logger.info(f"Updated date for article: {title} from {date} to {new_date}")

            conn.commit()
            logger.info(f"Updated dates for {updated_count} articles")
        else:
            # Check for articles with incorrect date formats
            cursor.execute("""
                SELECT id, title, date FROM news
                WHERE date NOT LIKE '____-__-__%' AND source = 'The Hacker News'
            """)

            bad_format_articles = cursor.fetchall()
            if bad_format_articles:
                logger.info(f"Found {len(bad_format_articles)} Hacker News articles with incorrect date format")

                for article_id, title, date in bad_format_articles:
                    # Try to fix the date format
                    try:
                        # If it's a timestamp format, convert to YYYY-MM-DD
                        if ' ' in date:
                            date_part = date.split(' ')[0]
                            if '-' in date_part and len(date_part) == 10:  # YYYY-MM-DD format
                                new_date = date
                            else:
                                # Default to original publication date if possible
                                new_date = date
                        else:
                            new_date = date

                        cursor.execute("UPDATE news SET date = ? WHERE id = ?", (new_date, article_id))
                        updated_count += 1
                        logger.info(f"Fixed date format for article: {title} from {date} to {new_date}")
                    except Exception as e:
                        logger.error(f"Error fixing date format for article {title}: {str(e)}")

                conn.commit()
                logger.info(f"Fixed date formats for {updated_count} articles")
            else:
                logger.info("No articles found with incorrect date formats")

    except Exception as e:
        logger.error(f"Error updating article dates: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function to update news database"""
    try:
        logger.info("Starting news update process")

        # Initialize database if needed
        init_db()

        # Set target date to today
        today = datetime.now().date()
        logger.info(f"Fetching news specifically for today: {today}")

        # Fetch today's articles
        news_items = fetch_security_news(target_date=today)

        # If no today's articles found, try fetching without date filter as fallback
        if news_items.empty:
            logger.info("No articles found for today, fetching latest news as fallback")
            news_items = fetch_security_news()

        if not news_items.empty:
            # Store new articles
            store_news(news_items)

            # Update article dates if needed
            update_article_dates()

            # Cleanup old articles
            cleanup_old_news()

            logger.info("News update completed successfully")
        else:
            logger.warning("No new articles found")

    except Exception as e:
        logger.error(f"Error in main update process: {str(e)}")
        raise

if __name__ == "__main__":
    main()