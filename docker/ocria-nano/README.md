# ocria-nano

API HTTP de OCR com o [OCRia-nano-1](https://huggingface.co/llamaindex/OCRia-nano-1)
via [LiteParse](https://github.com/run-llama/liteparse). Roda só na CPU, e o modelo
(~60 MB) já vem baixado na imagem, então funciona offline.

## Subir

```sh
docker compose up -d --build
```

A API fica em `http://127.0.0.1:8000`. A documentação interativa está em `/docs`.

## Usar

```sh
curl -F file=@documento.pdf localhost:8000/parse                  # Markdown
curl -F file=@foto.png "localhost:8000/parse?format=text"          # texto puro
curl -F file=@doc.pdf "localhost:8000/parse?pages=1-3,10"          # só algumas páginas
```

Aceita PDF, imagens, DOCX, XLSX, PPTX e outros formatos lidos pelo LiteParse.

| Endpoint | Descrição |
|---|---|
| `GET /health` | Verificação de saúde |
| `POST /parse` | Campo `file` (multipart); query `format` (`markdown` padrão ou `text`) e `pages` |

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `MAX_UPLOAD_MB` | `0` | Limite de upload em MB; `0` = sem limite. O arquivo é lido inteiro na memória. |

A porta é publicada só em `127.0.0.1`. Para expor na rede, altere `ports` no `compose.yaml`.
