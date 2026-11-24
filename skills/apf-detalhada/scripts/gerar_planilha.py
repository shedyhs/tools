#!/usr/bin/env python3
"""Gera a planilha de contagem APF detalhada a partir de um JSON de contagem.

Uso:
    python3 gerar_planilha.py contagem.json saida.xlsx [--modelo modelo.xlsx] [--recalcular]

- Preenche o modelo (abas Contagem, Funções, Sumário) mantendo as fórmulas IFPUG.
- Acrescenta as abas de rastreabilidade: Memória TD, Evidências, Revisão, Regras.
- Funções com TD ou AR/TR desconhecidos NÃO entram em Funções: vão para Revisão
  como "A apurar" (ausência de valor não é zero nem complexidade baixa).
- Valida a consistência e imprime o sumário calculado em Python.
- --recalcular: recalcula no LibreOffice (headless) e confere o total das fórmulas.

Requer: openpyxl. Opcional: soffice (LibreOffice) para --recalcular.
"""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict, defaultdict

try:
    import openpyxl
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.formula.translate import Translator
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.workbook.defined_name import DefinedName
except ImportError:
    sys.exit("openpyxl não instalado. Rode: python3 -m pip install openpyxl (de preferência num venv).")

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO_PADRAO = os.path.join(AQUI, "..", "assets", "modelo-saida.xlsx")

TIPOS_DADOS = {"ALI", "AIE"}
TIPOS_TRANS = {"EE", "SE", "CE"}
OPERACOES = {"I", "A", "E", "T"}
PESOS = {
    "EE": (3, 4, 6), "SE": (4, 5, 7), "CE": (3, 4, 6),
    "ALI": (7, 10, 15), "AIE": (5, 7, 10),
}
LINHA_MIN_FORMULAS = 215  # o modelo traz fórmulas até esta linha


# ---------------------------------------------------------------- regras IFPUG

def complexidade(tipo, td, ar):
    """Retorna 0 (Baixa), 1 (Média) ou 2 (Alta) — tabelas IFPUG do guia FATTO."""
    if tipo in TIPOS_DADOS:          # TR: 1 | 2-5 | 6+   TD: 1-19 | 20-50 | 51+
        lin = 0 if ar <= 1 else (1 if ar <= 5 else 2)
        col = 0 if td <= 19 else (1 if td <= 50 else 2)
    elif tipo == "EE":               # AR: 0-1 | 2 | 3+   TD: 1-4 | 5-15 | 16+
        lin = 0 if ar <= 1 else (1 if ar == 2 else 2)
        col = 0 if td <= 4 else (1 if td <= 15 else 2)
    else:                            # SE/CE AR: 0-1 | 2-3 | 4+  TD: 1-5 | 6-19 | 20+
        lin = 0 if ar <= 1 else (1 if ar <= 3 else 2)
        col = 0 if td <= 5 else (1 if td <= 19 else 2)
    matriz = ((0, 0, 1), (0, 1, 2), (1, 2, 2))
    return matriz[lin][col]


# ---------------------------------------------------------------- utilidades

def item_nome(it):
    return it if isinstance(it, str) else it.get("nome", "")


def item_fonte(it, padrao=""):
    return padrao if isinstance(it, str) else it.get("fonte", padrao)


def item_trat(it, padrao=""):
    return padrao if isinstance(it, str) else it.get("tratamento", padrao)


def primeira_fonte(f):
    fontes = f.get("fontes") or []
    if not fontes:
        return ""
    return item_fonte(fontes[0], fontes[0] if isinstance(fontes[0], str) else "")


def escrever(ws, celula, valor):
    """Escreve ignorando células mescladas (escreve só na âncora)."""
    c = ws[celula]
    if type(c).__name__ == "MergedCell":
        return
    c.value = valor


# ---------------------------------------------------------------- validação

