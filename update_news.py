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

                    # Insert new item
                    cursor.execute('''
                        INSERT INTO news (title, summary, source, url, date, category, ai_analysis, risk_level)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['title'],
                        row['summary'],
                        row['source'],
                        row['url'],
                        row['date'].strftime('%Y-%m-%d'),
                        row['category'],
                        ai_analysis,
                        risk_level
                    ))
                    new_items_count += 1
                    logger.info(f"Added new article: {row['title']} from {row['source']}")
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