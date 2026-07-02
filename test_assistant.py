import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def main():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    vector_store_id = os.getenv("VECTOR_STORE_ID")
    if not vector_store_id:
        print("VECTOR_STORE_ID not set in .env")
        return

    # 1. Tạo Assistant
    assistant = client.beta.assistants.create(
        name="OptiBot-Test",
        instructions="""You are OptiBot, the customer-support bot for OptiSigns.com.

• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply.""",
        model="gpt-4o-mini",  # hoặc "gpt-4o" nếu có
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store_id]
            }
        }
    )
    print(f"Created Assistant ID: {assistant.id}")

    # 2. Tạo thread và hỏi câu hỏi
    thread = client.beta.threads.create()
    print(f"Created Thread ID: {thread.id}")

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="How do I add a YouTube video?"
    )

    # 3. Chạy assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    # 4. Poll cho đến khi hoàn thành
    import time
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            print(f"Run failed: {run_status.status}")
            print(run_status.last_error)
            return
        time.sleep(1)

    # 5. Lấy phản hồi
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    for msg in messages.data:
        if msg.role == "assistant":
            content = msg.content[0].text.value
            print("\n--- Assistant Response ---")
            print(content)
            # In ra citations nếu có
            annotations = msg.content[0].text.annotations
            if annotations:
                print("\n--- Citations ---")
                for ann in annotations:
                    if ann.type == "file_citation":
                        print(f"File Citation: {ann.file_citation.quote}")
                        print(f"File ID: {ann.file_citation.file_id}")

    # 6. Xóa assistant (tùy chọn)
    # client.beta.assistants.delete(assistant.id)

if __name__ == "__main__":
    main()