def validar(dados):
    erros, avisos = [], []
    funcoes = dados.get("funcoes", [])
    if not funcoes:
        erros.append("nenhuma função em 'funcoes'")
    ids = set()
    nomes_dados = {f.get("nome", "").strip().upper() for f in funcoes if f.get("tipo") in TIPOS_DADOS}
    mantidos, lidos = set(), set()
    for i, f in enumerate(funcoes, 1):
        ref = f.get("id") or f"#{i}"
        for campo in ("id", "nome", "tipo"):
            if not f.get(campo):
                erros.append(f"{ref}: campo obrigatório ausente: {campo}")
        if f.get("id") in ids:
            erros.append(f"{ref}: id duplicado")
        ids.add(f.get("id"))
        tipo = f.get("tipo")
        if tipo not in TIPOS_DADOS | TIPOS_TRANS:
            erros.append(f"{ref}: tipo inválido {tipo!r}")
            continue
        op = f.get("operacao", "I")
        if op not in OPERACOES:
            erros.append(f"{ref}: operacao inválida {op!r} (use I, A, E ou T)")
        if tipo in TIPOS_TRANS and not f.get("grupo"):
            erros.append(f"{ref}: transação sem 'grupo' (seção FUNÇÃO <GRUPO>)")
        if not f.get("fontes"):
            avisos.append(f"{ref}: sem 'fontes' — rastreabilidade incompleta")
        td, ar = f.get("td"), f.get("ar_tr")
        if td is not None and (not isinstance(td, int) or td < 1):
            erros.append(f"{ref}: td deve ser inteiro >= 1 ou null")
        if ar is not None and (not isinstance(ar, int) or ar < 0):
            erros.append(f"{ref}: ar_tr deve ser inteiro >= 0 ou null")
        if tipo in TIPOS_DADOS and isinstance(ar, int) and ar < 1:
            erros.append(f"{ref}: ALI/AIE tem no mínimo 1 TR (o próprio arquivo)")
        if f.get("td_lista") and td is not None and len(f["td_lista"]) != td:
            erros.append(f"{ref}: td={td} mas td_lista tem {len(f['td_lista'])} itens")
        lista_ar = f.get("tr_lista") if tipo in TIPOS_DADOS else f.get("ar_lista")
        if lista_ar and ar is not None and len(lista_ar) != ar:
            rot = "TR" if tipo in TIPOS_DADOS else "AR"
            erros.append(f"{ref}: ar_tr={ar} mas a lista de {rot} tem {len(lista_ar)} itens")
        if tipo in TIPOS_TRANS:
            for it in f.get("ar_lista", []):
                n = item_nome(it).strip().upper()
                if n not in nomes_dados:
                    avisos.append(f"{ref}: AR '{item_nome(it)}' não é ALI/AIE declarado em funcoes")
                lidos.add(n)
            for it in f.get("mantem", []):
                n = item_nome(it).strip().upper()
                if tipo == "CE":
                    avisos.append(f"{ref}: CE não pode manter ALI ('{item_nome(it)}') — reclassificar como EE/SE")
                mantidos.add(n)
        if tipo == "CE" and f.get("calculo"):
            avisos.append(f"{ref}: CE marcada com 'calculo' — pela definição FATTO deveria ser SE")
    for f in funcoes:
        n = f.get("nome", "").strip().upper()
        if f.get("tipo") == "ALI" and n not in mantidos:
            avisos.append(f"{f.get('id')}: ALI '{f.get('nome')}' sem EE/SE que o mantenha (campo 'mantem'). "
                          "Confirmar se não é AIE ou se falta a transação.")
        if f.get("tipo") == "AIE" and n in mantidos:
            avisos.append(f"{f.get('id')}: AIE '{f.get('nome')}' aparece como mantido — AIE só é lido")
        if f.get("tipo") == "AIE" and n not in lidos:
            avisos.append(f"{f.get('id')}: AIE '{f.get('nome')}' não é referenciado por nenhuma transação")
    return erros, avisos


# ---------------------------------------------------------------- abas do modelo

def preencher_contagem(wb, c):
    ws = wb["Contagem"]
    for nome in ("Contagem", "Funções", "Sumário"):
        wb[nome]["A1"] = c.get("orgao", "")
        wb[nome]["A2"] = c.get("unidade", "")
    mapa = {"F4": "empresa", "F5": "aplicacao", "F6": "projeto", "F7": "responsavel",
            "F8": "contado_por", "F9": "revisor", "X7": "data_criacao", "X8": "data_revisao",
            "A18": "proposito", "A42": "escopo"}
    for cel, chave in mapa.items():
        if c.get(chave):
            escrever(ws, cel, c[chave])
    for cel in ("A18", "A42"):
        ws[cel].alignment = Alignment(wrap_text=True, vertical="top")
    ws["T4"] = c.get("valor_pf") or 0
    ws["C11"] = "Detalhada"
    tipo = (c.get("tipo_contagem") or "desenvolvimento").lower()
    rotulos = {"C12": ("desenvolvimento", "Projeto de Desenvolvimento"),
               "C13": ("melhoria", "Projeto de Melhoria"),
               "C14": ("aplicacao", "Aplicação ( Baseline )")}
    for cel, (chave, texto) in rotulos.items():
        ws[cel] = ("X " if tipo.startswith(chave[:5]) else "   ") + texto
    defl = c.get("deflatores", {})
    for cel, chave in (("U12", "I"), ("U13", "A"), ("U14", "E"), ("U15", "T")):
        if chave in defl:
            ws[cel] = defl[chave]


