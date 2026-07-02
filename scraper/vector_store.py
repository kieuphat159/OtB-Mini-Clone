import os
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI

def get_openai_client() -> OpenAI:
    """Khởi tạo OpenAI client từ biến môi trường."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    return OpenAI(api_key=api_key)

def create_vector_store(name: str = "optibot-kb") -> str:
    """
    Tạo Vector Store mới và trả về ID.
    """
    client = get_openai_client()
    vs = client.vector_stores.create(name=name)
    print(f"Created Vector Store: {vs.id} (name: {vs.name})")
    return vs.id

def get_or_create_vector_store(name: str = "optibot-kb") -> str:
    """
    Lấy Vector Store đã tồn tại (theo tên) hoặc tạo mới.
    """
    client = get_openai_client()
    # Liệt kê các vector store đã có
    stores = client.vector_stores.list()
    for store in stores.data:
        if store.name == name:
            print(f"Found existing Vector Store: {store.id}")
            return store.id
    # Không tìm thấy, tạo mới
    return create_vector_store(name)

def upload_file_to_openai(file_path: str, purpose: str = "assistants") -> str:
    """
    Upload file lên OpenAI Files API, trả về file_id.
    """
    client = get_openai_client()
    with open(file_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose=purpose)
    print(f"Uploaded file: {file_obj.id} ({file_path})")
    return file_obj.id

def attach_file_to_vector_store(
    vector_store_id: str,
    file_id: str,
    attributes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Gắn file vào Vector Store với attributes tùy chọn (article_id, content_hash, url).
    """
    client = get_openai_client()
    if attributes:
        # OpenAI yêu cầu attributes là dict với key string, value string
        # Tối đa 16 key-value, mỗi value <= 256 chars
        # Giới hạn an toàn: chúng ta chỉ dùng 3 key
        attr = {k: str(v)[:256] for k, v in attributes.items()}
    else:
        attr = {}
    vs_file = client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=file_id,
        attributes=attr
    )
    # Poll cho đến khi file status là 'completed'
    while True:
        status = client.vector_stores.files.retrieve(
            vector_store_id=vector_store_id,
            file_id=file_id  # hoặc vs_file.id nếu khác
        )
        if status.status == "completed":
            break
        elif status.status == "failed":
            raise Exception(f"File {file_id} failed to process: {status.last_error}")
        time.sleep(1)
    print(f"Attached file {file_id} to Vector Store {vector_store_id}")
    return vs_file.dict()

def list_vector_store_files(vector_store_id: str) -> List[Dict[str, Any]]:
    """
    Lấy danh sách tất cả file trong Vector Store (có attributes).
    Trả về list các dict với keys: id, file_id, attributes, status.
    """
    client = get_openai_client()
    all_files = []
    # Phân trang nếu cần (OpenAI limit 100 per page)
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
    return [f.dict() for f in all_files]

def delete_vector_store_file(vector_store_id: str, file_id: str) -> None:
    """
    Xóa file khỏi Vector Store (chỉ xóa khỏi VS, không xóa file trên OpenAI).
    """
    client = get_openai_client()
    client.vector_stores.files.delete(
        vector_store_id=vector_store_id,
        file_id=file_id
    )
    print(f"Deleted file {file_id} from Vector Store")

def delete_openai_file(file_id: str) -> None:
    """
    Xóa file khỏi OpenAI Files (giải phóng quota).
    """
    client = get_openai_client()
    client.files.delete(file_id=file_id)
    print(f"Deleted file {file_id} from OpenAI")