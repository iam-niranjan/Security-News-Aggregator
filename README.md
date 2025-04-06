# Security News Aggregator

A Streamlit application that aggregates critical security news and blogs, allowing security engineers to focus on summaries and access source links.

## Features

- Fetches security news from multiple sources
- Categorizes news by type (Vulnerabilities, Breaches, etc.)
- AI-powered analysis and risk assessment using Google's Gemini
- Daily automated updates via GitHub Actions
- 90-day news archive with pagination
- Critical CVE highlighting
- Source link preservation

## Setup

1. Clone the repository:
```bash
git clone https://github.com/iam-niranjan/security-news.git
cd security-news
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

4. Run the application:
```bash
streamlit run app.py
```

## Automated Updates

The application uses GitHub Actions to automatically fetch and update security news daily:

- Updates run at 00:00 UTC every day
- New articles are added to the database
- Articles older than 90 days are automatically removed
- Updates can be manually triggered from the Actions tab

To set up automated updates:

1. Fork this repository
2. Add your `GEMINI_API_KEY` to your repository's secrets:
   - Go to Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Name: `GEMINI_API_KEY`
   - Value: Your Gemini API key

## Data Sources

- Security Week
- The Hacker News
- (More sources to be added)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