def preencher_funcoes(wb, completas):
    ws = wb["Funções"]
    ncols = 21
    formulas = {col: ws[f"{col}9"].value for col in "KLMNO"}
    ws["T7"], ws["U7"] = "ID", "Fonte principal"
    for col in "TU":
        ws[f"{col}7"]._style = copy.copy(ws["P7"]._style)
    ws.column_dimensions["T"].width = 12
    ws.column_dimensions["U"].width = 60

    estilos_cab = [copy.copy(ws.cell(8, c)._style) for c in range(1, ncols + 1)]
    estilos_lin = [copy.copy(ws.cell(9, c)._style) for c in range(1, ncols + 1)]
    altura = ws.row_dimensions[9].height

    def linha(r, cabecalho, valores):
        estilos = estilos_cab if cabecalho else estilos_lin
        for c in range(1, ncols + 1):
            cel = ws.cell(r, c)
            if type(cel).__name__ == "MergedCell":
                continue
            cel._style = copy.copy(estilos[c - 1])
            cel.value = None
        ws.row_dimensions[r].height = altura
        for col, f in formulas.items():
            ws[f"{col}{r}"] = Translator(f, origin=f"{col}9").translate_formula(f"{col}{r}")
        for col, v in valores.items():
            ws[f"{col}{r}"] = v
        for faixa in (f"A{r}:F{r}", f"P{r}:S{r}"):
            if faixa not in {str(m) for m in ws.merged_cells.ranges}:
                ws.merge_cells(faixa)

    def valores_funcao(f):
        lista = f.get("tr_lista") if f["tipo"] in TIPOS_DADOS else f.get("ar_lista")
        obs = f.get("observacoes") or ", ".join(item_nome(x) for x in (lista or []))
        return {"A": f["nome"], "G": f["tipo"], "H": f.get("operacao", "I"),
                "I": f["td"], "J": f["ar_tr"], "P": obs, "T": f["id"], "U": primeira_fonte(f)}

    r = 8
    linha(r, True, {"A": "ARQUIVOS DE DADOS"})
    for f in [x for x in completas if x["tipo"] in TIPOS_DADOS]:
        r += 1
        linha(r, False, valores_funcao(f))
    grupos = OrderedDict()
    for f in [x for x in completas if x["tipo"] in TIPOS_TRANS]:
        grupos.setdefault(f["grupo"].strip(), []).append(f)
    for g, fs in grupos.items():
        r += 1
        titulo = g if g.upper().startswith("FUNÇÃO") else f"FUNÇÃO {g.upper()}"
        linha(r, True, {"A": titulo})
        for f in fs:
            r += 1
            linha(r, False, valores_funcao(f))
    ultima = r
    limite = max(ultima, LINHA_MIN_FORMULAS)
    # linhas restantes do modelo: estilo neutro (remove faixas de seção herdadas)
    for rr in range(ultima + 1, ws.max_row + 1):
        for c in range(1, ncols + 1):
            cel = ws.cell(rr, c)
            if type(cel).__name__ != "MergedCell":
                cel._style = copy.copy(estilos_lin[c - 1])

    verde = PatternFill("solid", fgColor="C6EFCE")
    amarelo = PatternFill("solid", fgColor="FFEB9C")
    vermelho = PatternFill("solid", fgColor="FFC7CE")
    faixa = f"H9:H{ultima}"
    ws.conditional_formatting.add(faixa, CellIsRule(operator="equal", formula=['"I"'], fill=verde))
    ws.conditional_formatting.add(faixa, CellIsRule(operator="equal", formula=['"A"'], fill=amarelo))
    ws.conditional_formatting.add(faixa, CellIsRule(operator="equal", formula=['"E"'], fill=vermelho))
    ws.auto_filter.ref = f"A7:U{ultima}"

    if "CF" in wb.defined_names:
        del wb.defined_names["CF"]
    wb.defined_names["CF"] = DefinedName("CF", attr_text=f"'Funções'!$K$8:$K${limite}")
    s = wb["Sumário"]
    for cel in ("E55", "E56", "E57", "E58"):
        s[cel] = s[cel].value.replace("$215", f"${limite}")
    return ultima


# ---------------------------------------------------------------- abas de rastreabilidade

