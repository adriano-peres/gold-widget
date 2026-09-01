#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ouro Widget — preço do ouro (spot) no desktop.
v5:
  * Tudo da v4 intacto (goldprice.dev como fonte principal do spot USD/BRL,
    baseline PAXG/awesomeapi, camada desktop, menu, arrastar, cache, 429...).
  * NOVO — cotações da CHINA (mapeadas em ~/gold-china-apis/RELATORIO.md),
    normalizadas pelas regras de exibição:
      - preço POR GRAMA     -> sempre BRL  (CNY/g x CNYBRL via awesomeapi)
      - preço por ONÇA TROY -> sempre USD  (mesmo vindo da China:
        CNY/oz ÷ USDCNY, com USDCNY = USDBRL ÷ CNYBRL)
    Fontes (grátis, sem chave):
      - Sina hq.sinajs.cn     : SGE Au99.99, Au(T+D) + hf_XAU (fallback USD)
      - Eastmoney push2delay  : futuro SHFE (113.aum); fallback SGE (118.*)
      - jijinhao/cngold       : base China Gold (JO_52683)
      - xxapi.cn              : barras de ouro de banco
v5.1:
  * Removidas, a pedido do usuário, as cotações:
      - CHINA · SPOT LONDRES (goldprice.org, CNY/oz)
      - CHINA · VAREJO / joalherias (jijinhao JO_42660, marcas xxapi)
      - CHINA · RECICLAGEM (xxapi 24K)
    Mantido o restante: spot principal USD/BRL, bolsas SGE/SHFE, referência
    base China Gold e barras de banco.
  * NOVO — fallback do spot principal: se goldprice.dev falhar, o spot USD
    vem da Sina (hf_XAU) e o BRL é derivado (USD x USDBRL awesomeapi).
  * NOVO — modo --dump: busca tudo sem abrir interface e imprime normalizado.
v5.2:
  * NOVO — cadeia de fallback em TODAS as fontes:
      - spot USD : goldprice.dev -> Sina hf_XAU -> goldprice.org
      - spot BRL : goldprice.dev -> derivado USD x USDBRL -> goldprice.org/BRL
      - FX       : awesomeapi -> currency-api (jsdelivr) -> open.er-api.com
      - baseline : Binance PAXG -> OKX PAXG-USDT (candles diários)
      - semana   : awesomeapi daily -> snapshot histórico jsdelivr (-7d)
      - SHFE     : Eastmoney 113.aum -> Sina nf_AU0
      - base CN  : jijinhao JO_52683 -> derivada do spot intl (hf_XAU x USDCNY)
      - barras   : xxapi -> cache por até 24h (depois sai da lista)
v5.3:
  * Fallbacks disparam também quando a fonte RESPONDE SEM DADO (antes só
    em exceção): Eastmoney SHFE f43="-" -> Sina nf_AU0; jijinhao sem
    JO_52683 -> base derivada.
  * Derivação (BRL e base CN) só com dado fresco: exige spot USD deste
    ciclo e câmbio com até FX_MAX_AGE (15 min); câmbio valida valores > 0.
  * Variação "no dia" pausa se o baseline (PAXG) for de outro dia UTC.
  * Indicador separado: "spot offline (cache)" no rodapé principal;
    China segue online com idade própria. Cache salvo em todo ciclo.
  * Lock entre poller e "Atualizar agora"; save_cache atômico
    (.tmp + os.replace); --dump tolera pct nulo.
v5.4 (ALTERAÇÃO LOCAL — não enviada ao repositório):
  * NOVO — seção "EUA · COMBUSTÍVEL": média semanal de VAREJO (bomba) da
    gasolina regular e do diesel on-highway nos EUA, em US$/gal com impostos.
   Fonte grátis sem chave: AmericasOilWatch /api/v1/us-prices, que replica
   as séries EIA EMM_EPMR / EMD_EPD2D (rota petroleum/pri/gnd).
v5.5 (ALTERAÇÃO LOCAL — não enviada ao repositório):
   * NOVO — fallback do combustível EUA (antes fonte única). Cadeia inteira
     de VAREJO de bomba com impostos (média nacional semanal; nada de
     atacado/platts/barril):
       - AmericasOilWatch                    [principal, como no v5.4]
       - EIA dnav oficial (HTML semanal)     [mesmas séries, fonte raiz]
       - FRED fredgraph.csv (GASREGW)        [cobre só a gasolina; o FRED
         não publica diesel de varejo]
       - EIA API v2 (petroleum/pri/gnd)      [se EIA_API_KEY no ambiente;
         chave grátis em eia.gov/opendata/register.php]
   * Cache de combustível vence após 14 dias (2 releases semanais
     perdidas), mesmo padrão das barras de banco (24 h).
v5.6 (fusão das forks local + instalada):
   * NOVO — seção "COMEX · FUTURO (GC=F)" (que só existia na cópia
     instalada): futuro ouro contínuo via chart do Yahoo Finance (grátis,
     sem chave), USD/oz, variação vs fechamento anterior e contango vs
     spot. O contínuo rola sozinho p/ o contrato mais líquido (dez/26;
     em nov/dez, fev/27). Falha isoladamente; marca "(cache)" após
     FUT_STALE (10 min).
   * O repo passa a ter TUDO: spot+China+COMEX+combustível EUA (v5.5).
