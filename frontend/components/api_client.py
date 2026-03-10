"""
api_client.py
All HTTP calls to the PaperIQ FastAPI backend.
"""
import requests
from typing import Optional, List

BASE_URL = "http://localhost:8000"


def upload_paper(file_bytes: bytes, filename: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/papers/upload",
        files={"file": (filename, file_bytes, "application/pdf")},
    )
    resp.raise_for_status()
    return resp.json()


def list_papers() -> List[dict]:
    resp = requests.get(f"{BASE_URL}/papers")
    resp.raise_for_status()
    return resp.json()


def get_paper(paper_id: str) -> dict:
    resp = requests.get(f"{BASE_URL}/papers/{paper_id}")
    resp.raise_for_status()
    return resp.json()


def delete_paper(paper_id: str) -> None:
    resp = requests.delete(f"{BASE_URL}/papers/{paper_id}")
    resp.raise_for_status()


def run_analysis(paper_id: int, n_sentences: int = 3) -> dict:
    resp = requests.post(
        f"{BASE_URL}/papers/{paper_id}/analyze",
        params={"n_sentences": n_sentences},
    )
    resp.raise_for_status()
    return resp.json()


def get_analysis(paper_id: int) -> dict:
    resp = requests.get(f"{BASE_URL}/papers/{paper_id}/analyze")
    resp.raise_for_status()
    return resp.json()


def compare_papers(paper_ids: List[int]) -> dict:
    resp = requests.post(
        f"{BASE_URL}/papers/compare",
        json={"paper_ids": paper_ids},
    )
    resp.raise_for_status()
    return resp.json()


def export_paper(paper_id: int, fmt: str = "pdf") -> bytes:
    resp = requests.get(f"{BASE_URL}/papers/{paper_id}/export?format={fmt}")
    resp.raise_for_status()
    return resp.content


def get_trends(paper_ids: List[int]) -> dict:
    resp = requests.post(
        f"{BASE_URL}/papers/trends",
        json={"paper_ids": paper_ids},
    )
    resp.raise_for_status()
    return resp.json()


def chat_with_paper(paper_id: int, question: str, history: list | None = None) -> dict:
    resp = requests.post(
        f"{BASE_URL}/papers/{paper_id}/chat",
        json={"question": question, "history": history or []},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()

    return resp.content
