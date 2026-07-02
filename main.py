import os
import glob
import sys
from dotenv import load_dotenv
from scraper.zendesk_client import fetch_articles
from scraper.markdown_converter import convert_article, save_article_markdown
from scraper.vector_store import (
    get_or_create_vector_store,
    upload_file_to_openai,
    attach_file_to_vector_store,
    list_vector_store_files,
    delete_vector_store_file,
    delete_openai_file
)

load_dotenv()

def main():
    # 1. Scrape và convert tất cả bài viết (đảm bảo file mới nhất)
    print("Scraping articles...")
    articles = fetch_articles()
    print(f"Fetched {len(articles)} articles")
    
    # Lưu file mới, đồng thời xây dựng dict article_id -> (slug, content_hash, html_url)
    # Để tiết kiệm, ta không ghi đè nếu không cần, nhưng ở đây cứ ghi lại để có file mới nhất
    output_dir = "data/articles"
    os.makedirs(output_dir, exist_ok=True)
    article_map = {}
    for article in articles:
        converted = convert_article(article)
        filepath = save_article_markdown(converted, output_dir)
        article_map[converted['article_id']] = {
            'slug': converted['slug'],
            'content_hash': converted['content_hash'],
            'html_url': converted['html_url'],
            'filepath': filepath
        }
    print(f"Saved/updated {len(article_map)} articles")
    
    # 2. Lấy hoặc tạo Vector Store
    vector_store_id = os.getenv("VECTOR_STORE_ID")
    if not vector_store_id:
        vector_store_id = get_or_create_vector_store("optibot-kb")
        # Lưu lại vào .env để dùng sau
        with open(".env", "a") as f:
            f.write(f"\nVECTOR_STORE_ID={vector_store_id}")
        print(f"VECTOR_STORE_ID saved to .env")
    else:
        print(f"Using existing Vector Store: {vector_store_id}")
    
    # 3. Lấy danh sách file hiện có trong Vector Store (để so sánh delta)
    existing_files = list_vector_store_files(vector_store_id)
    # Tạo dict: article_id -> {file_id, content_hash, url}
    existing_map = {}
    for f in existing_files:
        attrs = f.get('attributes', {})
        article_id = attrs.get('article_id')
        if article_id:
            existing_map[article_id] = {
                'file_id': f.get('id'),  # lưu ý: id của vector_store_file, không phải file_id
                'content_hash': attrs.get('content_hash'),
                'url': attrs.get('url'),
                'file_id_raw': f.get('file_id')  # file_id gốc
            }
    
    # 4. Sync: added, updated, skipped
    added = 0
    updated = 0
    skipped = 0
    for article_id, info in article_map.items():
        slug = info['slug']
        content_hash = info['content_hash']
        html_url = info['html_url']
        filepath = info['filepath']
        
        if article_id not in existing_map:
            # Added
            print(f"New article: {slug} (ID: {article_id})")
            # Upload file lên OpenAI
            file_id = upload_file_to_openai(filepath, purpose="assistants")
            # Attach vào Vector Store với attributes
            attach_file_to_vector_store(
                vector_store_id,
                file_id,
                attributes={
                    "article_id": str(article_id),
                    "content_hash": content_hash,
                    "url": html_url
                }
            )
            added += 1
        else:
            old_hash = existing_map[article_id]['content_hash']
            if old_hash != content_hash:
                # Updated: xóa file cũ khỏi Vector Store và OpenAI, upload mới
                print(f"Updated article: {slug} (ID: {article_id})")
                vs_file_id = existing_map[article_id]['file_id']
                openai_file_id = existing_map[article_id]['file_id_raw']
                # Xóa khỏi Vector Store
                delete_vector_store_file(vector_store_id, vs_file_id)
                # Xóa khỏi OpenAI Files (giải phóng quota)
                delete_openai_file(openai_file_id)
                # Upload mới
                new_file_id = upload_file_to_openai(filepath, purpose="assistants")
                attach_file_to_vector_store(
                    vector_store_id,
                    new_file_id,
                    attributes={
                        "article_id": str(article_id),
                        "content_hash": content_hash,
                        "url": html_url
                    }
                )
                updated += 1
            else:
                # Skipped
                skipped += 1
    
    # 5. (Bonus) Xóa các file trong Vector Store không còn trong article_map (orphan cleanup)
    # Lấy danh sách article_id từ map
    current_ids = set(article_map.keys())
    for article_id, vs_info in existing_map.items():
        if article_id not in current_ids:
            print(f"Orphan file found: {article_id}, deleting...")
            vs_file_id = vs_info['file_id']
            openai_file_id = vs_info['file_id_raw']
            delete_vector_store_file(vector_store_id, vs_file_id)
            delete_openai_file(openai_file_id)
    
    print(f"Sync completed: Added={added}, Updated={updated}, Skipped={skipped}")
    print(f"Total files in Vector Store: {len(article_map)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())