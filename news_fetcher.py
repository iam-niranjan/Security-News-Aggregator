import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
import logging
from requests.exceptions import RequestException
import time

# Configure logging to avoid sensitive data
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_date(date_str, source):
    """
    Parse date string from different sources into a standardized format
    """
    try:
        if source == 'The Hacker News':
            # Example: "2 days ago" or "5 hours ago"
            if 'ago' in date_str.lower():
                num = int(re.search(r'\d+', date_str).group())
                if 'day' in date_str.lower():
                    return (datetime.now() - timedelta(days=num)).strftime('%Y-%m-%d')
                elif 'hour' in date_str.lower():
                    return datetime.now().strftime('%Y-%m-%d')
            return datetime.now().strftime('%Y-%m-%d')
        elif source == 'Security Week':
            # Handle both ISO format and simple date format
            try:
                # Try ISO format first
                return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
            except ValueError:
                # If that fails, try simple date format
                return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
        else:
            return datetime.now().strftime('%Y-%m-%d')
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}' from {source}: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d')

def fetch_security_news(target_date=None):
    """Fetch security news from various sources"""
    try:
        logger.info(f"Fetching security news for {'latest' if target_date is None else target_date}")

        # Initialize empty list to store news items
        news_items = []

        # Fetch from Security Week
        try:
            security_week_items = fetch_security_week(target_date)
            logger.info(f"Retrieved {len(security_week_items)} items from Security Week")
            news_items.extend(security_week_items)
        except Exception as e:
            logger.error(f"Security Week fetch error: {type(e).__name__}")  # Log error type only

        # Fetch from The Hacker News
        try:
            hacker_news_items = fetch_hacker_news(target_date)
            logger.info(f"Retrieved {len(hacker_news_items)} items from The Hacker News")
            news_items.extend(hacker_news_items)
        except Exception as e:
            logger.error(f"Hacker News fetch error: {type(e).__name__}")  # Log error type only

        # Convert to DataFrame
        if news_items:
            df = pd.DataFrame(news_items)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=False)
            return df
        else:
            logger.warning("No news items found")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"General fetch error: {type(e).__name__}")  # Log error type only
        return pd.DataFrame()

def categorize_news(title, summary):
    """
    Categorize news based on title and summary content.
    Returns the most appropriate category.
    """
    # Keywords for different categories
    categories = {
        'Vulnerabilities': ['vulnerability', 'exploit', 'CVE', 'patch', 'security flaw', 'zero-day'],
        'Breaches': ['breach', 'leak', 'hack', 'stolen', 'exposed', 'compromised'],
        'Threat Intelligence': ['malware', 'ransomware', 'phishing', 'APT', 'threat actor', 'campaign'],
        'Compliance': ['GDPR', 'compliance', 'regulation', 'standard', 'framework', 'audit'],
        'Cloud Security': ['cloud', 'AWS', 'Azure', 'GCP', 'container', 'kubernetes'],
        'Privacy': ['privacy', 'data protection', 'encryption', 'PII', 'personal data'],
        'Identity & Access': ['authentication', 'authorization', 'IAM', 'identity', 'access control', 'SSO']
    }

    # Convert text to lowercase for case-insensitive matching
    title_lower = title.lower()
    summary_lower = summary.lower()

    # Check each category's keywords
    category_scores = {}
    for category, keywords in categories.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in title_lower:
                score += 2  # Title matches are weighted more
            if keyword.lower() in summary_lower:
                score += 1
        category_scores[category] = score

    # Get category with highest score
    max_score = max(category_scores.values())
    if max_score > 0:
        # If there are multiple categories with the same score, prioritize based on order
        for category in categories.keys():
            if category_scores[category] == max_score:
                return category

    # Default category if no keywords match
    return "Threat Intelligence"

