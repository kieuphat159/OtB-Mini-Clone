from scraper.zendesk_client import fetch_articles
from scraper.markdown_converter import convert_article, save_article_markdown
import os

def process_all_articles(output_dir="data/articles"):
    articles = fetch_articles()
    print(f"Processing {len(articles)} articles...")
    count = 0
    for article in articles:
        try:
            converted = convert_article(article)
            filepath = save_article_markdown(converted, output_dir)
            count += 1
            if count % 50 == 0:
                print(f"Saved {count} articles")
        except Exception as e:
            print(f"Error processing article {article.get('id')}: {e}")
    print(f"Done. Saved {count} articles to {output_dir}")

if __name__ == "__main__":
    process_all_articles()