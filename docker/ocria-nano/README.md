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

## Instalação local (sem container)

Se você não quiser usar o Docker, dá para instalar o LiteParse direto no PC e usar
o OCRia-nano-1 pela linha de comando (`lit`) ou pelo Python. Não precisa de `sudo`.

### 1. Instalar o LiteParse

Escolha uma das opções:

```sh
uv tool install liteparse         # recomendado: isolado, só para o seu usuário
pipx install liteparse            # alternativa ao uv
npm i -g @llamaindex/liteparse    # versão Node.js, que também instala o lit
```

### 2. Baixar o modelo OCRia-nano-1

```sh
lit models pull ocria-nano        # ~60 MB, salvo em ~/.cache/liteparse/models
lit models list                   # confere a instalação
```

> **Licença:** os pesos do OCRia-nano-1 não seguem a licença open-source do LiteParse.
> Eles usam a *OCRia-nano-1 Model License*, que é baixada junto como `LICENSE`.
> Ao rodar o `pull`, você concorda com esses termos. A imagem Docker também os baixa.

Depois disso o `ocria-nano` vira o OCR padrão do `lit`. Para guardar os modelos em
outra pasta, defina `LITEPARSE_MODEL_DIR` antes do `pull`.

### 3. Usar pela linha de comando

```sh
lit parse documento.pdf                                  # texto
lit parse documento.pdf --format markdown -o saida.md    # Markdown em arquivo
lit parse scan.pdf --target-pages "1-5,10"               # só algumas páginas
lit batch-parse ./entrada ./saida                        # pasta inteira
```

### Usar pelo Python

```sh
pip install liteparse
```

```python
from liteparse import LiteParse, models

models.pull("ocria-nano")  # só na primeira vez
result = LiteParse(ocr_backend="ocria-nano", output_format="markdown").parse("scan.pdf")
print(result.text)
```

### Rodar a API sem Docker

```sh
pip install liteparse fastapi uvicorn python-multipart
lit models pull ocria-nano
uvicorn app:app --host 127.0.0.1 --port 8000   # dentro desta pasta
```

### Desinstalar

```sh
uv tool uninstall liteparse       # ou: pipx uninstall liteparse
rm -rf ~/.cache/liteparse         # remove os modelos baixados
```