def fetch_security_week(target_date=None):
    """Fetch news from Security Week"""
    try:
        url = "https://www.securityweek.com"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('article', class_='article')

        news_items = []
        for article in articles:
            try:
                title = article.find('h2').text.strip()
                summary = article.find('div', class_='article-summary').text.strip()
                link = article.find('a')['href']
                date_str = article.find('time')['datetime']

                article_date = parse_date(date_str, 'Security Week')
                article_date_obj = pd.to_datetime(article_date).date()

                # Skip if target_date is specified and doesn't match
                if target_date:
                    if article_date_obj != target_date:
                        logger.debug(f"Skipping article from {article_date_obj}, not matching target date {target_date}")
                        continue
                    else:
                        logger.info(f"Found article from target date {target_date}: {title}")

                news_items.append({
                    'title': title,
                    'summary': summary,
                    'url': link if link.startswith('http') else f"https://www.securityweek.com{link}",
                    'source': 'Security Week',
                    'date': article_date,
                    'category': categorize_news(title, summary)
                })
            except Exception as e:
                logger.error(f"Error processing Security Week article: {str(e)}")
                continue

        return news_items
    except Exception as e:
        logger.error(f"Error in fetch_security_week: {str(e)}")
        return []

def fetch_hacker_news(target_date=None):
    """Fetch news from The Hacker News"""
    try:
        url = "https://thehackernews.com"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('div', class_='body-post')

        news_items = []
        for article in articles:
            try:
                title = article.find('h2', class_='home-title').text.strip()
                summary = article.find('div', class_='home-desc').text.strip()
                link = article.find('a', class_='story-link')['href']
                date_str = article.find('div', class_='item-label').text.strip()

                article_date = parse_date(date_str, 'The Hacker News')
                article_date_obj = pd.to_datetime(article_date).date()

                # Skip if target_date is specified and doesn't match
                if target_date:
                    if article_date_obj != target_date:
                        logger.debug(f"Skipping article from {article_date_obj}, not matching target date {target_date}")
                        continue
                    else:
                        logger.info(f"Found article from target date {target_date}: {title}")

                news_items.append({
                    'title': title,
                    'summary': summary,
                    'url': link,
                    'source': 'The Hacker News',
                    'date': article_date,
                    'category': categorize_news(title, summary)
                })
            except Exception as e:
                logger.error(f"Error processing Hacker News article: {str(e)}")
                continue

        return news_items
    except Exception as e:
        logger.error(f"Error in fetch_hacker_news: {str(e)}")
        return []

def is_critical_news(title, critical_keywords):
    """
    Check if the news title contains critical security keywords
    """
    try:
        title_lower = title.lower()
        return any(keyword.lower() in title_lower for keyword in critical_keywords)
    except Exception as e:
        logger.error(f"Error in is_critical_news: {str(e)}")
        return False

def determine_category(title, summary):
    """
    Determine the category of a security news item based on its content
    """
    try:
        text = f"{title} {summary}".lower()

        # Keywords for different categories
        categories = {
            'Vulnerabilities': ['vulnerability', 'cve', 'exploit', 'patch', 'zero-day'],
            'Breaches': ['breach', 'leak', 'data exposure', 'compromise', 'hack'],
            'Threat Intelligence': ['threat', 'malware', 'ransomware', 'attack', 'campaign'],
            'Compliance': ['compliance', 'gdpr', 'ccpa', 'soc 2', 'iso 27001', 'nist', 'cis'],
            'Cloud Security': ['cloud', 'aws', 'azure', 'gcp', 'cloud security'],
            'Privacy': ['privacy', 'data protection', 'personal data', 'pii'],
            'Identity & Access': ['iam', 'pam', 'identity', 'authentication', 'authorization']
        }

        # Count matches for each category
        category_scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text)
            category_scores[category] = score

        # Return category with highest score, or 'Other' if no matches
        if not any(category_scores.values()):
            return 'Other'

        return max(category_scores.items(), key=lambda x: x[1])[0]
    except Exception as e:
        logger.error(f"Error in determine_category: {str(e)}")
        return 'Other'
