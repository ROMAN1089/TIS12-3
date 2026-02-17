"""
AI Agent Service with S3 Backend and Ollama Integration

This agent service implements the new architecture with:
- S3/MinIO for artifact storage (Claim Check pattern)
- Ollama for AI generation
- Self-healing with linting for code generation
- Token-based authentication
"""
import os
import ast
import logging
import uuid
import json
import io
from typing import Optional, Dict, Any
from datetime import datetime

# Сторонние библиотеки
import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
import ollama
from dotenv import load_dotenv

# Загрузка конфигурации
load_dotenv()

# --- КОНФИГУРАЦИЯ ---
SERVICE_ROLE = os.getenv("AGENT_ROLE", "generic")  # decomposer | db_architect | coder
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
API_TOKEN = os.getenv("AGENT_SECRET_TOKEN", "change_me")
MAX_RETRIES = int(os.getenv("MAX_SELF_CORRECTION_RETRIES", 3))

# Настройки S3 (MinIO)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "agent-artifacts")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

# Настройка логгера
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(f"Agent-{SERVICE_ROLE}")

app = FastAPI(title=f"AI Agent: {SERVICE_ROLE} (S3 Backend)")

# --- S3 CLIENT SETUP ---
s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION
)

# Проверка доступа к бакету при старте
try:
    s3_client.head_bucket(Bucket=S3_BUCKET)
    logger.info(f"Connected to S3 bucket: {S3_BUCKET}")
except ClientError:
    logger.warning(f"Bucket {S3_BUCKET} does not exist or not accessible. Attempting to create...")
    try:
        s3_client.create_bucket(Bucket=S3_BUCKET)
        logger.info(f"Created bucket: {S3_BUCKET}")
    except Exception as e:
        logger.error(f"Failed to create bucket: {e}")

# --- МОДЕЛИ ДАННЫХ ---
class AgentRequest(BaseModel):
    input_data: str = Field(..., description="Промпт, Спецификация или Описание задачи")
    context_keys: Optional[Dict[str, str]] = Field(None, description="Ссылки на файлы контекста в S3 (например, {'spec': 's3://...'})")
    system_prompt_override: Optional[str] = None

class AgentArtifact(BaseModel):
    s3_key: str
    s3_url: str
    content_type: str
    filename: str

class AgentResponse(BaseModel):
    status: str
    artifact: AgentArtifact
    metadata: Dict[str, Any] = {}

# --- ИНСТРУМЕНТЫ (TOOLS) ---

def clean_code_block(text: str) -> str:
    """Вырезает чистый код/JSON из markdown блоков."""
    if "```" in text:
        lines = text.splitlines()
        code_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines)
    return text

def run_linter_check(code: str) -> str:
    """Валидация Python синтаксиса."""
    try:
        ast.parse(code)
        return "PASS"
    except SyntaxError as e:
        return f"SYNTAX_ERROR: Line {e.lineno}: {e.msg}\nCode: {e.text}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def upload_to_s3(content: str, extension: str) -> AgentArtifact:
    """Загружает строку (код/json) как файл в S3 и возвращает ссылку."""
    
    # Генерация уникального имени файла
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"{SERVICE_ROLE}/{timestamp}_{unique_id}.{extension}"
    
    # Конвертация строки в байтовый поток
    file_obj = io.BytesIO(content.encode('utf-8'))
    
    try:
        s3_client.upload_fileobj(file_obj, S3_BUCKET, filename)
        
        # Генерация Presigned URL (действителен 1 час) для удобства просмотра
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': filename},
            ExpiresIn=3600
        )
        
        logger.info(f"Artifact uploaded: {filename}")
        
        return AgentArtifact(
            s3_key=filename,
            s3_url=url,
            content_type=extension,
            filename=filename
        )
    except Exception as e:
        logger.error(f"S3 Upload Failed: {e}")
        raise HTTPException(status_code=500, detail=f"S3 Storage Error: {str(e)}")