v4: BRL por grama; camada desktop; polling 90 s; backoff 429; baseline PAXG.
Fonte principal do spot: goldprice.dev. Stdlib apenas (tkinter+urllib).
"""

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    import tkinter as tk
except Exception:  # no display / sem tk
    tk = None

# ------------------------------- CONFIG -------------------------------
API_URL       = "https://api.goldprice.dev/v1/prices"
SYMBOLS       = ("XAU-USD-SPOT", "XAU-BRL-SPOT")   # busca USD e BRL
POLL_SECONDS  = 90                                 # teto anônimo ~100 req/h por IP
NET_TIMEOUT   = 8                                  # timeout de rede (s)
PAXG_KLINES   = ("https://api.binance.com/api/v3/klines"
                 "?symbol=PAXGUSDT&interval=1d&limit=8")  # hoje + 7 dias (semana)
FX_URL        = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
FX_URL_ALL    = "https://economia.awesomeapi.com.br/json/last/USD-BRL,CNY-BRL"
FX_URL_WEEK   = "https://economia.awesomeapi.com.br/json/daily/USD-BRL/8"
# v5.2 — fallbacks do câmbio e do baseline
FX_JSD        = ("https://cdn.jsdelivr.net/npm/@fawazahmed0/"
                 "currency-api@latest/v1/currencies/usd.json")
FX_ERAPI      = "https://open.er-api.com/v6/latest/USD"
FX_JSD_HIST   = ("https://cdn.jsdelivr.net/npm/@fawazahmed0/"
                 "currency-api@{date}/v1/currencies/usd.json")
PAXG_KLINES_OKX = ("https://www.okx.com/api/v5/market/candles"
                   "?instId=PAXG-USDT&bar=1Dutc&limit=8")
STATE_DIR     = os.path.expanduser("~/.local/share/gold-widget")
CACHE_FILE    = os.path.join(STATE_DIR, "last_price.json")
LOG_FILE      = os.path.join(STATE_DIR, "widget.log")
MARGIN        = 16                                 # distância da borda lateral
MARGIN_Y      = 40                                 # abaixo da barra do topo
TROY_OZ_GRAMS = 31.1034768                         # 1 onça troy em gramas

# ------------------------ CONFIG · FONTES CHINA ------------------------
SINA_URL_FMT  = "https://hq.sinajs.cn/list={codes}"
SINA_REFERER  = "https://finance.sina.com.cn"
SINA_CODES    = ("gds_AU9999", "gds_AUTD", "hf_XAU")
EASTMONEY_FMT = ("https://push2delay.eastmoney.com/api/qt/stock/get"
                 "?secid={secid}&fields=f43,f60,f170"
                 "&ut=fa5fd1943c7b386f172d6893dbfba10b")
EM_SHFE_AU    = "113.aum"                          # futuro SHFE contrato principal
EM_SGE        = {"sge_au9999": "118.AU9999",       # fallback p/ quando Sina falha
                 "sge_autd":   "118.AUTD"}
JIJINHAO_URL  = ("https://api.jijinhao.com/quoteCenter/realTime.htm"
                 "?codes=JO_52683")
XXAPI_URL     = "https://v2.xxapi.cn/api/goldprice"
# jijinhao bloqueia UA "de robô"; precisa de UA de navegador
BROWSER_UA    = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
# v5.2 — mais fallbacks
GPORG_URL     = "https://data-asg.goldprice.org/dbXRates/{curr}"
SINA_FUT_CODE = "nf_AU0"                             # futuro SHFE ouro (main) na Sina
BANKS_MAX_AGE = 24 * 3600                            # cache de barras vale 24h
FX_MAX_AGE    = 15 * 60                              # câmbio mais velho que isso não deriva

# v5.6 — futuro COMEX (contrato contínuo GC=F) via chart do Yahoo
YAHOO_GC_URL  = ("https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
                 "?interval=1d&range=5d")            # 5 barras: atual + anteriores
FUT_STALE     = 10 * 60                              # acima disso mostra "(cache)"
MONTH_PT      = {"Jan": "jan", "Feb": "fev", "Mar": "mar", "Apr": "abr",
                 "May": "mai", "Jun": "jun", "Jul": "jul", "Aug": "ago",
                 "Sep": "set", "Oct": "out", "Nov": "nov", "Dec": "dez"}

# ----------------- CONFIG · COMBUSTÍVEL EUA (média de varejo) --------------
# Todas as fontes são a MESMA métrica: média nacional semanal de BOMBA
# (varejo, com impostos) da EIA — gasolina regular (EMM_EPMR_PTE_NUS_DPG)
# e diesel on-highway (EMD_EPD2D_PTE_NUS_DPG). Nada de atacado.
AOW_URL       = "https://americasoilwatch.com/api/v1/us-prices"
EIA_DNAV_FMT  = ("https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx"
                 "?n=PET&s={series}&f=W")          # página oficial (HTML)
EIA_DNAV_GAS  = "EMM_EPMR_PTE_NUS_DPG"             # gasolina regular varejo
EIA_DNAV_DIE  = "EMD_EPD2D_PTE_NUS_DPG"            # diesel on-highway varejo
FRED_GAS_URL  = ("https://fred.stlouisfed.org/graph/fredgraph.csv"
                 "?id=GASREGW&cosd={date}")        # espelho FRED: só gasolina
EIA_V2_URL    = "https://api.eia.gov/v2/petroleum/pri/gnd/data/"
FUEL_MAX_AGE  = 14 * 86400                         # cache vence (2 releases)

# Tradução dos nomes em chinês vindos da xxapi (fonte CJK não é necessária)
BANK_TR = {
    "工商银行如意金条": "ICBC Ruyi",
    "中国银行金条":     "Banco da China",
    "建设银行龙鼎金条": "CCB Longding",
    "农行传世之宝金条": "ABC Chuanshibao",
    "浦发银行投资金条": "SPD Invest.",
    "和谐平安金条":     "Ping An",
}

# ------------------------------- CORES ---------------------------------
BG         = "#101318"
BORDER     = "#c9a227"
TITLE      = "#c9a227"
TXT_USD    = "#f5f5f5"
TXT_BRL    = "#e6dbaa"
TXT_DIM    = "#8a8f98"
UP_COLOR   = "#4caf7d"
DOWN_COLOR = "#e05252"

# ------------------------------- LOG -----------------------------------
def log(msg):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass

# ----------------------------- FORMATAÇÃO -------------------------------
def fmt_usd(v):
    """4,615.47 (padrão US)"""
    return f"{v:,.2f}"

def fmt_brl(v):
    """23.823,37 (padrão BR)"""
    s = f"{v:,.2f}"
    return s.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")

def fmt_pct(p):
    arrow = "▲" if p >= 0 else "▼"
    return f"{arrow} {abs(p):.2f}%"

def _has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)

def _chg_pct(price, chg):
    """Variação % (semanal) a partir do delta absoluto em US$/gal."""
    base = (price - chg) if price is not None and chg is not None else None
    if not base:
        return None
    return chg / base * 100.0

# ------------------------------- HTTP -----------------------------------
def _http_get(url, headers=None, timeout=NET_TIMEOUT):
    hdrs = {"User-Agent": "gold-widget/5.0", "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def _get_json(url, headers=None, timeout=NET_TIMEOUT):
    return json.loads(_http_get(url, headers, timeout).decode("utf-8"))

# --------------------- FETCH · FONTES ORIGINAIS (v4) ---------------------
def fetch_price(symbol):
    """Busca o preço de um símbolo. Retorna dict ou lança exceção."""
    url = f"{API_URL}?symbol={urllib.parse.quote(symbol)}"
    data = _get_json(url)
    if not data.get("symbols"):
        return None
    s = data["symbols"][0]
    return {
        "price": float(s.get("price")),
        "bid":   float(s["bid"]) if s.get("bid")   is not None else None,
        "ask":   float(s["ask"]) if s.get("ask")   is not None else None,
    }

def try_fetch(symbol):
    """(dados|None, retry_after|None). 429 devolve o retry_after da API."""
    try:
        return fetch_price(symbol), None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            ra = 300.0
            try:
                body = json.loads(e.read().decode("utf-8"))
                ra = float(body.get("retry_after_seconds", 300))
            except Exception:
                pass
            return None, ra
        log(f"HTTP {e.code} ao buscar {symbol}")
        return None, None
    except Exception as e:
        log(f"falha ao buscar {symbol}: {e}")
        return None, None

def fetch_daily_baseline():
    """Abertura do dia (UTC) do ouro via PAXG (Binance -> OKX) + variação
    diária do USDBRL; referência de 7 dias (PAXG + USDBRL) para a variação
    na semana. Fontes gratuitas sem chave, fora da quota da goldprice.dev."""
    paxg_open, paxg_week_open = _paxg_daily_opens()
    fx_pct = 0.0
    fx_week_pct = 0.0
    usdbrl_now = None
    try:
        d = _get_json(FX_URL)["USDBRL"]
        fx_pct = float(d["pctChange"])   # variação diária do dólar vs real
        usdbrl_now = float(d["bid"])
    except Exception as e:
        log(f"FX awesomeapi indisponível ({e}); variação BRL só com ouro")
    if usdbrl_now is not None:
        alvo = time.time() - 7 * 86400
        try:
            hist = _get_json(FX_URL_WEEK)          # série diária, mais novo 1º
            ref = min((r for r in hist if r.get("timestamp")),
                      key=lambda r: abs(int(r["timestamp"]) - alvo),
                      default=None)
            if ref:
                fx_week_pct = (usdbrl_now / float(ref["bid"]) - 1.0) * 100.0
        except Exception as e:
            # fallback semanal: snapshot histórico da currency-api (-7d)
            try:
                dia = datetime.fromtimestamp(alvo, timezone.utc).strftime("%Y-%m-%d")
                h = _get_json(FX_JSD_HIST.format(date=dia))
                fx_week_pct = (usdbrl_now / float(h["usd"]["brl"]) - 1.0) * 100.0
            except Exception as e2:
                log(f"FX semanal indisponível (awesomeapi: {e} · "
                    f"currency-api: {e2}); variação BRL só com ouro")
    return {
        "paxg_open": paxg_open,
        "paxg_week_open": paxg_week_open,
        "fx_day_pct": fx_pct,
        "fx_week_pct": fx_week_pct,
        "day": datetime.now(timezone.utc).date().isoformat(),
    }

# ------------------------- FETCH · FONTES CHINA --------------------------
def fetch_fx():
    """USDBRL e CNYBRL. Cadeia: awesomeapi -> currency-api (jsdelivr)
    -> open.er-api.com. USDCNY é derivado da razão."""
    errs = []
    try:
        d = _get_json(FX_URL_ALL)
        usdbrl = float(d["USDBRL"]["bid"])
        cnybrl = float(d["CNYBRL"]["bid"])
        if usdbrl <= 0 or cnybrl <= 0:
            raise ValueError("câmbio <= 0")
        return {"usdbrl": usdbrl, "cnybrl": cnybrl,
                "usdcny": usdbrl / cnybrl, "src": "awesomeapi",
                "ts": time.time()}
    except Exception as e:
        errs.append(f"awesomeapi: {e}")
    try:
        d = _get_json(FX_JSD)
        usdbrl = float(d["usd"]["brl"])
        cnybrl = float(d["usd"]["cny"])
        if usdbrl <= 0 or cnybrl <= 0:
            raise ValueError("câmbio <= 0")
        return {"usdbrl": usdbrl, "cnybrl": cnybrl,
                "usdcny": usdbrl / cnybrl, "src": "currency-api",
                "ts": time.time()}
    except Exception as e:
        errs.append(f"currency-api: {e}")
    try:
        d = _get_json(FX_ERAPI)
        usdbrl = float(d["rates"]["BRL"])
        cnybrl = float(d["rates"]["CNY"])
        if usdbrl <= 0 or cnybrl <= 0:
            raise ValueError("câmbio <= 0")
        return {"usdbrl": usdbrl, "cnybrl": cnybrl,
                "usdcny": usdbrl / cnybrl, "src": "er-api",
                "ts": time.time()}
    except Exception as e:
        errs.append(f"er-api: {e}")
    raise RuntimeError("FX sem fonte viva (" + "; ".join(errs) + ")")

def _fx_fresh(fx):
    """Câmbio utilizável p/ derivação: presente e com até FX_MAX_AGE."""
    return bool(fx and fx.get("usdbrl")
                and time.time() - fx.get("ts", 0) <= FX_MAX_AGE)

def fetch_goldprice_org(curr="USD"):
    """Spot Londres via goldprice.org (fallback do spot principal).
    xauPrice na moeda pedida; pcXau = variação % no dia."""
    d = _get_json(GPORG_URL.format(curr=curr),
                  {"User-Agent": BROWSER_UA,
                   "Referer": "https://goldprice.org/"})
    it = (d.get("items") or [{}])[0]
    price = float(it["xauPrice"])
    if price <= 0:
        raise ValueError("goldprice.org sem preço")
    return {"price": price,
            "pct": _to_float(it.get("pcXau")),
            "prev_close": _to_float(it.get("xauClose"))}

def fetch_gc_future():
    """Futuro COMEX ouro contínuo (GC=F) pelo chart do Yahoo (grátis, sem
    chave). GC=F acompanha o contrato mais líquido (hoje dez/26; rola sozinho
    no vencimento). Preço = regularMarketPrice; referência = fech. anterior.
    range=5d dá barras suficientes p/ achar o fechamento da sessão anterior."""
    d = _get_json(YAHOO_GC_URL, {"User-Agent": BROWSER_UA})
    res = ((d.get("chart") or {}).get("result") or [])
    if not res:
        raise ValueError("Yahoo GC=F sem resultado")
    m = res[0].get("meta") or {}
    closes = [c for c in ((((res[0].get("indicators") or {}).get("quote")
                            or [{}])[0]).get("close") or []) if c is not None]
    price = m.get("regularMarketPrice")
    if price is None and closes:
        price = closes[-1]
    prev = closes[-2] if len(closes) >= 2 else m.get("chartPreviousClose")
    price, prev = _to_float(price), _to_float(prev)
    if not price or not prev or price <= 0 or prev <= 0:
        raise ValueError("Yahoo GC=F sem preço válido")
    return {"price": price, "prev_close": prev,
            "pct": (price / prev - 1.0) * 100.0,
            "name": m.get("shortName") or "", "ts": time.time()}

def fetch_sina_future():
    """Futuro SHFE ouro (nf_AU0, contrato main) direto da Sina.
    Campos nf_: [1]hora [2]abert. [3]máx [4]mín [8]último [10]liquidação ant."""
    txt = _http_get(SINA_URL_FMT.format(codes=SINA_FUT_CODE),
                    {"Referer": SINA_REFERER}).decode("gbk", "replace")
    m = re.search(r'hq_str_' + SINA_FUT_CODE + r'="([^"]*)"', txt)
    if not m:
        raise ValueError("resposta Sina nf_ sem payload")
    f = m.group(1).split(",")
    last, prev = float(f[8]), float(f[10])
    if last <= 0 or prev <= 0:
        raise ValueError("Sina nf_AU0 com preço inválido")
    return {"price": last, "pct": (last / prev - 1.0) * 100.0}

def _paxg_daily_opens():
    """(abertura do dia UTC, abertura de 7 dias atrás) do PAXG.
    Tenta Binance; fallback: OKX PAXG-USDT (mesma forma de candle)."""
    try:
        k = _get_json(PAXG_KLINES)
        opens = [float(r[1]) for r in k]          # ascendente
    except Exception as e:
        log(f"Binance PAXG indisponível ({e}); tentando OKX")
        rows = (_get_json(PAXG_KLINES_OKX).get("data") or [])
        opens = [float(r[1]) for r in sorted(rows, key=lambda r: int(r[0]))]
    if not opens:
        raise ValueError("sem candles de PAXG em nenhuma bolsa")
    return opens[-1], (opens[0] if len(opens) >= 8 else None)

_SINA_RE = re.compile(r'var hq_str_(\w+)="([^"]*)"')

def fetch_sina():
    """SGE (Au99.99, Au(T+D)) + spot Londres USD (hf_XAU), tudo num request.
    Encoding GBK; exige Referer. Campos gds_: [0]último [6]hora [7]fech.ant.
    [12]data. hf_XAU: [0]último USD/oz [7]fechamento anterior."""
    url = SINA_URL_FMT.format(codes=",".join(SINA_CODES))
    txt = _http_get(url, {"Referer": SINA_REFERER}).decode("gbk", "replace")
    out = {}
    for code, payload in _SINA_RE.findall(txt):
        f = payload.split(",")
        if len(f) < 13:
            continue
        try:
            last = float(f[0])
            prev = float(f[7])
        except ValueError:
            continue
        if last <= 0:
            continue
        out[code] = {"price": last, "prev_close": prev,
                     "pct": (last / prev - 1.0) * 100.0 if prev > 0 else None,
                     "time": f[6], "date": f[12]}
    return out

def fetch_eastmoney(secid):
    """Quote individual; preços vêm x100 (f170 = variação % x100)."""
    d = _get_json(EASTMONEY_FMT.format(secid=secid))
    data = d.get("data") or {}
    price, pct = data.get("f43"), data.get("f170")
    if price in (None, "-", ""):
        return None
    return {"price": float(price) / 100.0,
            "pct": float(pct) / 100.0 if pct not in (None, "-", "") else None}

def fetch_jijinhao():
    """JO_52683 = base China Gold. CNY/g."""
    raw = _http_get(JIJINHAO_URL, {"Referer": "https://m.cngold.org/",
                                   "User-Agent": BROWSER_UA}).decode("utf-8", "replace")
    s, e = raw.find("{"), raw.rfind("}")
    if s < 0 or e <= s:
        raise ValueError("resposta jijinhao sem JSON")
    d = json.loads(raw[s:e + 1])
    out = {}
    for code in ("JO_52683",):
        q = d.get(code) or {}
        if q.get("q2"):
            out[code] = float(q["q2"])
    return out

def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def fetch_xxapi():
    """Barras de ouro de banco (bank_gold_bar_price). CNY/g."""
    d = _get_json(XXAPI_URL).get("data") or {}
    banks = []
    for i, b in enumerate(d.get("bank_gold_bar_price") or []):
        p = _to_float(b.get("price"))
        if p is None:
            continue
        name = BANK_TR.get(b.get("bank"), b.get("bank", f"Banco {i+1}"))
        if _has_cjk(name):
            name = f"Banco {i+1}"
        banks.append({"name": name, "cny_g": p})
    return {"banks": banks}

_NAV_MON = {m: i for i, m in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
     "Sep", "Oct", "Nov", "Dec"), 1)}

def _parse_dnav(html):
    """Tabela semanal do dnav (EIA) -> [(data, US$/gal)] crescente.
    Cada <tr> traz o mês/ano (célula B6) e pares data (B5) / preço (B3)."""
    pat = (r"class=['\"]B5['\"]>\s*(\d{2})/(\d{2})\s*&nbsp;</td>\s*"
           r"<td[^>]*class=['\"]B3['\"]>\s*([0-9]+\.[0-9]+)")
    out = {}
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        ym = re.search(r"(\d{4})-([A-Za-z]{3})\s*<", tr)
        if not ym:
            continue
        y, mo = int(ym.group(1)), _NAV_MON.get(ym.group(2))
        if not mo:
            continue
        for m, dd, v in re.findall(pat, tr):
            try:
                out[datetime(y, mo, int(dd))] = float(v)
            except ValueError:
                continue
    return sorted(out.items())

def _fuel_weeks(hist):
    """((última semana, preço), (penúltima, preço)) ou None se <2 semanas."""
    if len(hist) < 2:
        return None
    return hist[-1], hist[-2]

def _us_fuel_aow():
    """Principal: AmericasOilWatch (JSON pronto, replica as séries EIA)."""
    d = _get_json(AOW_URL)
    gas, die = _to_float(d.get("gasolineUsdGal")), _to_float(d.get("dieselUsdGal"))
    if not gas or not die or gas <= 0 or die <= 0:
        raise ValueError("resposta sem preço válido")
    return {"gas": gas, "gas_chg": _to_float(d.get("gasolineChangeUsdGal")),
            "diesel": die, "diesel_chg": _to_float(d.get("dieselChangeUsdGal")),
            "week": d.get("weekEnding"), "prov": "EIA via AmericasOilWatch"}

def _us_fuel_dnav():
    """Fallback 1: página oficial da EIA (dnav) com a tabela semanal das
    MESMAS séries de varejo. Variação semanal = vs semana anterior."""
    out, weeks, got = {}, [], 0
    for series, key in ((EIA_DNAV_GAS, "gas"), (EIA_DNAV_DIE, "diesel")):
        try:
            # dnav é lento via urllib (~10s); fallback merece timeout frouxo
            html = _http_get(EIA_DNAV_FMT.format(series=series),
                             {"User-Agent": BROWSER_UA},
                             timeout=30).decode("windows-1252", "replace")
            wk = _fuel_weeks(_parse_dnav(html))
            if not wk:
                raise ValueError("tabela sem semanas suficientes")
        except Exception as e:
            log(f"dnav {series} indisponível: {e}")
            continue
        (d1, v1), (d0, v0) = wk
        out[key] = v1
        out[key + "_chg"] = round(v1 - v0, 3)
        weeks.append(d1.strftime("%Y-%m-%d"))
        got += 1
    if not got:
        raise ValueError("nenhuma série disponível")
    if weeks:
        out["week"] = max(weeks)
    out["prov"] = "EIA dnav"
    return out

def _us_fuel_fred():
    """Fallback 2: FRED (fredgraph.csv, sem chave) espelha a gasolina
    regular semanal da EIA. Não cobre diesel (FRED não tem a série)."""
    cosd = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    txt = _http_get(FRED_GAS_URL.format(date=cosd), timeout=30).decode(
        "utf-8", "replace")
    hist = []
    for ln in txt.splitlines()[1:]:          # 1ª linha é o cabeçalho
        parts = ln.split(",")
        if len(parts) == 2 and parts[1] not in (".", ""):
            try:
                hist.append((datetime.strptime(parts[0], "%Y-%m-%d"),
                             float(parts[1])))
            except ValueError:
                continue
    wk = _fuel_weeks(sorted(hist))
    if not wk:
        raise ValueError("CSV sem semanas suficientes")
    (d1, v1), (d0, v0) = wk
    return {"gas": v1, "gas_chg": round(v1 - v0, 3),
            "week": d1.strftime("%Y-%m-%d"), "prov": "FRED"}

def _us_fuel_eia_v2(key):
    """Fallback 3: API oficial da EIA (v2). Exige chave grátis registrada
    na variável de ambiente EIA_API_KEY (eia.gov/opendata/register.php)."""
    q = urllib.parse.urlencode({
        "api_key": key, "frequency": "weekly", "data[0]": "value",
        "facets[series][]": [EIA_DNAV_GAS, EIA_DNAV_DIE],
        "sort[0][column]": "period", "sort[0][direction]": "desc",
        "length": "10"})
    d = _get_json(EIA_V2_URL + "?" + q)
    rows = (d.get("response") or {}).get("data") or []
    out, weeks, got = {}, [], 0
    for series, key2 in ((EIA_DNAV_GAS, "gas"), (EIA_DNAV_DIE, "diesel")):
        vals = sorted((r.get("period"), _to_float(r.get("value")))
                      for r in rows if r.get("series") == series)
        vals = [(p, v) for p, v in vals if p and v and v > 0]
        wk = _fuel_weeks(vals)
        if not wk:
            log(f"EIA v2 {series} indisponível: sem dados")
            continue
        (p1, v1), (p0, v0) = wk
        out[key2] = v1
        out[key2 + "_chg"] = round(v1 - v0, 3)
        weeks.append(p1)
        got += 1
    if not got:
        raise ValueError("nenhuma série disponível")
    if weeks:
        out["week"] = max(weeks)
    out["prov"] = "EIA API"
    return out

def _merge_fuel(base, extra):
    """Preenche lacunas (gas/diesel) sem sobrescrever o que já veio antes."""
    if not base:
        return extra
    for k in ("gas", "gas_chg", "diesel", "diesel_chg"):
        if base.get(k) is None and extra.get(k) is not None:
            base[k] = extra[k]
    wks = [w for w in (base.get("week"), extra.get("week")) if w]
    if wks:
        base["week"] = max(wks)
    return base

def fetch_us_fuel():
    """Média semanal de VAREJO (bomba) nos EUA: gasolina regular e diesel
    on-highway, US$/gal com impostos — nada de atacado. Cadeia:
    AmericasOilWatch -> EIA dnav (HTML oficial) -> FRED (só gasolina)
    -> EIA API v2 (se EIA_API_KEY). Cada estágio preenche só o que falta."""
    out, provs, errs = {}, [], []
    try:
        out = _us_fuel_aow()
        provs.append(out.pop("prov"))
    except Exception as e:
        errs.append(f"AOW: {e}")
    if not (out.get("gas") and out.get("diesel")):
        try:
            out = _merge_fuel(out, _us_fuel_dnav())
            provs.append(out.pop("prov", "EIA dnav"))
        except Exception as e:
            errs.append(f"EIA dnav: {e}")
    if out.get("gas") is None:
        try:
            out = _merge_fuel(out, _us_fuel_fred())
            provs.append(out.pop("prov", "FRED"))
        except Exception as e:
            errs.append(f"FRED: {e}")
    if (not (out.get("gas") and out.get("diesel"))
            and os.environ.get("EIA_API_KEY")):
        try:
            out = _merge_fuel(out, _us_fuel_eia_v2(os.environ["EIA_API_KEY"]))
            provs.append(out.pop("prov", "EIA API"))
        except Exception as e:
            errs.append(f"EIA API: {e}")
    if out.get("gas") is None and out.get("diesel") is None:
        raise RuntimeError("combustível sem fonte viva (" + "; ".join(errs) + ")")
    out["src"] = " + ".join(provs) if provs else "EIA"
    out["ts"] = time.time()
    return out

def collect_china(last):
    """Popula last['fx'] e last['china'] com TODAS as fontes chinesas; cada
    fonte falha isoladamente. Retorna o rec hf_XAU (spot Londres USD na Sina)
    para fallback do spot principal, ou None."""
    china = last.setdefault("china", {})
    now = time.time()
    ok = 0
    sina_xau = None

    try:
        last["fx"] = fetch_fx()
    except Exception as e:
        log(f"FX awesomeapi (USD/CNY) indisponível: {e}")

    try:
        sina = fetch_sina()
        for code, key in (("gds_AU9999", "sge_au9999"), ("gds_AUTD", "sge_autd")):
            r = sina.get(code)
            if r:
                china[key] = {"cny_g": r["price"], "pct": r["pct"],
                              "dt": f"{r['date']} {r['time']}",
                              "src": "Sina", "ts": now}
                ok += 1
        sina_xau = sina.get("hf_XAU")
        if sina_xau:
            ok += 1
    except Exception as e:
        log(f"Sina indisponível: {e}")

    # SGE via Eastmoney — apenas quando a Sina não entregou dado fresco
    for key, secid in EM_SGE.items():
        cur = china.get(key)
        if cur and now - cur.get("ts", 0) < POLL_SECONDS * 2:
            continue
        try:
            r = fetch_eastmoney(secid)
            if r:
                china[key] = {"cny_g": r["price"], "pct": r["pct"],
                              "dt": None, "src": "Eastmoney", "ts": now}
                ok += 1
        except Exception as e:
            log(f"Eastmoney {secid} indisponível: {e}")

    try:
        r = fetch_eastmoney(EM_SHFE_AU)
    except Exception as e:
        log(f"Eastmoney SHFE indisponível ({e}); tentando Sina nf_AU0")
        r = None
    if r:
        china["shfe"] = {"cny_g": r["price"], "pct": r["pct"],
                         "src": "Eastmoney", "ts": now}
        ok += 1
    else:
        # dispara também quando a Eastmoney responde SEM dado (f43 "-")
        try:
            r = fetch_sina_future()
            china["shfe"] = {"cny_g": r["price"], "pct": r["pct"],
                             "src": "Sina", "ts": now}
            ok += 1
        except Exception as e2:
            log(f"Sina nf_AU0 também indisponível: {e2}")

    err_jjh = None
    try:
        j = fetch_jijinhao()
    except Exception as e:
        err_jjh, j = e, {}
    if "JO_52683" in j:
        china["base"] = {"cny_g": j["JO_52683"], "ts": now}
        ok += 1
    else:
        # fallback da base: spot internacional convertido p/ CNY por grama
        # (também quando a resposta vem sem o código pedido)
        motivo = f"jijinhao indisponível ({err_jjh})" if err_jjh \
                 else "jijinhao sem JO_52683"
        fxv = last.get("fx") or {}
        if sina_xau and _fx_fresh(fxv) and fxv.get("usdcny"):
            china["base"] = {"cny_g": (sina_xau["price"] * fxv["usdcny"]
                                       / TROY_OZ_GRAMS),
                             "src": "derivado hf_XAU", "ts": now}
            ok += 1
            log(f"{motivo}; base derivada do spot intl")
        else:
            log(f"{motivo}; sem base alternativa")

    try:
        x = fetch_xxapi()
        if x["banks"]:
            china["banks"] = [{**b, "ts": now} for b in x["banks"]]
            ok += 1
    except Exception as e:
        log(f"xxapi indisponível ({e}); mantendo barras do cache")
    # barras: sem fonte viva há mais de 24h -> some (evita preço velho na tela)
    banks = china.get("banks")
    if banks and now - max(b.get("ts", 0) for b in banks) > BANKS_MAX_AGE:
        china.pop("banks", None)
        log("barras de banco expiradas (>24h sem xxapi); removidas")

    # cotações removidas a pedido do usuário (limpa resíduos do cache antigo)
    for k in ("london_cny", "ztf", "brands", "recycle24"):
        china.pop(k, None)

    if ok:
        china["ts_last_ok"] = now
    return sina_xau

# ------------------------------- CACHE ----------------------------------
def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_cache(data):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, CACHE_FILE)     # atômico: crash no meio não corrompe
    except Exception:
        pass


# --------------------- CAMADA "ACIMA DOS ÍCONES" (X11) ------------------
# No GNOME/Mutter (X11) os ícones do desktop são uma janela
# _NET_WM_WINDOW_TYPE_DESKTOP da extensão DING. Janelas DESKTOP ficam todas
# na camada mais baixa (META_LAYER_DESKTOP) e a ordem ENTRE elas é apenas a
# ordem de criação -> corrida na inicialização: quem mapeia por último fica
# por cima. Para ficar SEMPRE acima dos ícones e abaixo das janelas normais,
# pedimos ao WM o estado _NET_WM_STATE_BELOW (client message): o Mutter
# coloca a janela na META_LAYER_BOTTOM, que fica entre a camada DESKTOP
# (ícones) e a camada NORMAL (janelas). Verificado no fonte do mutter 46:
# meta_window_get_default_layer() testa wm_state_below ANTES do tipo
# DESKTOP; reload/client-message de _NET_WM_STATE honra BELOW em runtime.
_NET_WM_STATE_REMOVE = 0
_NET_WM_STATE_ADD    = 1
_X11 = None

def _x11_lib():
    """Carrega libX11 via ctypes (só stdlib). None se indisponível."""
    global _X11
    if _X11 is not None:
        return _X11 or None
    try:
        import ctypes, ctypes.util
        name = ctypes.util.find_library("X11")
        if not name:
            _X11 = False
            return None
        x11 = ctypes.CDLL(name)
        x11.XOpenDisplay.restype  = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XInternAtom.restype   = ctypes.c_ulong
        x11.XInternAtom.argtypes  = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x11.XDefaultRootWindow.restype  = ctypes.c_ulong
        x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
                                   ctypes.c_long, ctypes.c_void_p]
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                   ctypes.POINTER(ctypes.c_ulong),
                                   ctypes.POINTER(ctypes.c_ulong),
                                   ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),
                                   ctypes.POINTER(ctypes.c_uint)]
        x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        _X11 = x11
        return x11
    except Exception:
        _X11 = False
        return None

def _build_client_message_struct():
    import ctypes
    class XClientMessageEvent(ctypes.Structure):
        _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong),
                    ("send_event", ctypes.c_int), ("display", ctypes.c_void_p),
                    ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                    ("format", ctypes.c_int), ("data", ctypes.c_long * 5)]
    return XClientMessageEvent

def x11_set_below_state(root, add=True):
    """Envia client message _NET_WM_STATE add/remove BELOW para a janela.

    root: toplevel do tkinter. A janela gerenciada pelo WM no X11 é o
    "wrapper" que o Tk cria no map (pai do toplevel no XQueryTree), então o
    client message precisa usar o id dela.
    """
    try:
        x11 = _x11_lib()
        if not x11 or os.environ.get("XDG_SESSION_TYPE", "x11") != "x11":
            return False
        import ctypes
        dpy = x11.XOpenDisplay(os.environ.get("DISPLAY", ":0").encode())
        if not dpy:
            return False
        try:
            toplevel = root.winfo_id()
            root_r = ctypes.c_ulong(); parent = ctypes.c_ulong()
            children = ctypes.POINTER(ctypes.c_ulong)(); n = ctypes.c_uint()
            x11.XQueryTree(dpy, toplevel, ctypes.byref(root_r),
                           ctypes.byref(parent), ctypes.byref(children),
                           ctypes.byref(n))
            wrapper = parent.value if parent.value else toplevel
            x11.XSync(dpy, 0)
            net_wm_state = x11.XInternAtom(dpy, b"_NET_WM_STATE", 0)
            below        = x11.XInternAtom(dpy, b"_NET_WM_STATE_BELOW", 0)
            rootwin      = x11.XDefaultRootWindow(dpy)
            ev = _build_client_message_struct()()
            ev.type = 33                      # ClientMessage
            ev.serial = 0
            ev.send_event = 1
            ev.display = dpy
            ev.window = wrapper
            ev.message_type = net_wm_state
            ev.format = 32
            ev.data[0] = _NET_WM_STATE_ADD if add else _NET_WM_STATE_REMOVE
            ev.data[1] = below
            ev.data[2] = 0
            SubstructureRedirectMask = 1 << 20
            SubstructureNotifyMask   = 1 << 19
            x11.XSendEvent(dpy, rootwin, 0,
                           SubstructureRedirectMask | SubstructureNotifyMask,
                           ctypes.byref(ev))
            x11.XFlush(dpy)
            return True
        finally:
            pass  # display fechado no GC; XCloseDisplay opcional aqui
    except Exception as e:
        log(f"falha ao ajustar _NET_WM_STATE_BELOW: {e}")
        return False

# ------------------------------- WIDGET ----------------------------------
class GoldWidget:
    def __init__(self, root):
        self.root = root
        self.stop = threading.Event()
        self.last = load_cache() or {}
        self.baseline = self.last.get("baseline") or None
        self.spot_offline = True                 # até o 1º spot ok
        self._poll_lock = threading.Lock()       # poller x "Atualizar agora"

        root.title("OuroWidget")
        # v3: camada da área de trabalho (_NET_WM_WINDOW_TYPE_DESKTOP): o WM
        # mantém o widget acima do papel de parede e ABAIXO de qualquer outra
        # janela. (overrideredirect fica como fallback: no GNOME/Mutter ela
        # tira a janela do gerenciamento do WM e ela acaba sempre no topo.)
        self.var_top = tk.BooleanVar(value=False)
        self._desktop_layer = False
        try:
            root.attributes("-type", "desktop")     # precisa ser antes do map
            self._desktop_layer = True
        except Exception:
            root.overrideredirect(True)             # fallback: sem borda
        root.attributes("-topmost", False)
        try:
            root.attributes("-alpha", 0.97)
        except Exception:
            pass

        # v5.1: só o tipo DESKTOP deixa o widget na MESMA camada da janela de
        # ícones do DING (e a ordem entre elas é corrida de inicialização —
        # por isso ele amanhecia atrás dos ícones). Pedir _NET_WM_STATE_BELOW
        # move a janela para a camada BOTTOM: sempre acima dos ícones e
        # sempre abaixo das janelas normais. O estado precisa ser enviado
        # DEPOIS do map (client message), por isso o after().
        self._below_applied = False
        if self._desktop_layer:
            root.after(400, self._apply_below_layer)

        self.frame = tk.Frame(root, bg=BG, highlightthickness=2,
                              highlightbackground=BORDER)
        self.frame.pack(fill="both", expand=True)

        self.l_title = tk.Label(self.frame, text="OURO · SPOT", bg=BG,
                                fg=TITLE, font=("DejaVu Sans", 9, "bold"))
        self.l_title.pack(anchor="w", padx=12, pady=(8, 0))

        row_usd = tk.Frame(self.frame, bg=BG)
        row_usd.pack(anchor="w", padx=12)
        self.l_usd = tk.Label(row_usd, text="—", bg=BG, fg=TXT_USD,
                              font=("DejaVu Sans", 22, "bold"))
        self.l_usd.pack(side="left")
        self.l_usd_var = tk.Label(row_usd, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 10, "bold"))
        self.l_usd_var.pack(side="left", padx=(10, 0), pady=(10, 0))
        self.l_usd_var_week = tk.Label(row_usd, text="", bg=BG, fg=TXT_DIM,
                                       font=("DejaVu Sans", 10, "bold"))
        self.l_usd_var_week.pack(side="left", padx=(8, 0), pady=(10, 0))

        row_brl = tk.Frame(self.frame, bg=BG)
        row_brl.pack(anchor="w", padx=12)
        self.l_brl = tk.Label(row_brl, text="—", bg=BG, fg=TXT_BRL,
                              font=("DejaVu Sans", 13, "bold"))
        self.l_brl.pack(side="left")
        self.l_brl_var = tk.Label(row_brl, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 9, "bold"))
        self.l_brl_var.pack(side="left", padx=(8, 0), pady=(4, 0))
        self.l_brl_var_week = tk.Label(row_brl, text="", bg=BG, fg=TXT_DIM,
                                       font=("DejaVu Sans", 9, "bold"))
        self.l_brl_var_week.pack(side="left", padx=(8, 0), pady=(4, 0))

        self.l_sub = tk.Label(self.frame, text="", bg=BG, fg=TXT_DIM,
                              font=("DejaVu Sans", 8))
        self.l_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # ------------------ seção FUTURO COMEX (v5.6) ---------------------
        self.fut_frame = tk.Frame(self.frame, bg=BG)
        self.fut_frame.pack(anchor="w", padx=12, fill="x")
        lh_fut = tk.Label(self.fut_frame, text="── COMEX · FUTURO (GC=F) ──",
                          bg=BG, fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                          anchor="w")
        lh_fut.grid(row=0, column=0, columnspan=3, sticky="w", pady=(7, 1))
        self.l_fut_name = tk.Label(self.fut_frame, text="—", bg=BG,
                                   fg=TXT_DIM, font=("DejaVu Sans", 8),
                                   anchor="w")
        self.l_fut_price = tk.Label(self.fut_frame, text="", bg=BG,
                                    fg=TXT_USD,
                                    font=("DejaVu Sans", 8, "bold"),
                                    anchor="e")
        self.l_fut_pct = tk.Label(self.fut_frame, text="", bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="e")
        self.l_fut_name.grid(row=1, column=0, sticky="w")
        self.l_fut_price.grid(row=1, column=1, sticky="e", padx=(16, 6))
        self.l_fut_pct.grid(row=1, column=2, sticky="e")
        self.fut_frame.columnconfigure(0, weight=1)
        for w in (lh_fut, self.l_fut_name, self.l_fut_price, self.l_fut_pct):
            self._bind(w)

        # ----------------------- seção CHINA (v5) -------------------------
        self.china_frame = tk.Frame(self.frame, bg=BG)
        self.china_frame.pack(anchor="w", padx=12, fill="x")
        self._china_sig = None
        self._china_refs = []
        self.l_china_sub = tk.Label(self.frame, text="", bg=BG, fg=TXT_DIM,
                                    font=("DejaVu Sans", 7))
        self.l_china_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # --------------- seção EUA · COMBUSTÍVEL (média de varejo) ---------
        self.us_frame = tk.Frame(self.frame, bg=BG)
        self.us_frame.pack(anchor="w", padx=12, fill="x")
        self._us_sig = None
        self._us_refs = []
        self.l_us_sub = tk.Label(self.frame, text="", bg=BG, fg=TXT_DIM,
                                 font=("DejaVu Sans", 7))
        self.l_us_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ----------------------- menu de botão direito ----------------------
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Atualizar agora", command=self.update_now)
        self.menu.add_checkbutton(label="Manter no topo",
                                  variable=self.var_top,
                                  command=self._toggle_top)
        self.menu.add_command(label="Encostar no canto", command=self.snap_corner)
        self.menu.add_separator()
        self.menu.add_command(label="Sair", command=self.quit)

        # ----------------------- arrastar com o mouse ------------------------
        self._drag_off = (0, 0)
        self._user_moved = False
        for w in (root, self.frame, self.l_title, self.l_usd, self.l_usd_var,
                  self.l_usd_var_week, self.l_brl, self.l_brl_var,
                  self.l_brl_var_week, self.l_sub, self.l_china_sub):
            self._bind(w)

        # posição inicial: canto superior direito
        self.snap_corner()

        # mostra último preço conhecido enquanto não chega dado novo
        self._render()

        # thread de atualização em background
        self._poller = threading.Thread(target=self._poll_loop, daemon=True)
        self._poller.start()

        # re-render periódico p/ "atualizado há Ns"
        self._tick()

    def _apply_below_layer(self):
        """Pede ao WM o estado BELOW (camada entre ícones e janelas)."""
        if self._below_applied:
            return
        try:
            if not self.root.winfo_viewable():
                self.root.after(300, self._apply_below_layer)
                return
        except Exception:
            return
        if x11_set_below_state(self.root, add=True):
            self._below_applied = True
            log("camada BOTTOM aplicada (_NET_WM_STATE_BELOW): acima dos "
                "ícones, abaixo das janelas")
        else:
            self.root.after(2000, self._apply_below_layer)

    def _bind(self, w):
        w.bind("<Button-1>",         self._on_press)
        w.bind("<B1-Motion>",        self._on_drag)
        w.bind("<Button-3>",         self._on_menu)
        w.bind("<Double-Button-1>",  lambda e: self.snap_corner())

    # ----------------------------- geometria -------------------------------
    def snap_corner(self):
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        x = self.root.winfo_screenwidth() - w - MARGIN
        y = MARGIN_Y
        self.root.geometry(f"+{x}+{y}")

    def _toggle_top(self):
        on = self.var_top.get()
        if self._desktop_layer:
            # na camada desktop/BOTTOM o WM ignora o topmost; para subir
            # acima das outras janelas volta ao tipo normal (e vice-versa ao
            # desligar). O estado BELOW precisa sair para o topmost valer e
            # voltar quando o topmost é desligado.
            x11_set_below_state(self.root, add=not on)
            self._below_applied = not on
            try:
                self.root.attributes("-type", "normal" if on else "desktop")
            except Exception:
                pass
        self.root.attributes("-topmost", on)

    def _on_press(self, e):
        self._drag_off = (e.x_root - self.root.winfo_x(),
                          e.y_root - self.root.winfo_y())

    def _on_drag(self, e):
        self._user_moved = True
        x = e.x_root - self._drag_off[0]
        y = e.y_root - self._drag_off[1]
        self.root.geometry(f"+{x}+{y}")

    def _on_menu(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    # ----------------------------- dados --------------------------------
    def update_now(self):
        threading.Thread(target=lambda: self._poll_now(), daemon=True).start()

    def _poll_now(self):
        """Refresh manual: se um poll já está rodando, não empilha outro."""
        if self._poll_lock.acquire(blocking=False):
            try:
                self._poll_once_impl()
            finally:
                self._poll_lock.release()

    def _poll_once(self):
        """Serializa polls (um por vez). Retorna retry_after (429) ou None."""
        with self._poll_lock:
            return self._poll_once_impl()

    def _poll_once_impl(self):
        """Retorna retry_after (429) ou None."""
        # baseline diário: busca no boot e na virada do dia (UTC)
        today = datetime.now(timezone.utc).date().isoformat()
        if (not self.baseline or self.baseline.get("day") != today
                or "paxg_week_open" not in self.baseline):
            try:
                self.baseline = fetch_daily_baseline()
            except Exception as e:
                log(f"falha no baseline diário: {e}")

        usd, r1 = try_fetch(SYMBOLS[0])
        brl, r2 = try_fetch(SYMBOLS[1])
        retries = [r for r in (r1, r2) if r is not None]
        retry = max(retries) if retries else None

        # ---- China (v5): todas as fontes, cada uma falha isoladamente ----
        sina_xau = collect_china(self.last)
        fx = self.last.get("fx")

        # ---- Futuro COMEX GC=F (v5.6): falha isolada, mantém cache ----
        try:
            self.last["gc_fut"] = fetch_gc_future()
        except Exception as e:
            log(f"Yahoo GC=F indisponível: {e}")

        # ---- EUA · combustível (média de varejo): falha isolada ----
        try:
            self.last["us_fuel"] = fetch_us_fuel()
        except Exception as e:
            log(f"combustível EUA indisponível ({e}); mantendo cache")
        # combustível: cache vence após 14 dias (2 releases semanais), igual
        # às barras de banco — evita preço velho na tela
        uf = self.last.get("us_fuel")
        if uf and time.time() - uf.get("ts", 0) > FUEL_MAX_AGE:
            self.last.pop("us_fuel", None)
            log("combustível EUA: cache >14 dias sem fonte; removido")

        usd_ok = False
        if usd:
            self.last["usd_price"] = usd["price"]
            self.last["usd_bid"]   = usd["bid"]
            self.last["usd_ask"]   = usd["ask"]
            self.last["usd_src"]   = "goldprice.dev"
            usd_ok = True
        elif sina_xau:  # fallback: spot Londres USD direto da Sina
            self.last["usd_price"] = sina_xau["price"]
            self.last["usd_bid"]   = None
            self.last["usd_ask"]   = None
            self.last["usd_src"]   = "Sina"
            usd_ok = True
            log("goldprice.dev USD falhou; usando Sina hf_XAU")
        else:           # última linha: goldprice.org
            try:
                g = fetch_goldprice_org("USD")
                self.last["usd_price"] = g["price"]
                self.last["usd_bid"]   = None
                self.last["usd_ask"]   = None
                self.last["usd_src"]   = "goldprice.org"
                usd_ok = True
                log("goldprice.dev e Sina falharam; usando goldprice.org")
            except Exception as e:
                log(f"goldprice.org (USD) também falhou: {e}")

        brl_ok = False
        if brl:
            self.last["brl_price"] = brl["price"]
            self.last["brl_src"]   = "goldprice.dev"
            brl_ok = True
        elif usd_ok and _fx_fresh(fx):
            # fallback: BRL derivado do spot USD x câmbio oficial — só com
            # USD deste ciclo e câmbio de até FX_MAX_AGE (nada de dado velho)
            self.last["brl_price"] = self.last["usd_price"] * fx["usdbrl"]
            self.last["brl_src"]   = "derivado USDxBRL"
            brl_ok = True
        else:           # sem spot/câmbio fresco: BRL direto do goldprice.org
            try:
                g = fetch_goldprice_org("BRL")
                self.last["brl_price"] = g["price"]
                self.last["brl_src"]   = "goldprice.org"
                brl_ok = True
                log("sem derivação possível; usando goldprice.org/BRL")
            except Exception as e:
                log(f"goldprice.org (BRL) também falhou: {e}")

        if usd_ok or brl_ok or sina_xau:
            self.last["ts"] = time.time()
        self.last["baseline"] = self.baseline

        # variação diária (vs abertura do dia UTC). Baseline de OUTRO dia
        # (refresh falhou na virada UTC) não pode virar "variação no dia"
        b = self.baseline
        if b and b.get("day") == today and self.last.get("usd_price"):
            g_usd = self.last["usd_price"] / b["paxg_open"] - 1.0
            self.last["usd_day_pct"] = g_usd * 100.0
            self.last["brl_day_pct"] = ((1.0 + g_usd) *
                                        (1.0 + b["fx_day_pct"] / 100.0) - 1.0) * 100.0
            # variação na semana (vs 7 dias atrás)
            pw = b.get("paxg_week_open")
            if pw:
                g_sem = self.last["usd_price"] / pw - 1.0
                self.last["usd_week_pct"] = g_sem * 100.0
                self.last["brl_week_pct"] = ((1.0 + g_sem) *
                                             (1.0 + (b.get("fx_week_pct") or 0.0) / 100.0)
                                             - 1.0) * 100.0

        # indicador separado: spot morto não derruba o status da China,
        # que mostra idade própria ("China há Ns"). Cache é salvo sempre.
        save_cache(self.last)
        self.root.after(0, self._set_spot_offline,
                        not (usd_ok or brl_ok or sina_xau))
        self.root.after(0, self._render)
        return retry

    def _poll_loop(self):
        wait = POLL_SECONDS
        while not self.stop.is_set():
            retry = self._poll_once()
            if retry is not None:
                wait = min(max(retry + 5, 30), 3600)
                log(f"429 na fonte; próxima tentativa em {wait:.0f}s")
            else:
                wait = POLL_SECONDS
            self.stop.wait(wait)

    # ----------------------------- exibição -------------------------------
    def _set_spot_offline(self, off):
        self.spot_offline = off
        self._render()

    def _render(self):
        data = self.last
        if not data or not (data.get("usd_price") or data.get("brl_price")):
            self.l_usd.config(text="—")
            self.l_brl.config(text="—")
            self.l_sub.config(text="sem dados ainda", fg=TXT_DIM)
        else:
            if data.get("usd_price"):
                self.l_usd.config(text=f"US$ {fmt_usd(data['usd_price'])}")
            if data.get("brl_price"):
                self.l_brl.config(text=f"R$ {fmt_brl(data['brl_price'] / TROY_OZ_GRAMS)}/g")

            for lab, lab_sem, key, key_sem in (
                    (self.l_usd_var, self.l_usd_var_week,
                     "usd_day_pct", "usd_week_pct"),
                    (self.l_brl_var, self.l_brl_var_week,
                     "brl_day_pct", "brl_week_pct")):
                p = data.get(key)
                if p is None:
                    lab.config(text="—", fg=TXT_DIM)
                else:
                    lab.config(text=f"{fmt_pct(p)} no dia",
                               fg=UP_COLOR if p >= 0 else DOWN_COLOR)
                s = data.get(key_sem)
                if s is None:
                    lab_sem.config(text="", fg=TXT_DIM)
                else:
                    lab_sem.config(text=f"{fmt_pct(s)} na semana",
                                   fg=UP_COLOR if s >= 0 else DOWN_COLOR)
            self._render_sub()

        # seções Futuro COMEX + China — sempre renderizam, mesmo sem spot
        self._render_fut()
        self._render_china()
        self._render_china_sub()

        # seção EUA · combustível (v5.4 local)
        self._render_us()
        self._render_us_sub()

        # re-encosta no canto com a largura real (a menos que o user arrastou)
        if not self._user_moved:
            self.snap_corner()

    def _render_sub(self):
        data = self.last
        bid, ask = data.get("usd_bid"), data.get("usd_ask")
        sub = (f"bid {fmt_usd(bid) if bid else '—'} · "
               f"ask {fmt_usd(ask) if ask else '—'}")
        ts = data.get("ts")
        if ts:
            age = max(0, int(time.time() - ts))
            sub += f" · há {age}s"
        if self.spot_offline:
            sub += "   · spot offline (cache)"
        src = data.get("usd_src")
        if src and src != "goldprice.dev":
            sub += f" · fonte: {src}"
        self.l_sub.config(text=sub, fg=TXT_DIM)

    # ------------------ exibição · seção FUTURO COMEX (v5.6) --------------
    def _fut_label(self, rec=None):
        """Nome amigável: 'GC=F · dez/26 · contango +64' (+ '(cache)')."""
        rec = rec or {}
        nome = "GC=F"
        parts = (rec.get("name") or "").split()
        if len(parts) >= 3:                      # ex.: "Gold Dec 26"
            mes = MONTH_PT.get(parts[-2], parts[-2].lower())
            nome += f" · {mes}/{parts[-1]}"
        spot = self.last.get("usd_price")
        if rec.get("price") and spot:
            cont = rec["price"] - spot
            nome += f" · contango {cont:+.0f}"
        if rec.get("ts") and time.time() - rec["ts"] > FUT_STALE:
            nome += " · (cache)"
        return nome

    def _render_fut(self):
        r = self.last.get("gc_fut")
        self.l_fut_name.config(text=self._fut_label(r))
        if not r or not r.get("price"):
            self.l_fut_price.config(text="—", fg=TXT_USD)
            self.l_fut_pct.config(text="")
            return
        self.l_fut_price.config(text=f"US$ {fmt_usd(r['price'])}", fg=TXT_USD)
        p = r.get("pct")
        if p is None:
            self.l_fut_pct.config(text="")
        else:
            self.l_fut_pct.config(text=fmt_pct(p),
                                  fg=UP_COLOR if p >= 0 else DOWN_COLOR)

    # --------------------- exibição · seção CHINA (v5) --------------------
    def _china_rows(self):
        """Linhas: ((tipo, texto/nome[, is_usd]), preço_str, pct|None).
        Regras de exibição: grama -> BRL; onça troy -> USD."""
        d = self.last.get("china") or {}
        fx = self.last.get("fx") or {}
        cnybrl = fx.get("cnybrl")
        rows = []

        def brl_g(rec):
            if rec and rec.get("cny_g") is not None and cnybrl:
                return f"R$ {fmt_brl(rec['cny_g'] * cnybrl)}/g"
            return "—"

        bolsa = []
        for key, name in (("sge_au9999", "SGE Au99.99"),
                          ("sge_autd", "SGE Au(T+D)"),
                          ("shfe", "SHFE futuro principal")):
            r = d.get(key)
            if r:
                bolsa.append((("r", name, False), brl_g(r), r.get("pct")))
        if bolsa:
            rows.append((("h", "── CHINA · BOLSAS (SGE/SHFE) ──"), None, None))
            rows.extend(bolsa)

        if d.get("base"):
            rows.append((("h", "── CHINA · REFERÊNCIA ──"), None, None))
            rows.append((("r", "Base China Gold", False), brl_g(d["base"]), None))

        if d.get("banks"):
            rows.append((("h", "── CHINA · BARRAS DE BANCO ──"), None, None))
            for b in d["banks"]:
                rows.append((("r", b["name"], False), brl_g(b), None))

        return rows

    def _render_china(self):
        rows = self._china_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._china_sig:
            for w in self.china_frame.winfo_children():
                w.destroy()
            self._china_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.china_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._china_refs.append(("h", lab))
                else:
                    is_usd = r[0][2]
                    ln = tk.Label(self.china_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8), anchor="w")
                    lp = tk.Label(self.china_frame, text="—", bg=BG, fg=TXT_BRL,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.china_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w)
                    self._china_refs.append(("r", ln, lp, lv, is_usd))
                grid += 1
            self.china_frame.columnconfigure(0, weight=1)
            self._china_sig = sig

        for ref, r in zip(self._china_refs, rows):
            if ref[0] == "h":
                continue
            _, ln, lp, lv, is_usd = ref
            price_str, pct = r[1], r[2]
            lp.config(text=price_str, fg=TXT_USD if is_usd else TXT_BRL)
            if pct is None:
                lv.config(text="")
            else:
                lv.config(text=fmt_pct(pct),
                          fg=UP_COLOR if pct >= 0 else DOWN_COLOR)

    def _render_china_sub(self):
        d = self.last.get("china") or {}
        parts = []
        sge = d.get("sge_au9999") or {}
        if sge.get("dt"):
            try:
                dia, hora = str(sge["dt"]).split(" ")
                parts.append(f"SGE {dia[8:]}{dia[5:8]} {hora[:5]} Pequim")
            except Exception:
                pass
        ts = d.get("ts_last_ok")
        if ts:
            age = max(0, int(time.time() - ts))
            parts.append(f"China há {age}s")
        self.l_china_sub.config(text=" · ".join(parts), fg=TXT_DIM)

    # ----------------- exibição · seção EUA · COMBUSTÍVEL (local) ---------
    def _us_rows(self):
        d = self.last.get("us_fuel") or {}
        rows = []
        if d.get("gas") or d.get("diesel"):
            rows.append((("h", "── EUA · COMBUSTÍVEL (MÉDIA VAREJO) ──"),
                         None, None))
            if d.get("gas"):
                rows.append((("r", "Gasolina (regular)", True),
                             f"US$ {d['gas']:,.3f}/gal",
                             _chg_pct(d.get("gas"), d.get("gas_chg"))))
            if d.get("diesel"):
                rows.append((("r", "Diesel (on-highway)", True),
                             f"US$ {d['diesel']:,.3f}/gal",
                             _chg_pct(d.get("diesel"), d.get("diesel_chg"))))
        return rows

    def _render_us(self):
        rows = self._us_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._us_sig:
            for w in self.us_frame.winfo_children():
                w.destroy()
            self._us_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.us_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._us_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.us_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.us_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.us_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w)
                    self._us_refs.append(("r", ln, lp, lv))
                grid += 1
            self.us_frame.columnconfigure(0, weight=1)
            self._us_sig = sig

        for ref, r in zip(self._us_refs, rows):
            if ref[0] == "h":
                continue
            _, lp, lv = ref[1], ref[2], ref[3]
            price_str, pct = r[1], r[2]
            lp.config(text=price_str, fg=TXT_USD)
            if pct is None:
                lv.config(text="")
            else:
                lv.config(text=fmt_pct(pct),
                          fg=UP_COLOR if pct >= 0 else DOWN_COLOR)

    def _render_us_sub(self):
        d = self.last.get("us_fuel") or {}
        parts = []
        if d.get("week"):
            parts.append(f"semana {d['week']} · {d.get('src', 'EIA')}")
        ts = d.get("ts")
        if ts:
            age = max(0, int(time.time() - ts))
            parts.append(f"atualizado há {age}s")
        self.l_us_sub.config(text=" · ".join(parts), fg=TXT_DIM)

    def _tick(self):
        if self.stop.is_set():
            return
        self._render_sub()
        self._render_fut()          # reavalia idade/cache do GC=F
        self._render_china_sub()
        self._render_us_sub()
        self.root.after(5000, self._tick)

    # ----------------------------- saída --------------------------------
    def quit(self):
        self.stop.set()
        self.root.destroy()

# ------------------------------- DUMP ------------------------------------
def dump():
    """Modo sem interface: busca tudo e imprime já normalizado
    (grama -> BRL; onça troy -> USD)."""
    last = {}
    fx = None
    try:
        fx = fetch_fx()
        last["fx"] = fx
        print(f"FX [{fx['src']}]: USDBRL {fx['usdbrl']:.4f} · "
              f"CNYBRL {fx['cnybrl']:.4f} · USDCNY {fx['usdcny']:.4f}")
    except Exception as e:
        print(f"FX (3 fontes): FALHOU ({e})")
    for sym in SYMBOLS:
        try:
            p = fetch_price(sym)
            print(f"goldprice.dev {sym}: {p['price']:,.2f} "
                  f"(bid {p['bid']} · ask {p['ask']})")
        except Exception as e:
            print(f"goldprice.dev {sym}: FALHOU ({e})")

    sina_xau = collect_china(last)
    if sina_xau:
        pct = (f" ({sina_xau['pct']:+.2f}% no dia)"
               if sina_xau.get("pct") is not None else "")
        print(f"Sina hf_XAU (spot Londres USD): {sina_xau['price']:,.2f}{pct}")

    try:
        g = fetch_gc_future()
        print(f"Yahoo GC=F ({g['name']}) futuro COMEX: {g['price']:,.2f} "
              f"(fech. ant. {g['prev_close']:,.2f} · {g['pct']:+.2f}%)")
    except Exception as e:
        print(f"Yahoo GC=F: FALHOU ({e})")

    try:
        f = fetch_us_fuel()
        last["us_fuel"] = f
        precos = []
        if f.get("gas"):
            precos.append(f"gasolina {f['gas']:.3f} US$/gal")
        if f.get("diesel"):
            precos.append(f"diesel {f['diesel']:.3f} US$/gal")
        chgs = []
        for fuel, chg in (("gasolina", f.get("gas_chg")),
                          ("diesel", f.get("diesel_chg"))):
            if chg is not None:
                chgs.append(f"{fuel} {chg:+.3f}")
        chg_s = f" (Δ semana: {', '.join(chgs)})" if chgs else ""
        print(f"US FUEL [{f.get('src', 'EIA')}]: "
              f"{' · '.join(precos)} (semana {f.get('week')}){chg_s}")
    except Exception as e:
        print(f"US FUEL: FALHOU ({e})")

    d = last.get("china") or {}
    cnybrl = (fx or {}).get("cnybrl")
    print("\nCHINA — normalizado (grama->BRL · onça->USD):")

    def line(name, rec, unit="g"):
        if not rec or cnybrl is None:
            print(f"  {name:34s} — sem dados")
            return
        pct = f"{rec['pct']:+.2f}%" if rec.get("pct") is not None else ""
        meta = rec.get("src") or ""
        if rec.get("dt"):
            meta += f" {rec['dt']}"
        print(f"  {name:34s} {rec['cny_g']:>9.2f} CNY/{unit} -> "
              f"R$ {rec['cny_g'] * cnybrl:>10.2f}/{unit}  {pct:8s} {meta}")

    line("SGE Au99.99", d.get("sge_au9999"))
    line("SGE Au(T+D)", d.get("sge_autd"))
    line("SHFE futuro principal", d.get("shfe"))
    line("Base China Gold", d.get("base"))
    for b in d.get("banks") or []:
        line(f"Barra {b['name']}", b)
    return 0

# ------------------------------- MAIN ------------------------------------
def main():
    if "--dump" in sys.argv:
        log("modo --dump (sem interface)")
        return dump()

    if tk is None:
        log("tkinter indisponível")
        print("Erro: tkinter não disponível neste sistema.", file=sys.stderr)
        return 1

    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("Sem display gráfico (DISPLAY não definido).", file=sys.stderr)
        return 1

    log("iniciando widget (v5.6: fallbacks totais + combustível EUA + "
        "futuro COMEX GC=F)")
    root = tk.Tk()
    GoldWidget(root)
    root.mainloop()
    log("widget encerrado")
    return 0

if __name__ == "__main__":
    sys.exit(main())
