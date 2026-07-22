#!/usr/bin/env python3
"""
Healthcheck script for services awailability check
"""

import os
import sys
import time

import redis
import requests


def check_ollama() -> tuple[bool, str]:
    """Check Ollama and models awailability"""
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        embed_model = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

        resp = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if resp.status_code != 200:
            return False, f"Ollama API unawailable: {resp.status_code}"

        models = [m.get("name", "") for m in resp.json().get("models", [])]
        if not any(embed_model in m for m in models):
            return False, f"Model {embed_model} not found in Ollama"

        return True, "OK"
    except requests.exceptions.ConnectionError:
        return False, "Ollama unawailable (ConnectionError)"
    except Exception as e:
        return False, f"Check Ollama error: {str(e)}"


def check_qdrant() -> tuple[bool, str]:
    """Check Qdrant awailability"""
    try:
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        qdrant_port = os.getenv("QDRANT_PORT", "6333")

        resp = requests.get(f"http://{qdrant_host}:{qdrant_port}/healthz", timeout=5)
        if resp.status_code == 200:
            return True, "OK"
        return False, f"Qdrant healthcheck response {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Qdrant unawailable (ConnectionError)"
    except Exception as e:
        return False, f"Check Qdrant error: {str(e)}"


def check_redis() -> tuple[bool, str]:
    """Check Redis awailability"""
    try:
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))

        r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, socket_timeout=5)
        if r.ping():
            return True, "OK"
        return False, "Redis not responding to ping"
    except redis.ConnectionError:
        return False, "Redis unawailable (ConnectionError)"
    except Exception as e:
        return False, f"Check Redis error: {str(e)}"


def main():
    """Main healthcheck"""
    checks = {
        "Ollama": check_ollama,
        "Qdrant": check_qdrant,
        "Redis": check_redis,
    }

    all_healthy = True
    for service_name, check_func in checks.items():
        status, message = check_func()
        if not status:
            print(f"{service_name}: {message}")
            all_healthy = False
        else:
            print(f"{service_name}: {message}")

    sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    time.sleep(2)
    main()