def download_context_from_s3(s3_key: str) -> str:
    """Скачивает контекст (например, JSON спеку) из S3 по ключу."""
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        return obj['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to download context {s3_key}: {e}")
        return ""

# --- ЯДРО АГЕНТА ---

def generate_with_retry(system_prompt: str, user_prompt: str, is_code: bool = False) -> str:
    client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    logger.info("Starting generation...")
    response = client.chat(model=OLLAMA_MODEL, messages=messages)
    content = response['message']['content']
    
    # Очистка от маркдауна сразу
    clean_content = clean_code_block(content)

    if not is_code:
        return clean_content

    # Логика самолечения (Lint -> Fix)
    for attempt in range(MAX_RETRIES):
        lint_result = run_linter_check(clean_content)
        
        if lint_result == "PASS":
            logger.info(f"Linter passed on attempt {attempt + 1}")
            return clean_content
        
        logger.warning(f"Linter failed on attempt {attempt + 1}: {lint_result}")
        
        fix_prompt = (
            f"SYNTAX ERROR DETECTED:\n{lint_result}\n\n"
            "TASK: Fix the error and output the COMPLETE corrected code.\n"
            "REQUIREMENTS:\n"
            "1. Keep all functionality intact\n"
            "2. Only fix the syntax error, don't refactor\n"
            "3. Return ONLY the code, no explanations or markdown\n"
            "4. Ensure the code is complete and runnable"
        )
        
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": fix_prompt})
        
        response = client.chat(model=OLLAMA_MODEL, messages=messages)
        content = response['message']['content']
        clean_content = clean_code_block(content)

    logger.error("Max retries reached. Returning last attempt.")
    return clean_content

# --- API ENDPOINTS ---

@app.post("/generate", response_model=AgentResponse)
async def generate_task(request: AgentRequest, x_service_token: str = Header(None)):
    
    # 1. Auth Check
    if x_service_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid Service Token")

    # 2. Подготовка контекста (Скачивание из S3 если нужно)
    # Если на вход подали ключи S3 (например, спеку), скачиваем их текст
    full_input_context = ""
    if request.context_keys:
        for key, s3_path in request.context_keys.items():
            logger.info(f"Downloading context '{key}' from {s3_path}...")
            file_content = download_context_from_s3(s3_path)
            full_input_context += f"\n\n--- CONTEXT ({key}) ---\n{file_content}\n"

    final_user_prompt = request.input_data + full_input_context

    # 3. Настройка роли
    is_code_mode = False
    file_extension = "txt"
    system_prompt = request.system_prompt_override

    if not system_prompt:
        if SERVICE_ROLE == "decomposer":
            system_prompt = (
                "You are an expert Software Architect specializing in project decomposition.\n"
                "CRITICAL RULES:\n"
                "1. Output ONLY valid JSON, no markdown, no explanations\n"
                "2. Structure: {\"tasks\": [{\"id\": str, \"title\": str, \"description\": str, \"dependencies\": [str]}]}\n"
                "3. Break down complex requirements into atomic, testable tasks\n"
                "4. Identify dependencies between tasks clearly\n"
                "5. Each task must be actionable and have clear acceptance criteria"
            )
            file_extension = "json"
        elif SERVICE_ROLE == "db_architect":
            system_prompt = (
                "You are an expert Database Architect specializing in SQLAlchemy ORM.\n"
                "CRITICAL RULES:\n"
                "1. Output ONLY valid Python code with proper imports\n"
                "2. Use SQLAlchemy 2.0+ style (declarative_base or DeclarativeBase)\n"
                "3. Include: proper types, constraints, indexes, relationships\n"
                "4. Follow naming conventions: snake_case for tables/columns\n"
                "5. Add docstrings to models explaining their purpose\n"
                "6. Include __repr__ methods for debugging\n"
                "7. Consider cascading, back_populates, and lazy loading strategies"
            )
            is_code_mode = True
            file_extension = "py"
        elif SERVICE_ROLE == "coder":
            system_prompt = (
                "You are an expert Python Developer focused on production-ready code.\n"
                "CRITICAL RULES:\n"
                "1. Output ONLY valid, executable Python code\n"
                "2. Include all necessary imports at the top\n"
                "3. Follow PEP 8 style guide strictly\n"
                "4. Add type hints for all functions and methods\n"
                "5. Write clear docstrings (Google or NumPy style)\n"
                "6. Handle errors with proper exception handling\n"
                "7. Add logging where appropriate\n"
                "8. Make code modular, testable, and maintainable\n"
                "9. Use meaningful variable/function names\n"
                "10. Include brief inline comments for complex logic"
            )
            is_code_mode = True
            file_extension = "py"
        else:
            system_prompt = (
                "You are a helpful AI assistant with expertise in software development.\n"
                "Provide clear, accurate, and actionable responses based on the user's request."
            )

    # 4. Генерация
    try:
        generated_content = generate_with_retry(system_prompt, final_user_prompt, is_code=is_code_mode)
        
        # 5. Выгрузка в S3 (Claim Check)
        artifact = upload_to_s3(generated_content, file_extension)
        
        return AgentResponse(
            status="success",
            artifact=artifact, # Возвращаем НЕ контент, а объект с ссылкой
            metadata={
                "model": OLLAMA_MODEL, 
                "role": SERVICE_ROLE,
                "retries_used": 0 # TODO: прокинуть счетчик ретраев
            }
        )
    except Exception as e:
        logger.error(f"Process failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
