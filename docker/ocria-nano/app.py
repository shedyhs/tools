"""API HTTP mínima para OCR com LiteParse + OCRia-nano-1."""

import asyncio
import os
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from liteparse import LiteParse

MAX_MB = int(os.environ.get("MAX_UPLOAD_MB", "0"))  # 0 = sem limite
MAX_BYTES = MAX_MB * 1024 * 1024

app = FastAPI(title="OCRia-nano-1 (LiteParse)")


def _parse(data: bytes, fmt: str, pages: str | None):
    parser = LiteParse(
        ocr_backend="ocria-nano",
        output_format=fmt,
        target_pages=pages,
        quiet=True,
    )
    return parser.parse(data)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse")
async def parse(
    file: UploadFile = File(...),
    format: Literal["text", "markdown"] = Query("markdown"),
    pages: str | None = Query(None, description='Ex.: "1-5,10"'),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Arquivo vazio")
    if MAX_BYTES and len(data) > MAX_BYTES:
        raise HTTPException(413, f"Arquivo maior que {MAX_MB} MB")
    try:
        result = await asyncio.to_thread(_parse, data, format, pages)
    except Exception as exc:  # erro do parser vira 422 com a mensagem
        raise HTTPException(422, f"Falha ao processar: {exc}") from exc
    return PlainTextResponse(result.text)