def aba_tabela(wb, titulo, cabecalhos, linhas, larguras, subtitulo):
    ws = wb.create_sheet(titulo)
    azul = PatternFill("solid", fgColor="1F497D")
    ws["A1"] = wb["Contagem"]["A1"].value
    ws["A2"] = titulo
    ws["A2"].font = Font(bold=True, size=13)
    ws["A3"] = subtitulo
    for i, h in enumerate(cabecalhos, 1):
        c = ws.cell(5, i, h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = azul
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for r, valores in enumerate(linhas, 6):
        for i, v in enumerate(valores, 1):
            ws.cell(r, i, v).alignment = Alignment(wrap_text=True, vertical="top")
    for i, w in enumerate(larguras, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = "A6"
    ultima_col = openpyxl.utils.get_column_letter(len(cabecalhos))
    ws.auto_filter.ref = f"A5:{ultima_col}{5 + max(1, len(linhas))}"
    return ws


def montar_memoria(funcoes):
    linhas = []
    for f in funcoes:
        fonte_pad = primeira_fonte(f)
        listas = [("TD", f.get("td_lista") or [])]
        if f["tipo"] in TIPOS_DADOS:
            listas += [("TR", f.get("tr_lista") or []),
                       ("Coluna de evidência", f.get("colunas_excluidas") or [])]
        else:
            listas += [("AR", f.get("ar_lista") or []),
                       ("Campo excluído", f.get("campos_excluidos") or [])]
        for natureza, lista in listas:
            padrao = "Não acrescenta TD (técnico/transporte/repetido)." if natureza in (
                "Coluna de evidência", "Campo excluído") else ""
            for n, it in enumerate(lista, 1):
                linhas.append([f["id"], f["nome"], f["tipo"], natureza, n, item_nome(it),
                               item_fonte(it, fonte_pad), item_trat(it, padrao)])
    return linhas


def montar_regras(dados):
    linhas = [
        ["Pesos", "EE 3/4/6 · SE 4/5/7 · CE 3/4/6 · ALI 7/10/15 · AIE 5/7/10 (Baixa/Média/Alta)",
         "Guia FATTO, tab. 2.3 e 2.11"],
        ["ALI/AIE", "TR 1: TD 1-50 Baixa, 51+ Média · TR 2-5: 1-19 Baixa, 20-50 Média, 51+ Alta · "
                    "TR 6+: 1-19 Média, 20+ Alta", "Guia FATTO, tab. 2.2"],
        ["EE", "AR 0-1: TD 1-15 Baixa, 16+ Média · AR 2: 1-4 Baixa, 5-15 Média, 16+ Alta · "
               "AR 3+: 1-4 Média, 5+ Alta", "Guia FATTO, tab. 2.9"],
        ["SE/CE", "AR 0-1: TD 1-19 Baixa, 20+ Média · AR 2-3: 1-5 Baixa, 6-19 Média, 20+ Alta · "
                  "AR 4+: 1-5 Média, 6+ Alta", "Guia FATTO, tab. 2.10"],
        ["Fator de ajuste", "VAF = 1 (não aplicado; opcional no IFPUG desde 2002)", "Guia FATTO, 2.7"],
        ["Desenvolvimento", "DFP = (UFP + CFP) × VAF; CFP = funções de conversão (operação T)", "Guia FATTO, 2.8"],
        ["Lacunas", "TD ou AR/TR desconhecido: a função fica em Revisão como 'A apurar', sem PF. "
                    "Ausência não é zero.", "Contagem Detalhada (referência)"],
    ]
    for p in dados.get("premissas", []):
        linhas.append(["Premissa", p, "Contagem atual"])
    return linhas


# ---------------------------------------------------------------- recálculo

def recalcular(caminho):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("! soffice não encontrado; recálculo pulado.")
        return None
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [soffice, f"-env:UserInstallation=file://{tmp}/perfil", "--headless", "--calc",
               "--convert-to", "xlsx", "--outdir", os.path.join(tmp, "out"), os.path.abspath(caminho)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=240)
        wb = openpyxl.load_workbook(os.path.join(tmp, "out", os.path.basename(caminho)), data_only=True)
        return {"Sumário!G45": wb["Sumário"]["G45"].value, "Contagem!W5": wb["Contagem"]["W5"].value}


# ---------------------------------------------------------------- principal

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--modelo", default=MODELO_PADRAO)
    ap.add_argument("--recalcular", action="store_true")
    a = ap.parse_args()

    with open(a.entrada, encoding="utf-8") as fh:
        dados = json.load(fh)
    erros, avisos = validar(dados)
    for e in erros:
        print("ERRO:", e)
    if erros:
        sys.exit(f"{len(erros)} erro(s); planilha não gerada.")

    funcoes = dados["funcoes"]
    completas = [f for f in funcoes if f.get("td") is not None and f.get("ar_tr") is not None]
    pendentes = [f for f in funcoes if f.get("td") is None or f.get("ar_tr") is None]

    wb = openpyxl.load_workbook(a.modelo)
    preencher_contagem(wb, dados.get("contagem", {}))
    ultima = preencher_funcoes(wb, completas)

    aba_tabela(wb, "Memória TD",
               ["Identificador", "Função", "Tipo", "Natureza", "Ordem", "Campo / subgrupo / arquivo",
                "Fonte", "Tratamento"],
               montar_memoria(funcoes), [12, 34, 6, 18, 7, 34, 60, 50],
               "Cada TD, TR e AR contado, com a fonte (código, DER ou tela). Colunas físicas e campos "
               "excluídos ficam como evidência e não somam.")
    evid = [[e.get("tipo", ""), e.get("local", ""), e.get("operacao", ""), e.get("funcao", ""),
             e.get("entradas", ""), e.get("saidas", ""), e.get("tabelas", ""), e.get("tratamento", ""),
             e.get("fonte", "")] for e in dados.get("evidencias", [])]
    aba_tabela(wb, "Evidências",
               ["Tipo", "Local (rota / tela / tabela)", "Operação", "Função relacionada", "Entradas",
                "Saídas", "Tabelas / modelos", "Tratamento", "Fonte"],
               evid, [10, 40, 18, 14, 30, 30, 26, 28, 50],
               "Registro técnico para conciliação. Uma rota, tela ou tabela não equivale a uma função.")
    rev = [[r.get("referencia", ""), r.get("situacao", "Pendente"), r.get("item", ""),
            r.get("decisao", ""), r.get("fonte", "")] for r in dados.get("revisao", [])]
    for f in pendentes:
        falta = " e ".join(x for x, v in (("TD", f.get("td")), ("AR/TR", f.get("ar_tr"))) if v is None)
        rev.append([f.get("id"), "A apurar", f"{f.get('tipo')} {f.get('nome')}",
                    f"Apurar {falta}. {f.get('pendencia', '')}".strip(), primeira_fonte(f)])
    aba_tabela(wb, "Revisão",
               ["Referência", "Situação", "Item", "Decisão / evidência necessária", "Fonte"],
               rev, [14, 14, 50, 60, 50],
               "Pendências para fechar a contagem. Itens 'A apurar' não entram em Funções nem no total.")
    aba_tabela(wb, "Regras", ["Regra", "Aplicação", "Referência"], montar_regras(dados), [18, 100, 32],
               "Base metodológica: Guia Prático em APF (Lopes & Braga, 2011 — FATTO) / IFPUG.")

    wb.active = 0
    wb.save(a.saida)

    tot = defaultdict(lambda: [0, 0, 0])
    pf_op = defaultdict(int)
    for f in completas:
        cx = complexidade(f["tipo"], f["td"], f["ar_tr"])
        tot[f["tipo"]][cx] += 1
        pf_op[f.get("operacao", "I")] += PESOS[f["tipo"]][cx]
    total = 0
    print(f"\nPlanilha: {a.saida}  (Funções até a linha {ultima})")
    print(f"{'Tipo':5} {'Baixa':>6} {'Média':>6} {'Alta':>6} {'PF':>6}")
    for t in ("ALI", "AIE", "EE", "SE", "CE"):
        b, m, h = tot[t]
        pf = b * PESOS[t][0] + m * PESOS[t][1] + h * PESOS[t][2]
        total += pf
        print(f"{t:5} {b:6} {m:6} {h:6} {pf:6}")
    print(f"Total PF não ajustado: {total}  | por operação (I/A/E/T): {dict(pf_op)}")
    print(f"Funções completas: {len(completas)} | A apurar (em Revisão): {len(pendentes)}")
    for av in avisos:
        print("AVISO:", av)
    if a.recalcular:
        r = recalcular(a.saida)
        if r:
            print("Recalculado no LibreOffice:", r)
            if r["Sumário!G45"] != total:
                sys.exit(f"DIVERGÊNCIA: fórmulas da planilha = {r['Sumário!G45']}, Python = {total}")
            print("OK: total das fórmulas confere com o cálculo em Python.")


if __name__ == "__main__":
    main()
