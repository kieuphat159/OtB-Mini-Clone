from scraper.zendesk_client import fetch_articles
from scraper.markdown_converter import convert_article, save_article_markdown

# Lấy 1 bài đầu tiên
articles = fetch_articles(per_page=1)
if articles:
    article = articles[0]
    converted = convert_article(article)
    filepath = save_article_markdown(converted)
    print(f"Saved to {filepath}")
    print("\n--- Preview ---")
    print(converted['full_markdown'][:500])