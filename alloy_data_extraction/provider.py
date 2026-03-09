import os
from pathlib import Path

from dataflow.serving import APILLMServing_request

DEFAULT_ENV_FILE = ".env"
DF_API_KEY_ENV = "DF_API_KEY"
DF_MODEL_ID_ENV = "DF_MODEL_ID"
DF_BASE_URL_ENV = "DF_BASE_URL"
DF_BASE_URLS_ENV = "DF_BASE_URLS"
DF_DISABLE_JSON_SCHEMA_ENV = "DF_DISABLE_JSON_SCHEMA"


def _load_env_file(env_file: str = DEFAULT_ENV_FILE) -> None:
    """Load `.env` key-value pairs into `os.environ` without overriding existing values."""
    env_path = Path(env_file)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _get_required_env(env_name: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if not value:
        raise ValueError(f"Missing env key: {env_name}")
    return value


def _get_base_url() -> str:
    for env_name in (DF_BASE_URLS_ENV, DF_BASE_URL_ENV):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value.split(",")[0].strip()
    raise ValueError(f"Missing env key: {DF_BASE_URLS_ENV} (or {DF_BASE_URL_ENV})")


def _normalize_api_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    return f"{url}/v1/chat/completions"


def _parse_bool_env(env_name: str) -> bool | None:
    raw_value = os.environ.get(env_name, "").strip().lower()
    if not raw_value:
        return None
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean env {env_name}={raw_value!r}")


def _supports_json_schema(base_url: str, model_name: str) -> bool:
    disabled = _parse_bool_env(DF_DISABLE_JSON_SCHEMA_ENV)
    if disabled is not None:
        return not disabled

    normalized_url = base_url.strip().lower()
    normalized_model = model_name.strip().lower()
    if "deepseek.com" in normalized_url or normalized_model.startswith("deepseek"):
        return False
    return True


def build_api_llm_serving(
    env_file: str = DEFAULT_ENV_FILE,
    max_workers: int = 8,
    max_retries: int = 5,
    temperature: float = 0.0,
) -> APILLMServing_request:
    """
    Build an `APILLMServing_request` from a single LLM env group.

    Required keys:
    - `DF_API_KEY`
    - `DF_MODEL_ID`
    - `DF_BASE_URLS` or `DF_BASE_URL`
    """
    _load_env_file(env_file)

    api_key_env_name = DF_API_KEY_ENV
    base_url = _get_base_url()
    model_name = _get_required_env(DF_MODEL_ID_ENV)
    _get_required_env(api_key_env_name)

    llm_serving = APILLMServing_request(
        api_url=_normalize_api_url(base_url),
        key_name_of_api_key=api_key_env_name,
        model_name=model_name,
        max_workers=max_workers,
        max_retries=max_retries,
        temperature=temperature,
    )
    llm_serving.supports_json_schema = _supports_json_schema(base_url=base_url, model_name=model_name)
    return llm_serving
