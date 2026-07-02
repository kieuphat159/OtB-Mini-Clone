import os
import time
import random
from typing import List, Dict, Any, Optional
from openai import OpenAI

def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)

def with_retry(func, max_retries=5, base_delay=2):
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "rate_limit" in str(e).lower() or "timeout" in str(e).lower():
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Retry {attempt+1}/{max_retries} after {delay:.1f}s due to: {e}")
                    time.sleep(delay)
                else:
                    raise
        raise Exception(f"Failed after {max_retries} retries")
    return wrapper

def create_vector_store(name: str = "optibot-kb") -> str:
    client = get_openai_client()
    vs = client.vector_stores.create(name=name)
    print(f"Created Vector Store: {vs.id}")
    return vs.id

def get_or_create_vector_store(name: str = "optibot-kb") -> str:
    client = get_openai_client()
    configured_id = os.getenv("VECTOR_STORE_ID")
    if configured_id:
        try:
            store = client.vector_stores.retrieve(configured_id)
            print(f"Using existing Vector Store: {store.id}")
            return store.id
        except Exception as e:
            print(f"Configured VECTOR_STORE_ID is not usable: {e}")
            print("Creating a new Vector Store instead")

    stores = client.vector_stores.list()
    for store in stores.data:
        if store.name == name:
            print(f"Found existing Vector Store: {store.id}")
            return store.id
    return create_vector_store(name)

@with_retry
def upload_file_to_openai(file_path: str, purpose: str = "assistants") -> str:
    client = get_openai_client()
    with open(file_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose=purpose)
    print(f"Uploaded file: {file_obj.id} ({file_path})")
    return file_obj.id

@with_retry
def attach_file_to_vector_store(
    vector_store_id: str,
    file_id: str,
    attributes: Optional[Dict[str, str]] = None
):
    client = get_openai_client()
    attr = {k: str(v)[:256] for k, v in (attributes or {}).items()}
    vs_file = client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=file_id,
        attributes=attr
    )
    # Poll for completion
    for _ in range(30):
        try:
            status = client.vector_stores.files.retrieve(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            if status.status == "completed":
                print(f"Attached file {file_id} to Vector Store")
                return vs_file
            elif status.status == "failed":
                raise Exception(f"File {file_id} failed: {status.last_error}")
            time.sleep(1)
        except Exception as e:
            print(f"Retry retrieving status: {e}")
            time.sleep(2)
    raise Exception(f"Timeout waiting for file {file_id} to complete")

@with_retry
def list_vector_store_files(vector_store_id: str) -> List[Dict[str, Any]]:
    client = get_openai_client()
    all_files = []
    has_more = True
    after = None
    while has_more:
        params = {"limit": 100}
        if after:
            params["after"] = after
        response = client.vector_stores.files.list(
            vector_store_id=vector_store_id,
            **params
        )
        all_files.extend(response.data)
        has_more = response.has_more
        if has_more:
            after = response.last_id
    result = []
    for f in all_files:
        item = f.dict()
        result.append(item)
    print(f"Found {len(result)} files in Vector Store")
    if result:
        sample = result[0]
        print(f"Sample attributes: {sample.get('attributes')}")
    return result

@with_retry
def delete_vector_store_file(vector_store_id: str, file_id: str):
    client = get_openai_client()
    client.vector_stores.files.delete(vector_store_id=vector_store_id, file_id=file_id)
    print(f"Deleted file {file_id} from Vector Store")

@with_retry
def delete_openai_file(file_id: str):
    client = get_openai_client()
    client.files.delete(file_id=file_id)
    print(f"Deleted file {file_id} from OpenAI")
