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
v5.7:
   * NOVO — seção "BRASIL · RISCO SOBERANO": CDS soberano de 5 anos do
     Brasil em bps, com variação de 1 semana e probabilidade de default
     implícita (hipótese de 40% de recuperação). Fonte grátis sem chave:
     worldgovernmentbonds.com — POST JSON no REST interno deles
     (wp-json/country/v1/main), exigindo header Origin no host www (o
     apex está com o certificado SSL vencido desde out/2024; usar SEMPRE
     www). Cadeia: payload embutido no código -> se falhar, extrai o
     payload fresco da página do país e repete. Dado lento (e resposta
     de ~100 KB): refetch a cada 15 min; cache vence após 7 dias.
v5.8:
   * NOVO — fallback do CDS Brasil (antes WGB era fonte única). Cadeia:
     WGB (intraday) -> Investing.com SSR (EOD, delayed ~1 dia) -> cache 7d.
     O Investing expõe o BRGV5YUSAC=R como JSON embutido no __NEXT_DATA__
     da página do instrumento (urllib puro, sem chave). Check no
     lastUpdateTime (epoch ms): cotação mais velha que 4 dias = feed
     congelado -> é rejeitada e NÃO renova o cache (que vence em 7d).
     Pegadinha: o lastClose do SSR vem corrompido (190.23 com last
     121.08); fechamento anterior real = last - change. PD implícita
     calculada com a mesma fórmula do WGB (1 - exp(-s/(1-R)), rec. 40% —
      confere com o lastCdsDefaultProb deles, horizonte 1 ano).
 v5.9 (ALTERAÇÃO LOCAL — não enviada ao repositório):
    * TROCA da fonte do combustível EUA: sai a EIA SEMANAL com toda a
      cadeia (AmericasOilWatch -> dnav -> FRED -> API v2), entra a AAA
      Fuel Prices (gasprices.aaa.com) — média nacional DIÁRIA de varejo,
      gasolina regular e diesel, US$/gal. Motivo: a EIA só publica
      1x/semana (a API v2 não tem frequência diária de varejo —
      confirmado nos metadados) e o usuário quer o dado do dia. A AAA
      atualiza todo dia ("updated daily"; rede de postos OPIS/WEX).
      Sem chave: scrape da tabela nacional (table-mob) com urllib puro,
      mesmo padrão dos scrapes dnav/Investing já existentes. Variação
      exibida = vs ontem (linhas Current/Yesterday da tabela). Dado
      diário não muda no ciclo de 90 s: refetch no máx. 1/h
      (FUEL_REFETCH); cache vence após 14 dias (FUEL_MAX_AGE, inalterado).
 v4: BRL por grama; camada desktop; polling 90 s; backoff 429; baseline PAXG.
 v6.0:
    * NOVO — clique num valor abre um popup com o grafico do ativo no periodo
      escolhido (7D/1M/3M/6M/1A, conforme a fonte): spot USD/BRL (PAXG),
      COMEX GC=F (Yahoo), SGE/SHFE (SGE oficial/Eastmoney), base China Gold
      (derivada), barras (proxy SGE), combustiveis EUA (FRED), CDS 5 anos
      (Investing, 7D/1M). Clique simples abre; arrastar continua movendo;
      duplo-clique encosta no canto. Cursor de "mao" marca o que e clicavel.
      Menu botao-direito ganhou "Ver grafico". Sem dependencia nova: Canvas
      puro + urllib. Fallback: log local acumulado (~/.local/share/...).
 v6.1 (ESTA VERSAO):
    * NOVO — secao "NYMEX · DIESEL (HO=F)": futuro ULSD/heating oil (o
      benchmark do diesel da foto do TradingView HO1!), USD/gal, cotacao
      intraday do front-month com var. vs fechamento anterior. Alem do preco
      por galao, mostra o equivalente US$/barril (x42 — a escala em que o
      grafico da foto cotava: 210 = US$ 5.00/gal).
    * Cadeia de fallback:
        - Yahoo HO=F (chart API, como o GC=F)     [principal]
        - FXEmpire /commodities/ho (blob JSON do
          react-query no SSR; vendor Oanda; traz
          last/change/prevClose/lastUpdate/OI e
          futuresMonth p/ o rotulo do contrato)   [fallback 1]
        - Trading Economics (scrape market_last)  [fallback 2; referencia]
        - cache local, com etiqueta "(cache)" apos
          FUT_STALE (10 min) e expiracao em 4 dias
          (cobre o fim de semana sem pregao).
     * Refetch a cada HO_REFETCH (5 min; 2 futuros no mesmo IP do Yahoo nao
       pode virar martelada). Grafico historico: Yahoo HO=F (7D-1A) com
       fallback no log local. Falha isolada das demais secoes.
 v6.2 (ESTA VERSAO):
    * NOVO — secao "RUSSIA · CRUDE URALS": preco do Urals (blend de
      exportacao russo, FOB NW Europe/Primorsk), US$/barril com variacao
      do dia. Dado NAO existe em bolsa regular (Yahoo/FRED/Investing/TE
      nao tem serie de spot do Urals — verificado), e o spot vem de
      avaliacoes com 1-2 dias de atraso. Fontes gratis sem chave:
        - OilPrice.com oil-price-charts: tabela com a linha do Urals
          (data-name 'Urals-Brent'; GET puro, mesmo padrao dos scrapes
          AAA/dnav/Investing ja existentes)           [principal]
        - OilPrice.com /freewidgets/json_get_oilprices: POST JSON que o
          proprio grafico do blend usa (CSRF via /ajax/csrf; o POST
          exige header X-Requested-With, senao volta HTML) [fallback 1]
        - cache local, etiqueta "(cache)" e expiracao em 7 dias.
    * Refetch no max. 1/h (dado tem atraso de 1-2 dias; martelada nao
      adianta). Grafico historico (7D/1M/3M/6M/1A): series do mesmo
      endpoint freewidgets (periodos 4=1M, 6=3M, 5=1A), com fallback no
      log local. Falha isolada das demais secoes.
 v6.3 (ESTA VERSAO):
     * NOVO — secao "BRENT · CRUDE (BENCHMARK)": o benchmark global do
       petroleo (mar do Norte; precifica ~2/3 do crude mundial),
       US$/barril com variacao do dia. Cadeia:
         - Yahoo BZ=F (chart API, intraday do front-month; mesmo
           pipeline do GC=F/HO=F)                       [principal]
         - FXEmpire /commodities/brent-crude-oil (blob JSON do
           react-query no SSR; vendor Oanda — CFD BCO/USD realtime;
           last/change/percentChange/previousClose/high/low/
           lastUpdate; marker unico "vendorSymbol":"BCO/USD", blob
           DIFERENTE do do HO)                          [fallback 1]
         - OilPrice.com oil-price-charts, linha data-name
           'Brent-Crude' (data-id 46; avaliacao c/ ~11 min de atraso)
                                                        [fallback 2]
         - OilPrice.com /freewidgets/json_get_oilprices (blend_id=46;
           CSRF + X-Requested-With, como no Urals)       [fallback 3]
         - cache local, etiqueta "(cache)" apos FUT_STALE (10 min) e
           expiracao em 4 dias (cobre o fim de semana).
     * NOVO — backoff por SECAO (offline / 429): cadeia morta nao vira
       martelada. Cada secao com refetch proprio (GC=F, combustivel,
       CDS, HO=F, Urals, Brent) ganha um cooldown que dobra a cada
       falha consecutiva da cadeia (teto 30 min); "429" em qualquer
       degrau da cadeia conta como falha dupla. Sucesso zera o estado.
       A tabela do OilPrice.com (serve Urals E Brent) agora tem cache
       de 2 min p/ nao duplicar request entre as duas secoes.
     * GC=F (v5.6) ganha cadeia de fallback: Yahoo chart ->
       Trading Economics (scrape SSR, comma-tolerante) -> cache.
     * Grafico historico: Yahoo BZ=F (7D-1A), fallback no log local.
       Falha isolada das demais secoes.
 v6.4 PERFEITA (ESTA VERSAO — correcao dos 429 do GC=F):
     * GC=F vira cadeia de 6 fontes + cache: Yahoo-q1 -> Yahoo-q2 ->
       FXEmpire ouro (/commodities/gold, CFD Oanda) -> TradingEconomics ->
       goldprice.org (spot proxy) -> Sina hf_XAU (spot proxy) -> cache 4d.
       Qualquer degrau vivo salva o preco; UI mostra a fonte
       (Yahoo/FXE/TE/GPorg/Sina) e "(cache)" apos 10min.
     * Backoff POR FONTE: cada fonte tem cooldown proprio (429 = falha
       dupla + jitter). Fallback que salva NAO anistia a primaria morta —
       era esse o bug que martelava o Yahoo banido a cada 90s e eternizava
       o 429. Cadeia toda morta ainda ganha cooldown da secao (teto 30min).
     * GC_REFETCH 90s -> 5min (igual HO/Brent; 3x menos pressao no Yahoo),
       throttle 1,5s entre calls Yahoo, tentativa automatica query2 em 429,
       log com lock thread-safe, jitter no poller, GC expira em 4d como
       HO/Brent, HO/Brent ganham Yahoo-q2 + mesmo backoff por fonte.
v6.5 (2026-09-17, a pedido do usuário):
    * REMOVIDO — seção "COMEX · FUTURO (GC=F)" e TODA a seção CHINA
      (BOLSAS SGE/SHFE, REFERÊNCIA Base China Gold, BARRAS DE BANCO).
      Buscas desativadas: Sina, Eastmoney, jijinhao, xxapi e cadeia Yahoo-GC.
      Mantidos: spot USD/BRL, combustível EUA, CDS, HO=F, Brent, Urals.
      Spot agora usa goldprice.dev -> goldprice.org (sem fallback Sina).
Fonte principal do spot: goldprice.dev. Stdlib apenas (tkinter+urllib).
"""

import json
import math
import os
import re
import sys
import threading
import time
import random
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
YAHOO_GC_URL_Q2 = ("https://query2.finance.yahoo.com/v8/finance/chart/GC=F"
                 "?interval=1d&range=5d")            # host reserva (mesma API)
YAHOO_HO_URL_Q2 = ("https://query2.finance.yahoo.com/v8/finance/chart/HO=F"
                 "?interval=1d&range=5d")
YAHOO_BZ_URL_Q2 = ("https://query2.finance.yahoo.com/v8/finance/chart/BZ=F"
                 "?interval=1d&range=5d")
FXE_GOLD_URL  = "https://www.fxempire.com/commodities/gold"
GC_REFETCH    = 5 * 60                               # v6.4: intraday mas sem martelar (era 90s -> 429)
GC_MAX_AGE    = 4 * 86400                            # v6.4: cache expira em 4d como HO/Brent
FUT_STALE     = 10 * 60                              # acima disso mostra "(cache)"
MONTH_PT      = {"Jan": "jan", "Feb": "fev", "Mar": "mar", "Apr": "abr",
                 "May": "mai", "Jun": "jun", "Jul": "jul", "Aug": "ago",
                 "Sep": "set", "Oct": "out", "Nov": "nov", "Dec": "dez"}

# ----------------- CONFIG · COMBUSTÍVEL EUA (varejo, DIÁRIO) ---------------
# v5.9 — fonte única: AAA Fuel Prices (gasprices.aaa.com), a média nacional
# DIÁRIA de varejo (gasolina regular e diesel, US$/gal com impostos) que a
# AAA atualiza todo dia ("updated daily"; rede de postos OPIS/WEX).
# Substitui a EIA semanal (v5.4-v5.8): a EIA só publica 1x/semana e os
# metadados da API v2 confirmam que NÃO existe série diária de varejo.
# Sem chave: scrape da tabela nacional (table-mob) com urllib puro, no
# mesmo padrão dos scrapes dnav/Investing. O dado é diário, então o
# refetch passa a ser no máx. 1x/hora (não a cada ciclo de 90 s).
AAA_FUEL_URL   = "https://gasprices.aaa.com/"
FUEL_REFETCH   = 3600                # dado diário: refetch no máx. 1/h
FUEL_MAX_AGE   = 14 * 86400          # cache vence (14 dias sem fonte)

# ---------------- CONFIG · CDS 5 ANOS BRASIL (risco soberano) ---------------
# CDS soberano de 5 anos do Brasil, em bps (termômetro de risco-país).
# Dado OTC: não há ticker em bolsa regular (Yahoo/FRED não têm; BCB não
# publica). Fontes grátis sem chave:
#   - worldgovernmentbonds.com — POST JSON no REST interno (WordPress);
#     o endpoint exige header Origin no host WWW (apex com SSL vencido).
#   - Investing.com (v5.8, fallback) — BRGV5YUSAC=R, JSON embutido no
#     __NEXT_DATA__ da página do instrumento (urllib puro). Curiosidade:
#     o rodapé do próprio WGB cita Investing/TradingEconomics como
#     créditos — pipeline diferente, mas upstream em comum.
WGB_POST_URL  = "https://www.worldgovernmentbonds.com/wp-json/country/v1/main"
WGB_PAGE_URL  = "https://www.worldgovernmentbonds.com/country/brazil/"
WGB_HEADERS   = {"Origin": "https://www.worldgovernmentbonds.com",
                 "Referer": WGB_PAGE_URL,
                 "Accept": "application/json"}
WGB_PAYLOAD   = {                       # capturado da página do país (estável)
    "JS_VARIABLE": "jsGlobalVars",
    "FUNCTION": "Country",
    "DOMESTIC": True,
    "ENDPOINT": "https://www.worldgovernmentbonds.com/wp-json/country/v1/historical",
    "DATE_RIF": "2099-12-31",
    "OBJ": None,
    "COUNTRY1": {"SYMBOL": "7", "PAESE": "Brazil",
                 "PAESE_UPPERCASE": "BRAZIL", "BANDIERA": "br",
                 "URL_PAGE": "brazil"},
    "COUNTRY2": None, "OBJ1": None, "OBJ2": None,
}
CDS_POLL_SECONDS = 15 * 60              # refetch (dado lento, resposta ~100 KB)
CDS_MAX_AGE      = 7 * 86400            # cache vence (7 dias sem fonte)

# v5.8 — fallback do CDS: Investing.com (SSR da página do instrumento).
# EOD (isDelayed): mostra o fechamento do dia anterior, por isso o check
# no lastUpdateTime — mais velho que CDS_INV_MAX_AGE = feed congelado.
INV_CDS_URL      = "https://www.investing.com/rates-bonds/brazil-cds-5-years-usd"
CDS_INV_MAX_AGE  = 4 * 86400            # EOD (~1 dia) + folga p/ fds (sex->seg ~3d)

# ---------------- CONFIG · NYMEX DIESEL HO=F (futuro ULSD, v6.1) -------------
# Futuro ULSD (heating oil) da NYMEX — o benchmark do diesel (proxy do HO1!
# do TradingView; no gráfico da foto cotava em US$/barril: 210 = US$ 5/gal).
# Cadeia (Yahoo -> FXEmpire -> Trading Economics -> cache):
#   - Yahoo: mesma chart API do GC=F, intraday do front-month (HO=F).
#   - FXEmpire: blob JSON do react-query no SSR da página /commodities/ho
#     (vendor Oanda; traz last/change/percentChange/previousClose/lastUpdate/
#     openInterest/high/low + futuresMonth p/ o rótulo do contrato).
#   - Trading Economics: scrape do SSR (market_last + market_daily_Pchg),
#     referência CFD do front-month — só como 3ª opção (atrasa/intraday lento).
YAHOO_HO_URL  = ("https://query1.finance.yahoo.com/v8/finance/chart/HO=F"
                 "?interval=1d&range=5d")   # 5 barras: atual + anteriores
FXE_HO_URL    = "https://www.fxempire.com/commodities/ho"
TE_HO_URL     = "https://tradingeconomics.com/commodity/heating-oil"
TE_GC_URL     = "https://tradingeconomics.com/commodity/gold"
HO_REFETCH    = 5 * 60               # dado intraday; refetch no máx. 1/5min
HO_MAX_AGE    = 4 * 86400            # cache vence (4 dias; cobre fim de semana)

# -------------- CONFIG · CRUDE URALS (Rússia, v6.2) --------------------------
# Urals = blend de exportação da Rússia (FOB NW Europe/Primorsk). NÃO é
# cotado em bolsa regular: Yahoo/FRED/Investing/TradingEconomics não têm
# série de spot (testado) — o valor vem de avaliações com 1-2 dias de
# atraso. Fontes grátis sem chave:
#   - OilPrice.com oil-price-charts: tabela com dezenas de blends; a
#     linha do Urals (data-name 'Urals-Brent') traz preço, Δ, Δ%,
#     timestamp e o texto do atraso. GET puro, sem chave.
#   - OilPrice.com /freewidgets/json_get_oilprices: POST JSON usado pelo
#     próprio gráfico do blend (CSRF de /ajax/csrf; o POST exige header
#     X-Requested-With, senão responde HTML). É também a fonte das
#     séries históricas (períodos: 4=1M, 6=3M, 5=1A, 7=5A).
OILPRICE_CHARTS_URL = "https://oilprice.com/oil-price-charts/"
OILPRICE_CSRF_URL   = "https://oilprice.com/ajax/csrf"
OILPRICE_JSON_URL   = "https://oilprice.com/freewidgets/json_get_oilprices"
URALS_BLEND_ID      = "4466"
URALS_REFETCH       = 3600              # dado atrasado 1-2 dias: refetch 1/h
URALS_MAX_AGE       = 7 * 86400         # cache vence (7 dias sem fonte)
OILPRICE_PAGE_TTL   = 120               # tabela serve Urals E Brent: cache 2min

# ------------------- CONFIG · BRENT (benchmark global, v6.3) -----------------
# Brent = benchmark do petroleo (mar do Norte). Nao é spot em bolsa
# comum: o intraday é o front-month do futuro (BZ=F/ICE), e o "spot" de
# referência vem de avaliacoes (OilPrice.com, ~11 min de atraso).
# Cadeia (Yahoo -> FXEmpire -> OilPrice tabela -> OilPrice JSON -> cache):
#   - Yahoo: chart API do continuo BZ=F, igual GC=F/HO=F.
#   - FXEmpire: /commodities/brent-crude-oil — blob do react-query com o
#     quote do CFD BCO/USD (Oanda, realtime); marker "vendorSymbol":
#     "BCO/USD" (unico na pagina; blob rates, diferente do do HO).
#   - OilPrice.com tabela: linha data-name='Brent-Crude' (data-id 46).
#   - OilPrice.com freewidgets: POST JSON do proprio grafico do blend
#     (CSRF de /ajax/csrf; header X-Requested-With obrigatorio).
YAHOO_BZ_URL  = ("https://query1.finance.yahoo.com/v8/finance/chart/BZ=F"
                 "?interval=1d&range=5d")   # 5 barras: atual + anteriores
FXE_BRENT_URL = "https://www.fxempire.com/commodities/brent-crude-oil"
BRENT_BLEND_ID = "46"
BRENT_REFETCH  = 5 * 60               # intraday: refetch no máx. 1/5min
BRENT_MAX_AGE  = 4 * 86400            # cache vence (4 dias; cobre fim de semana)

# Tradução dos nomes em chinês vindos da xxapi (fonte CJK não é necessária)
BANK_TR = {
    "工商银行如意金条": "ICBC Ruyi",
    "中国银行金条":     "Banco da China",
    "建设银行龙鼎金条": "CCB Longding",
    "农行传世之宝金条": "ABC Chuanshibao",
    "浦发银行投资金条": "SPD Invest.",
    "和谐平安金条":     "Ping An",
}

# -------------------- HISTORICO P/ GRAFICOS (v6.0) --------------------
# Clique num valor abre um popup com o grafico do ativo no periodo
# escolhido (7D/1M/3M/6M/1A). Tudo gratis, sem chave, so stdlib:
#   spot USD/BRL : PAXG (Binance->OKX) [+ USDBRL p/ o BRL]
#   COMEX GC=F   : Yahoo chart (range conforme o periodo)
#   SGE          : oficial SGE Dailyhq (desde 2016); fallback Eastmoney
#   SHFE         : Eastmoney kline (113.aum)
#   base CN      : PAXG x USDCNY/oz (derivada, padrao do widget)
#   barras       : proxy SGE Au99.99 (mesmo mercado; sem serie propria)
#   gasolina     : FRED GASREGW (semanal); diesel tenta series FRED
#   CDS 5Y       : Investing (SSR da pagina historical-data, ~1 mes)
# Sem serie remota (ou se ela falhar): usa o log local acumulado.
HIST_CACHE_TTL = 600
HIST_FILE      = os.path.join(STATE_DIR, "history.json")
SGE_DAILYHQ_URL = "https://www.sge.com.cn/graph/Dailyhq"
EM_KLINE_FMT    = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
                   "?secid={secid}&fields1=f1,f2,f3,f4,f5"
                   "&fields2=f51,f52,f53,f54,f55,f56,f57"
                   "&klt=101&fqt=0&beg={beg}&end={end}")
INV_CDS_HIST_URL = ("https://www.investing.com/rates-bonds/"
                    "brazil-cds-5-years-usd-historical-data")
FRED_CSV_FMT    = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
DIESEL_FRED_IDS = ("GASDESW", "DIESEL", "DD1NUS_DPG")


def _hist_date(ts):
    return datetime.fromtimestamp(float(ts), timezone.utc).strftime("%Y-%m-%d")


def _hist_paxg(days):
    lim = min(max(int(days) + 5, 8), 1000)
    errs = []
    try:
        k = _get_json("https://api.binance.com/api/v3/klines"
                      f"?symbol=PAXGUSDT&interval=1d&limit={lim}")
        pts = []
        for r in k:
            try:
                pts.append((_hist_date(r[0] / 1000.0), float(r[4])))
            except Exception:
                continue
        if len(pts) >= 2:
            return pts[-int(days):] if len(pts) > days else pts, "Binance PAXG"
        errs.append("binance: poucos pontos")
    except Exception as e:
        errs.append(f"binance: {e}")
    try:
        rows = (_get_json("https://www.okx.com/api/v5/market/candles"
                          f"?instId=PAXG-USDT&bar=1Dutc&limit={lim}").get("data")
                or [])
        pts = []
        for r in sorted(rows, key=lambda r: int(r[0])):
            try:
                pts.append((_hist_date(int(r[0]) / 1000.0), float(r[4])))
            except Exception:
                continue
        if len(pts) >= 2:
            return pts[-int(days):] if len(pts) > days else pts, "OKX PAXG"
        errs.append("okx: poucos pontos")
    except Exception as e:
        errs.append(f"okx: {e}")
    raise RuntimeError("PAXG sem serie (" + "; ".join(errs) + ")")


def _hist_yahoo(sym, days):
    days = int(days)
    rng = ("1mo" if days <= 31 else "3mo" if days <= 93
           else "6mo" if days <= 186 else "1y" if days <= 370
           else "2y" if days <= 730 else "5y")
    d = _get_json("https://query1.finance.yahoo.com/v8/finance/chart/"
                  f"{urllib.parse.quote(sym)}?interval=1d&range={rng}",
                  {"User-Agent": BROWSER_UA})
    res = ((d.get("chart") or {}).get("result") or [])
    if not res:
        raise ValueError(f"Yahoo {sym} sem resultado")
    ts = res[0].get("timestamp") or []
    quote = (((res[0].get("indicators") or {}).get("quote")) or [{}])[0]
    closes = quote.get("close") or []
    pts = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        try:
            pts.append((_hist_date(t), float(c)))
        except Exception:
            continue
    if len(pts) < 2:
        raise ValueError(f"Yahoo {sym} sem serie")
    return pts[-days:] if len(pts) > days else pts, f"Yahoo {sym}"


def _hist_fx(pair, days):
    n = min(max(int(days) + 10, 8), 360)
    hist = _get_json(f"https://economia.awesomeapi.com.br/json/daily/{pair}/{n}")
    pts = []
    for r in sorted(hist, key=lambda r: int(r.get("timestamp") or 0)):
        try:
            pts.append((_hist_date(int(r["timestamp"])), float(r["bid"])))
        except Exception:
            continue
    if len(pts) < 2:
        raise ValueError(f"FX {pair} sem serie")
    days = int(days)
    return pts[-days:] if len(pts) > days else pts, f"awesomeapi {pair}"


def _hist_sge(instid, days):
    data = ("instid=" + urllib.parse.quote(instid)).encode()
    req = urllib.request.Request(
        SGE_DAILYHQ_URL, data=data,
        headers={"User-Agent": "gold-widget/6.0",
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=NET_TIMEOUT + 7) as r:
        d = json.loads(r.read().decode("utf-8"))
    rows = d.get("time") or []
    pts = []
    for row in rows:
        try:
            pts.append((str(row[0]), float(row[2])))
        except Exception:
            continue
    if len(pts) < 2:
        raise ValueError(f"SGE {instid} sem serie")
    days = int(days)
    return pts[-days:] if len(pts) > days else pts, f"SGE {instid}"


def _hist_em(secid, days):
    days = int(days)
    end = datetime.now(timezone.utc).date()
    beg = end - timedelta(days=days * 2 + 10)
    url = EM_KLINE_FMT.format(secid=secid, beg=beg.strftime("%Y%m%d"),
                              end=end.strftime("%Y%m%d"))
    d = _get_json(url)
    kl = ((d.get("data") or {}).get("klines")) or []
    pts = []
    for line in kl:
        p = line.split(",")
        if len(p) < 3:
            continue
        try:
            pts.append((p[0], float(p[2])))
        except Exception:
            continue
    if len(pts) < 2:
        raise ValueError(f"Eastmoney {secid} sem serie")
    return pts[-days:] if len(pts) > days else pts, f"Eastmoney {secid}"


def _hist_fred(sids, days):
    days = int(days)
    errs = []
    for sid in sids:
        try:
            raw = _http_get(FRED_CSV_FMT.format(sid=sid),
                            {"User-Agent": BROWSER_UA},
                            timeout=25).decode("utf-8", "replace")
            pts = []
            for ln in raw.splitlines()[1:]:
                ln = ln.strip()
                if not ln or "," not in ln:
                    continue
                dt, val = ln.split(",", 1)
                val = val.strip()
                if not val or val == ".":
                    continue
                try:
                    pts.append((dt.strip(), float(val)))
                except Exception:
                    continue
            if len(pts) >= 5:
                return pts[-days:] if len(pts) > days else pts, f"FRED {sid}"
            errs.append(f"{sid}: so {len(pts)} pts")
        except Exception as e:
            errs.append(f"{sid}: {e}")
    raise RuntimeError("FRED sem serie (" + "; ".join(errs) + ")")


def _hist_cds(days):
    html = _http_get(
        INV_CDS_HIST_URL,
        {"User-Agent": BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"},
        timeout=20).decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("SSR sem __NEXT_DATA__")
    data = json.loads(m.group(1))
    rows = (data.get("props", {}).get("pageProps", {}).get("state", {})
            .get("historicalDataStore", {}).get("historicalData", {})
            .get("data")) or []
    pts = []
    for r in rows:
        try:
            dt = str(r.get("rowDateTimestamp") or "")[:10]
            raw = (r.get("last_closeRaw")
                   if r.get("last_closeRaw") is not None else r.get("last_close"))
            v = float(raw)
            if v > 0 and len(dt) == 10:
                pts.append((dt, v))
        except Exception:
            continue
    pts.sort()
    if len(pts) < 2:
        raise ValueError("SSR sem serie")
    days = int(days)
    return pts[-days:] if len(pts) > days else pts, "Investing.com"


def _hist_urals(days):
    """Série histórica do Urals no endpoint JSON do OilPrice.com.
    Períodos do blend: 4=1M (~20 pts), 6=3M (~61), 5=1A (~251).
    Pontos vêm em epoch; normaliza p/ data UTC deduplicada."""
    days = int(days)
    if days <= 40:
        period = 4
    elif days <= 120:
        period = 6
    else:
        period = 5
    pts, _lc, _u = _oilprice_json_period(URALS_BLEND_ID, period)
    by = {}
    for t, v in pts:
        try:
            if v > 0:
                by[datetime.fromtimestamp(t, timezone.utc)
                   .strftime("%Y-%m-%d")] = v
        except Exception:
            continue
    ser = sorted(by.items())
    if len(ser) < 2:
        raise ValueError("OilPrice Urals sem serie")
    return ser[-days:] if len(ser) > days else ser, "OilPrice.com"


def _hist_join(dates_vals, fx_by_date):
    items = sorted(fx_by_date.items())
    out = []
    for dt, v in dates_vals:
        f = fx_by_date.get(dt)
        if f is None:
            prev = None
            for d2, v2 in items:
                if d2 <= dt:
                    prev = v2
                else:
                    break
            f = prev
        if f:
            out.append((dt, v * f))
    return out


def load_hist_log():
    try:
        with open(HIST_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_hist_log(store):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = HIST_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(store, f)
        os.replace(tmp, HIST_FILE)
    except Exception:
        pass


def log_hist_point(store, key, val, cap=2000):
    if val is None:
        return
    try:
        v = float(val)
    except Exception:
        return
    if not v > 0:
        return
    lst = store.setdefault(key, [])
    ts = time.time()
    if lst and ts - lst[-1][0] < 3600:
        try:
            if abs(float(lst[-1][1]) - v) < 1e-9:
                return
        except Exception:
            pass
    lst.append([ts, v])
    if len(lst) > cap:
        del lst[:len(lst) - cap]


def hist_log_series(store, key, days):
    cut = time.time() - int(days) * 86400
    by = {}
    for t, v in (store.get(key) or []):
        try:
            if float(t) >= cut:
                by[datetime.fromtimestamp(float(t), timezone.utc)
                   .strftime("%Y-%m-%d")] = float(v)
        except Exception:
            continue
    return sorted(by.items())


HIST_META = {
    "spot_usd":   {"title": "Ouro · Spot (USD/oz)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}",
                   "yfmt": lambda v: f"{v:,.0f}",
                   "ranges": (7, 30, 90, 180, 365)},
    "spot_brl":   {"title": "Ouro · Spot (R$/g)",
                   "fmt": lambda v: f"R$ {fmt_brl(v)}/g",
                   "yfmt": lambda v: fmt_brl(v).split(",")[0],
                   "ranges": (7, 30, 90, 180, 365)},
    "gc_f":       {"title": "COMEX · Futuro GC=F (USD/oz)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}",
                   "yfmt": lambda v: f"{v:,.0f}",
                   "ranges": (7, 30, 90, 180, 365)},
    "ho_f":       {"title": "NYMEX · Diesel HO=F (USD/gal)",
                   "fmt": lambda v: f"US$ {v:,.3f}",
                   "yfmt": lambda v: f"{v:.2f}",
                   "ranges": (7, 30, 90, 180, 365)},
    "brent":      {"title": "Brent · Futuro BZ=F (USD/bbl)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}",
                   "yfmt": lambda v: f"{v:,.0f}",
                   "ranges": (7, 30, 90, 180, 365)},
    "urals":      {"title": "Rússia · Urals (USD/bbl)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}",
                   "yfmt": lambda v: f"{v:,.0f}",
                   "ranges": (7, 30, 90, 180, 365)},
    "sge_au9999": {"title": "SGE Au99.99 (R$/g)",
                   "fmt": lambda v: f"R$ {fmt_brl(v)}/g",
                   "yfmt": lambda v: fmt_brl(v).split(",")[0],
                   "ranges": (7, 30, 90, 180, 365)},
    "sge_autd":   {"title": "SGE Au(T+D) (R$/g)",
                   "fmt": lambda v: f"R$ {fmt_brl(v)}/g",
                   "yfmt": lambda v: fmt_brl(v).split(",")[0],
                   "ranges": (7, 30, 90, 180, 365)},
    "shfe":       {"title": "SHFE futuro (R$/g)",
                   "fmt": lambda v: f"R$ {fmt_brl(v)}/g",
                   "yfmt": lambda v: fmt_brl(v).split(",")[0],
                   "ranges": (7, 30, 90, 180, 365)},
    "base_cn":    {"title": "Base China Gold (R$/g)",
                   "fmt": lambda v: f"R$ {fmt_brl(v)}/g",
                   "yfmt": lambda v: fmt_brl(v).split(",")[0],
                   "ranges": (7, 30, 90, 180, 365)},
    "fuel_gas":   {"title": "EUA · Gasolina (US$/gal)",
                   "fmt": lambda v: f"US$ {v:,.3f}/gal",
                   "yfmt": lambda v: f"{v:.2f}",
                   "ranges": (30, 90, 180, 365)},
    "fuel_diesel": {"title": "EUA · Diesel (US$/gal)",
                    "fmt": lambda v: f"US$ {v:,.3f}/gal",
                    "yfmt": lambda v: f"{v:.2f}",
                    "ranges": (30, 90, 180, 365)},
    "cds_5y":     {"title": "Brasil · CDS 5 anos (bps)",
                   "fmt": lambda v: f"{fmt_bps(v)} bps",
                   "yfmt": lambda v: f"{v:.0f}",
                   "ranges": (7, 30)},
}


def fetch_history(key, days=30, hist_log=None):
    days = int(days)
    base = key
    bank_name = None
    if key.startswith("bank:"):
        bank_name = key.split(":", 1)[1]
        base = "sge_au9999"
    note = None
    if bank_name:
        note = f"{bank_name} acompanha o fisico: serie SGE de referencia"
    try:
        if base == "spot_usd":
            pts, src = _hist_paxg(days)
        elif base == "spot_brl":
            paxg, s1 = _hist_paxg(days + 10)
            fx, s2 = _hist_fx("USD-BRL", days + 10)
            joined = _hist_join([(d, p / TROY_OZ_GRAMS) for d, p in paxg],
                                dict(fx))
            if len(joined) < 2:
                raise ValueError("juncao PAXG x USDBRL vazia")
            pts = joined[-days:] if len(joined) > days else joined
            src = f"PAXG x USDBRL ({s1}; {s2})"
        elif base == "gc_f":
            pts, src = _hist_yahoo("GC=F", days)
        elif base == "ho_f":
            pts, src = _hist_yahoo("HO=F", days)
        elif base == "brent":
            pts, src = _hist_yahoo("BZ=F", days)
        elif base == "urals":
            pts, src = _hist_urals(days)
        elif base in ("sge_au9999", "sge_autd"):
            inst = "Au99.99" if base == "sge_au9999" else "Au(T+D)"
            sec = "118.AU9999" if base == "sge_au9999" else "118.AUTD"
            try:
                cny_pts, s0 = _hist_sge(inst, days + 10)
                s0 = f"SGE {inst}"
            except Exception:
                cny_pts, s0 = _hist_em(sec, days + 10)
            try:
                fx, s1 = _hist_fx("CNY-BRL", days + 10)
                joined = _hist_join(cny_pts, dict(fx))
                if len(joined) < 2:
                    raise ValueError("juncao SGE x CNYBRL vazia")
                pts = joined[-days:] if len(joined) > days else joined
                src = f"{s0} x CNYBRL"
            except Exception as e2:
                pts = cny_pts[-days:] if len(cny_pts) > days else cny_pts
                src = s0
                n2 = "sem CNYBRL historico: valores em CNY/g"
                note = f"{note} · {n2}" if note else n2
                log(f"hist {base}: {e2}; mostrando CNY")
        elif base == "shfe":
            try:
                cny_pts, _s0 = _hist_em("113.aum", days + 10)
                s0 = "SHFE"
            except Exception:
                cny_pts, s0 = _hist_sge("Au99.99", days + 10)
                s0 = "SGE Au99.99 (proxy SHFE)"
                n2 = "SHFE sem serie: referencia SGE"
                note = f"{note} · {n2}" if note else n2
            try:
                fx, _s1 = _hist_fx("CNY-BRL", days + 10)
                joined = _hist_join(cny_pts, dict(fx))
                if len(joined) < 2:
                    raise ValueError("juncao SHFE x CNYBRL vazia")
                pts = joined[-days:] if len(joined) > days else joined
                src = f"{s0} x CNYBRL"
            except Exception as e2:
                pts = cny_pts[-days:] if len(cny_pts) > days else cny_pts
                src = s0
                n2 = "sem CNYBRL historico: valores em CNY/g"
                note = f"{note} · {n2}" if note else n2
        elif base == "base_cn":
            paxg, s1 = _hist_paxg(days + 10)
            ub, _s2 = _hist_fx("USD-BRL", days + 10)
            cb, _s3 = _hist_fx("CNY-BRL", days + 10)
            ubd, cbd = dict(ub), dict(cb)
            out = []
            for dt, p in paxg:
                u, c = ubd.get(dt), cbd.get(dt)
                if u and c:
                    out.append((dt, p * (u / c) / TROY_OZ_GRAMS))
            if len(out) < 2:
                raise ValueError("juncao base CN vazia")
            pts = out[-days:] if len(out) > days else out
            src = "PAXG x USDCNY/oz (derivada)"
        elif base == "fuel_gas":
            pts, src = _hist_fred(["GASREGW"], days)
        elif base == "fuel_diesel":
            pts, src = _hist_fred(list(DIESEL_FRED_IDS), days)
        elif base == "cds_5y":
            pts, src = _hist_cds(days)
        else:
            raise ValueError(f"ativo desconhecido: {key}")
    except Exception as e:
        if hist_log:
            fb = hist_log_series(hist_log, key, days)
            if len(fb) >= 2:
                return {"points": fb, "src": "cache local",
                        "note": f"serie remota falhou ({e})"}
            if base != key:
                fb = hist_log_series(hist_log, base, days)
                if len(fb) >= 2:
                    return {"points": fb, "src": "cache local",
                            "note": f"serie remota falhou ({e})"}
        raise
    return {"points": pts, "src": src, "note": note}


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
_LOG_LOCK = threading.Lock()

def log(msg):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n"
        with _LOG_LOCK:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
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

def fmt_bps(v):
    """121,1 (pt-BR, 1 decimal) — CDS em basis points."""
    s = f"{v:,.1f}"
    return s.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")

def _has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)

def _chg_pct(price, chg):
    """Variação % do dia a partir do delta absoluto em US$/gal (AAA)."""
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

def _http_post_json(url, payload, headers=None, timeout=NET_TIMEOUT):
    hdrs = {"User-Agent": "gold-widget/5.0", "Accept": "*/*",
            "Content-Type": "application/json; charset=utf-8"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

# --------------------- BACKOFF POR SEÇÃO (offline/429) -----------------------
# Fonte morta não pode virar martelada: cada seção com refetch próprio
# leva um cooldown que dobra a cada falha consecutiva da CADEIA INTEIRA
# (teto 30 min). "429" em qualquer degrau da cadeia conta como falha
# dupla (excesso de requisição pede pausa maior). Sucesso zera o estado.
_RETRY = {}                              # key -> [next_try_ts, fails]

def _due(key, rec, interval):
    """Hora de refetch: sem dado novo há `interval` E fora de cooldown."""
    if rec and time.time() - rec.get("ts", 0) < interval:
        return False
    st = _RETRY.get(key)
    return st is None or time.time() >= st[0]

def _cooldown(key, interval, errs=""):
    st = _RETRY.setdefault(key, [0.0, 0])
    st[1] += 2 if "429" in errs else 1
    wait = min(interval * (2 ** min(st[1], 6)), 1800)
    wait += random.uniform(0, min(15, wait * 0.1))   # v6.4: jitter p/ não sincronizar polls
    st[0] = time.time() + wait
    log(f"{key}: cadeia morta; cooldown {wait:.0f}s")

def _cooldown_clear(key):
    _RETRY.pop(key, None)

# v6.4 — backoff POR FONTE (não só por cadeia). Sucesso via fallback NÃO
# pode zerar o castigo da fonte primária morta, senão o poll seguinte
# martela o Yahoo banido de novo a cada ciclo e o ban nunca acaba.
_SRC_RETRY = {}                           # src-name -> [next_try_ts, fails]

def _src_due(name):
    st = _SRC_RETRY.get(name)
    return st is None or time.time() >= st[0]

def _src_cooldown(name, interval, errs=""):
    st = _SRC_RETRY.setdefault(name, [0.0, 0])
    st[1] += 2 if "429" in errs else 1
    wait = min(interval * (2 ** min(st[1], 6)), 1800)
    wait += random.uniform(0, min(15, wait * 0.1))
    st[0] = time.time() + wait
    log(f"{name}: fonte em cooldown {wait:.0f}s")

def _src_clear(name):
    _SRC_RETRY.pop(name, None)

# v6.4 — throttle global do Yahoo (no máx. 1 req / 1,5s neste processo;
# widget + gráficos + dumps disputam o mesmo IP).
_YAHOO_LAST = [0.0]
_YAHOO_LOCK = threading.Lock()

def _yahoo_throttle(min_gap=1.5):
    with _YAHOO_LOCK:
        dt = time.time() - _YAHOO_LAST[0]
        if dt < min_gap:
            time.sleep(min_gap - dt)
        _YAHOO_LAST[0] = time.time()

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

def _fetch_yahoo_future(sym, url):
    """Futuro contínuo do Yahoo (chart API, grátis, sem chave). Usado pelo
    GC=F (v5.6) e pelo HO=F (v6.1). Preço = regularMarketPrice; referência =
    fech. anterior. range=5d dá barras suficientes p/ achar o fechamento da
    sessão anterior. v6.4: throttle + tenta query2 se query1 der 429."""
    _yahoo_throttle()
    try:
        d = _get_json(url, {"User-Agent": BROWSER_UA})
    except urllib.error.HTTPError as e:
        if getattr(e, "code", None) == 429 and "query1." in url:
            _yahoo_throttle()
            url2 = url.replace("query1.", "query2.")
            d = _get_json(url2, {"User-Agent": BROWSER_UA})
        else:
            raise
    res = ((d.get("chart") or {}).get("result") or [])
    if not res:
        raise ValueError(f"Yahoo {sym} sem resultado")
    m = res[0].get("meta") or {}
    closes = [c for c in ((((res[0].get("indicators") or {}).get("quote")
                            or [{}])[0]).get("close") or []) if c is not None]
    price = m.get("regularMarketPrice")
    if price is None and closes:
        price = closes[-1]
    prev = closes[-2] if len(closes) >= 2 else m.get("chartPreviousClose")
    price, prev = _to_float(price), _to_float(prev)
    if not price or not prev or price <= 0 or prev <= 0:
        raise ValueError(f"Yahoo {sym} sem preço válido")
    return {"price": price, "prev_close": prev,
            "pct": (price / prev - 1.0) * 100.0,
            "name": m.get("shortName") or "", "src": "Yahoo", "ts": time.time()}

def fetch_gc_yahoo_q1():
    """Yahoo GC=F host primário (nome próprio p/ log legível)."""
    return _fetch_yahoo_future("GC=F", YAHOO_GC_URL)

def fetch_gc_yahoo_q2():
    """Yahoo GC=F host reserva."""
    return _fetch_yahoo_future("GC=F", YAHOO_GC_URL_Q2)

def fetch_gc_fxempire():
    """Fallback GC=F: FXEmpire ouro (CFD/Oanda, realtime). Blob
    prices.gold no SSR de /commodities/gold (last/percentChange/
    previousClose/high/low/lastUpdate). Pipeline independente do Yahoo."""
    html = _http_get(FXE_GOLD_URL, {"User-Agent": BROWSER_UA},
                     timeout=25).decode("utf-8", "replace")
    i = html.find('"prices":{"gold":{')
    if i < 0:
        # fallback: qualquer segmento com "correspondingFutures":"gc"
        i = html.find('"correspondingFutures":"gc"')
        if i < 0:
            raise ValueError("FXEmpire ouro sem blob")
        i = max(0, i - 6000)
    seg = html[i:i + 12000]
    # extrai o objeto gold por balanceamento simples
    j = seg.find("{", seg.find('"gold"') if '"gold"' in seg else 0)
    if j < 0:
        # plano B: regex direta nos campos
        m = re.search(r'"last":\s*([0-9]+(?:\.[0-9]+)?)', seg)
        if not m:
            raise ValueError("FXEmpire ouro sem last")
        price = float(m.group(1))
        mp = re.search(r'"percentChange":\s*(-?[0-9]+(?:\.[0-9]+)?)', seg)
        mc = re.search(r'"previousClose":\s*"?([0-9]+(?:\.[0-9]+)?)"?', seg)
        mh = re.search(r'"high":\s*([0-9]+(?:\.[0-9]+)?)', seg)
        ml = re.search(r'"low":\s*([0-9]+(?:\.[0-9]+)?)', seg)
        mu = re.search(r'"lastUpdate":\s*"([^"]+)"', seg)
        prev = float(mc.group(1)) if mc else None
        pct = float(mp.group(1)) if mp else ((price / prev - 1.0) * 100.0 if prev else None)
        return {"price": price, "pct": pct, "prev_close": prev,
                "high": float(mh.group(1)) if mh else None,
                "low": float(ml.group(1)) if ml else None,
                "vendor_ts": mu.group(1) if mu else "",
                "name": "Gold CFD", "src": "FXEmpire/Oanda", "ts": time.time()}
    depth, k = 0, j
    while k < len(seg):
        if seg[k] == "{":
            depth += 1
        elif seg[k] == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    try:
        q = json.loads(seg[j:k + 1])
    except Exception:
        raise ValueError("FXEmpire ouro JSON inválido")
    price = _to_float(q.get("last"))
    if not price or price <= 0 or price > 100000:
        raise ValueError("FXEmpire ouro sem preço válido")
    prev = _to_float(q.get("previousClose"))
    pct = _to_float(q.get("percentChange"))
    if pct is None and prev and prev > 0:
        pct = (price / prev - 1.0) * 100.0
    return {"price": price, "pct": pct, "prev_close": prev,
            "high": _to_float(q.get("high")), "low": _to_float(q.get("low")),
            "vendor_ts": q.get("lastUpdate") or "",
            "name": "Gold CFD", "src": "FXEmpire/Oanda", "ts": time.time()}

def fetch_gc_gporg():
    """Fallback GC=F: goldprice.org (spot Londres, proxy do futuro)."""
    g = fetch_goldprice_org("USD")
    return {"price": g["price"], "prev_close": g.get("prev_close"),
            "pct": g.get("pct"), "name": "Gold spot (proxy)",
            "src": "goldprice.org", "ts": time.time()}

def fetch_gc_sina():
    """Fallback GC=F: Sina hf_XAU (spot Londres USD, proxy do futuro)."""
    sina = fetch_sina()
    r = (sina or {}).get("hf_XAU")
    if not r or not r.get("price"):
        raise ValueError("Sina hf_XAU sem preço")
    return {"price": r["price"], "prev_close": r.get("prev_close"),
            "pct": r.get("pct"), "name": "",
            "src": "Sina hf_XAU (spot proxy)", "ts": time.time()}

def fetch_gc_future():
    """Futuro COMEX ouro contínuo (GC=F): rola sozinho p/ o contrato mais
    líquido (dez/26; em nov/dez, fev/27). Cadeia (v6.4 PERFEITA):
    Yahoo-q1 -> Yahoo-q2 -> FXEmpire -> TradingEconomics -> goldprice.org
    -> Sina hf_XAU -> cache (a camada de cima mantém). Cada fonte tem
    cooldown próprio: fallback que salva NÃO anistia a primária morta."""
    cands = (
        ("Yahoo-GC-q1", fetch_gc_yahoo_q1, GC_REFETCH),
        ("Yahoo-GC-q2", fetch_gc_yahoo_q2, GC_REFETCH),
        ("FXEmpire-GC", fetch_gc_fxempire, GC_REFETCH),
        ("TE-GC", fetch_gc_te, GC_REFETCH),
        ("GPorg-GC", fetch_gc_gporg, GC_REFETCH),
        ("Sina-GC", fetch_gc_sina, GC_REFETCH),
    )
    errs = []
    for name, fn, iv in cands:
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            continue
        try:
            r = fn()
            _src_clear(name)
            return r
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, iv, str(e))
    raise RuntimeError("GC=F sem fonte viva (" + "; ".join(errs) + ")")

def fetch_ho_yahoo():
    """Futuro NYMEX ULSD/diesel contínuo (HO=F) pelo chart do Yahoo —
    fonte principal, mesmo pipeline do GC=F."""
    return _fetch_yahoo_future("HO=F", YAHOO_HO_URL)

def fetch_ho_yahoo_q2():
    """HO=F host reserva."""
    return _fetch_yahoo_future("HO=F", YAHOO_HO_URL_Q2)

def _fxe_segment(html, marker):
    """Último segmento {"state":{"data":{"statusCode":…}}} do react-query
    que vem ANTES do marker (ex.: '"vendorSymbol":"HO"'). O segmento que
    contém o marker é o que interessa. Extração por balanceamento de
    chaves: nada de regex frágil sobre JSON aninhado."""
    pos = html.find(marker)
    if pos < 0:
        raise ValueError(f"FXEmpire sem blob ({marker})")
    starts = [m.start() for m in
              re.finditer(r'\{"state":\{"data":\{"statusCode":', html)]
    cand = [s for s in starts if s < pos]
    if not cand:
        raise ValueError("FXEmpire sem segmento")
    s0 = cand[-1]
    i, depth = s0, 0
    end = min(len(html), s0 + 120000)
    while i < end:
        ch = html[i]
        if ch == '"':
            j = i + 1
            while j < end:
                if html[j] == "\\":
                    j += 2
                    continue
                if html[j] == '"':
                    break
                j += 1
            i = j
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                d = json.loads(html[s0:i + 1])
                return (((d.get("state") or {}).get("data") or {})
                        .get("data") or {})
        i += 1
    raise ValueError("FXEmpire segmento sem fim")

def fetch_ho_fxempire():
    """Fallback do diesel: SSR da página /commodities/ho do FXEmpire — o
    cache do react-query vem serializado em <script>, como segmentos
    {"state":{"data":{"statusCode":N,"data":…}},"queryKey":…}. O segmento
    que interessa contém "vendorSymbol":"HO" (único) e, dentro, o quote do
    Oanda (front-month; futuresMonth = contrato principal)."""
    html = _http_get(FXE_HO_URL, {"User-Agent": BROWSER_UA},
                     timeout=25).decode("utf-8", "replace")
    q = _fxe_segment(html, '"vendorSymbol":"HO"')
    price = _to_float(q.get("last"))
    month, chg, pct, high, low = "", None, None, None, None
    # front-month real: 1º contrato com expiração futura — é o que o HO=F do
    # Yahoo e o HO1! do TradingView acompanham (o blob top-level é o contrato
    # "principal" da Oanda, que pode estar 1 vencimento à frente: hoje o
    # front é HOV26/out/26 ~5.09 e o top-level traz nov/26 ~4.85)
    con = q.get("contracts") or []
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    front = next((c for c in con
                  if (c.get("expiration_date") or "") >= hoje), None)
    if front:
        price = _to_float(front.get("last_price"))
        month = front.get("display_month") or ""
        chg = _to_float(front.get("net_change"))
        pct = _to_float(front.get("percent_change"))
        high = _to_float(front.get("high"))
        low = _to_float(front.get("low"))
        prev = (round(price - chg, 4) if price is not None and chg else None)
    else:                       # lista de contratos ausente/expirada: top-level
        price = _to_float(q.get("last"))
        chg = _to_float(q.get("change"))
        pct = _to_float(q.get("percentChange"))
        prev = _to_float(q.get("previousClose"))
        high = _to_float(q.get("high"))
        low = _to_float(q.get("low"))
        month = q.get("futuresMonth") or ""
    if not price or price <= 0 or price > 100:
        raise ValueError("FXEmpire sem preço válido")
    if pct is None and prev and prev > 0:
        pct = (price / prev - 1.0) * 100.0
    return {"price": price,
            "pct": pct,
            "day_chg": chg,
            "prev_close": prev,
            "high": high,
            "low": low,
            "oi": _to_float(q.get("openInterest")),
            "month": month,
            "vendor_ts": q.get("lastUpdate") or "",
            "name": q.get("name") or "",
            "src": "FXEmpire/Oanda", "ts": time.time()}

def fetch_ho_te():
    """Fallback 2 do diesel: scrape do SSR do Trading Economics."""
    return {**_fetch_te_commodity(TE_HO_URL, 100), "ts": time.time()}

def _fetch_te_commodity(url, hi):
    """Scrape do SSR do Trading Economics — <span id="market_last"> com o
    preço (aceita separador de milhar, ex.: '4,374.01'), market_daily_chg
    com o Δ absoluto e market_daily_Pchg com o Δ% do dia."""
    html = _http_get(url, {"User-Agent": BROWSER_UA,
                           "Accept-Language": "en-US,en;q=0.9"},
                     timeout=30).decode("utf-8", "replace")
    m = re.search(r'id="market_last">'
                  r'\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*<', html)
    if not m:
        raise ValueError("TE sem market_last")
    price = float(m.group(1).replace(",", ""))
    if not price or price <= 0 or price > hi:
        raise ValueError("TE sem preço válido")
    mc = re.search(r'id="market_daily_chg"[^>]*>'
                   r'\s*([-+]?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', html)
    mp = re.search(r'id="market_daily_Pchg"[^>]*>'
                   r'\s*(-?[0-9]+(?:\.[0-9]+)?)\s*%', html)
    chg = _to_float(mc.group(1).replace(",", "")) if mc else None
    return {"price": price,
            "pct": _to_float(mp.group(1)) if mp else None,
            "day_chg": chg,
            "prev_close": (round(price - chg, 4) if chg else None),
            "month": "", "src": "TradingEconomics", "ts": time.time()}

def fetch_gc_te():
    """Fallback do GC=F: scrape do SSR do Trading Economics (referência
    internacional do ouro, USD/oz) — 2º degrau quando o Yahoo limita."""
    return {**_fetch_te_commodity(TE_GC_URL, 100000), "ts": time.time()}

def fetch_ho_future():
    """Futuro NYMEX ULSD/diesel (HO=F) em US$/gal. Cadeia (v6.4):
    Yahoo-q1 -> Yahoo-q2 -> FXEmpire -> TradingEconomics -> cache.
    Todas sem chave; cada fonte tem cooldown próprio."""
    cands = (
        ("Yahoo-HO-q1", fetch_ho_yahoo, HO_REFETCH),
        ("Yahoo-HO-q2", fetch_ho_yahoo_q2, HO_REFETCH),
        ("FXEmpire-HO", fetch_ho_fxempire, HO_REFETCH),
        ("TE-HO", fetch_ho_te, HO_REFETCH),
    )
    errs = []
    for name, fn, iv in cands:
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            continue
        try:
            r = fn()
            _src_clear(name)
            return r
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, iv, str(e))
    raise RuntimeError("diesel NYMEX sem fonte viva (" + "; ".join(errs) + ")")

# ------------------- FETCH · CRUDE URALS (Rússia, v6.2) ----------------------
def _urals_delay(txt):
    """'2-day Delay' -> '2d' · '(11-Minute Delay)'/'11 min delay' -> '11m';
    outro formato, texto baixo."""
    m = re.search(r"(\d+)\s*-?\s*(day|minute|min)", txt or "", re.I)
    return (f"{m.group(1)}{m.group(2)[0].lower()}"
            if m else (txt or "").strip().lower())

# A tabela do OilPrice.com alimenta Urals E Brent — cache curto evita
# request duplicado quando as duas seções precisam do fallback juntos.
_OILPRICE_PAGE = {"html": None, "ts": 0.0}

def _oilprice_charts_page():
    now = time.time()
    if (_OILPRICE_PAGE["html"] is None
            or now - _OILPRICE_PAGE["ts"] > OILPRICE_PAGE_TTL):
        _OILPRICE_PAGE["html"] = _http_get(
            OILPRICE_CHARTS_URL, {"User-Agent": BROWSER_UA},
            timeout=25).decode("utf-8", "replace")
        _OILPRICE_PAGE["ts"] = now
    return _OILPRICE_PAGE["html"]

def _oilprice_row(name_re, lo=1.0, hi=500.0):
    """Preço de um blend na tabela principal do OilPrice.com — 1ª linha
    data-name='<name_re>…'. GET puro, sem chave: preço no atributo
    data-price, Δ$ na célula change_up/down, Δ% na change_*_percent e
    data no data-stamp. O Brent usa classes compostas na célula do Δ$
    ('change_down flat_change_cell'): o [^']* cobre o sufixo extra sem
    quebrar o caso simples do Urals."""
    html = _oilprice_charts_page()
    m = re.search(r"data-name='(%s[^']*)'" % name_re, html)
    if not m:
        raise ValueError(f"OilPrice sem linha ({name_re})")
    e = html.find("</tr>", m.start())
    row = html[m.start():e if e > 0 else m.start() + 4000]
    mp = re.search(r"data-price='([0-9.]+)'", row)
    if not mp:
        raise ValueError("OilPrice sem preço na linha")
    price = _to_float(mp.group(1))
    if not price or price < lo or price > hi:
        raise ValueError("OilPrice com preço inválido")
    mc = re.search(r"class='change_(?:up|down)[^']*'>\s*([-+]?[0-9.]+)", row)
    mpct = re.search(r"change_(?:up|down)_percent[^>]*>\s*([-+]?[0-9.]+)%", row)
    mstamp = re.search(r"data-stamp='(\d+)'", row)
    mdelay = re.search(r"blend_update_text'>\(([^)]+)\)", row)
    chg = _to_float(mc.group(1)) if mc else None
    pct = _to_float(mpct.group(1)) if mpct else None
    prev = (round(price - chg, 2) if price is not None and chg is not None
            else None)
    if pct is None and prev and prev > 0:
        pct = (price / prev - 1.0) * 100.0
    day = (datetime.fromtimestamp(int(mstamp.group(1)), timezone.utc)
           .strftime("%Y-%m-%d") if mstamp else None)
    return {"price": price, "pct": pct, "day_chg": chg, "prev_close": prev,
            "delay": _urals_delay(mdelay.group(1) if mdelay else ""),
            "day": day, "src": "OilPrice.com", "ts": time.time()}

def fetch_urals_table():
    """Preço do Urals na tabela principal do OilPrice.com — a linha
    data-name='Urals-Brent' (avaliação spot com 1-2 dias de atraso)."""
    return _oilprice_row("Urals")

def _oilprice_json_period(blend_id, period):
    """Série de um blend no endpoint JSON do OilPrice.com (o mesmo que o
    gráfico deles consome). CSRF vem de /ajax/csrf; o POST exige header
    X-Requested-With — sem ele a rota devolve HTML em vez de JSON."""
    csrf = _get_json(OILPRICE_CSRF_URL,
                     {"X-Requested-With": "XMLHttpRequest",
                      "Referer": "https://oilprice.com/"})
    data = urllib.parse.urlencode({"blend_id": blend_id,
                                   "period": str(period),
                                   csrf["name"]: csrf["hash"]}).encode()
    req = urllib.request.Request(
        OILPRICE_JSON_URL, data=data,
        headers={"User-Agent": BROWSER_UA,
                 "X-Requested-With": "XMLHttpRequest",
                 "Origin": "https://oilprice.com",
                 "Referer": ("https://oilprice.com/freewidgets/"
                             f"get_oilprices_chart/{blend_id}/4"),
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=NET_TIMEOUT + 7) as r:
        d = json.loads(r.read().decode("utf-8"))
    pts = [(int(p["time"]), float(p["price"]))
           for p in (d.get("prices") or []) if isinstance(p, dict)]
    last_close = _to_float(d.get("last_close_price"))
    update = (((d.get("blend") or {}).get("update_text")) or "")
    return pts, last_close, update

def _oilprice_json_quote(blend_id):
    """Quote de um blend no freewidgets: último ponto da série (período
    4 = ~1 mês; o preço atual é o último ponto). Variação vs
    last_close_price (fechamento anterior) ou vs o ponto anterior."""
    pts, last_close, update = _oilprice_json_period(blend_id, 4)
    if not pts:
        raise ValueError("freewidgets sem série")
    price = pts[-1][1]
    if not price or price < 1 or price > 500:
        raise ValueError("freewidgets com preço inválido")
    prev = last_close if (last_close and last_close != price) else (
        pts[-2][1] if len(pts) >= 2 else None)
    pct = (price / prev - 1.0) * 100.0 if prev and prev > 0 else None
    day = datetime.fromtimestamp(pts[-1][0], timezone.utc).strftime("%Y-%m-%d")
    return {"price": price, "pct": pct,
            "day_chg": (round(price - prev, 2) if prev else None),
            "prev_close": prev, "delay": _urals_delay(update), "day": day}

def fetch_urals_json():
    """Fallback do Urals: quote JSON do freewidgets (blend 4466)."""
    return {**_oilprice_json_quote(URALS_BLEND_ID),
            "src": "OilPrice.com (freewidgets)", "ts": time.time()}

def fetch_urals():
    """Crude Urals (blend de exportação russo), US$/barril. Cadeia (v6.2):
    OilPrice.com tabela (GET) -> OilPrice.com freewidgets (POST JSON com
    CSRF). Avaliação com 1-2 dias de atraso; falha isolada das demais."""
    errs = []
    for fetcher in (fetch_urals_table, fetch_urals_json):
        try:
            return fetcher()
        except Exception as e:
            errs.append(f"{fetcher.__name__}: {e}")
    raise RuntimeError("crude Urals sem fonte (" + "; ".join(errs) + ")")

# ----------------------- FETCH · BRENT (benchmark, v6.3) ---------------------
def fetch_brent_yahoo():
    """Brent pelo chart do Yahoo (front-month contínuo BZ=F) — fonte
    principal, mesmo pipeline do GC=F/HO=F."""
    return _fetch_yahoo_future("BZ=F", YAHOO_BZ_URL)

def fetch_brent_fxempire():
    """Fallback do Brent: SSR da página /commodities/brent-crude-oil do
    FXEmpire. Blob DIFERENTE do do HO: aqui o quote vem do segmento
    /commodities/rates?instruments=brent-crude-oil…, com o CFD BCO/USD
    (Oanda, realtime=true): prices[name] = {last, change, percentChange,
    previousClose (string), high, low, lastUpdate (ISO)}."""
    html = _http_get(FXE_BRENT_URL, {"User-Agent": BROWSER_UA},
                     timeout=25).decode("utf-8", "replace")
    data = _fxe_segment(html, '"vendorSymbol":"BCO/USD"')
    q = (data.get("prices") or {}).get("brent-crude-oil") or {}
    price = _to_float(q.get("last"))
    if not price or price <= 0 or price > 500:
        raise ValueError("FXEmpire sem preço válido")
    chg = _to_float(q.get("change"))
    pct = _to_float(q.get("percentChange"))
    prev = _to_float(q.get("previousClose"))
    if pct is None and prev and prev > 0:
        pct = (price / prev - 1.0) * 100.0
    return {"price": price, "pct": pct, "day_chg": chg, "prev_close": prev,
            "high": _to_float(q.get("high")), "low": _to_float(q.get("low")),
            "vendor_ts": q.get("lastUpdate") or "",
            "name": "Brent CFD", "src": "FXEmpire/Oanda", "ts": time.time()}

def fetch_brent_oilprice():
    """Brent na tabela do OilPrice.com — linha data-name='Brent-Crude'
    (data-id 46): avaliação com ~11 min de atraso; fica viva quando
    Yahoo e FXEmpire caem juntos. Mesma página do Urals (cache 2min)."""
    return _oilprice_row("Brent")

def fetch_brent_json():
    """Última linha do Brent: POST JSON do freewidgets (blend 46) — a
    mesma mecânica (CSRF + X-Requested-With) do fallback do Urals."""
    return {**_oilprice_json_quote(BRENT_BLEND_ID),
            "src": "OilPrice.com (freewidgets)", "ts": time.time()}

def fetch_brent_yahoo_q2():
    """Brent host reserva."""
    return _fetch_yahoo_future("BZ=F", YAHOO_BZ_URL_Q2)

def fetch_brent():
    """Brent (benchmark global), US$/barril. Cadeia (v6.4): Yahoo-q1 ->
    Yahoo-q2 -> FXEmpire -> OilPrice tabela -> OilPrice freewidgets ->
    cache. Todas sem chave; cada fonte tem cooldown próprio."""
    cands = (
        ("Yahoo-BZ-q1", fetch_brent_yahoo, BRENT_REFETCH),
        ("Yahoo-BZ-q2", fetch_brent_yahoo_q2, BRENT_REFETCH),
        ("FXEmpire-BZ", fetch_brent_fxempire, BRENT_REFETCH),
        ("OilPrice-tab", fetch_brent_oilprice, BRENT_REFETCH),
        ("OilPrice-json", fetch_brent_json, BRENT_REFETCH),
    )
    errs = []
    for name, fn, iv in cands:
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            continue
        try:
            r = fn()
            _src_clear(name)
            return r
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, iv, str(e))
    raise RuntimeError("brent sem fonte viva (" + "; ".join(errs) + ")")

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

_AAA_DATE = re.compile(r"Price as of\s*(\d{1,2})/(\d{1,2})/(\d{2,4})")

def _aaa_tag(td):
    """Texto limpo de uma célula da tabela AAA (sem tags/entidades)."""
    return re.sub(r"<[^>]+>", " ", td).replace("&nbsp;", " ").strip()

def fetch_us_fuel():
    """Média nacional DIÁRIA de varejo (AAA Fuel Prices): gasolina regular e
    diesel, US$/gal com impostos. A AAA atualiza 1x/dia ("Price as of …");
    variação exibida = vs ontem (linhas Current/Yesterday da tabela)."""
    html = _http_get(AAA_FUEL_URL, {"User-Agent": BROWSER_UA},
                     timeout=30).decode("utf-8", "replace")
    m = _AAA_DATE.search(html)
    if not m:
        raise ValueError("AAA sem 'Price as of'")
    mo, dy, yr = (int(g) for g in m.groups())
    day = f"{yr + (2000 if yr < 100 else 0):04d}-{mo:02d}-{dy:02d}"
    tbl = re.search(r'<table class="table-mob">(.*?)</table>', html, re.S)
    if not tbl:
        raise ValueError("AAA sem tabela nacional")
    seg = tbl.group(1)
    cols = [_aaa_tag(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", seg, re.S)]
    rows = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", seg, re.S):
        tds = [_aaa_tag(t) for t in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        # 1ª coluna = rótulo da linha (Current Avg., Yesterday Avg., …);
        # exige alinhamento exato com o thead pra indexar pela coluna certa
        if len(tds) == len(cols) and tds[0]:
            rows[tds[0]] = tds
    def _col(vals, name):
        if not vals or name not in cols:
            return None
        return _to_float(vals[cols.index(name)].lstrip("$"))
    cur = rows.get("Current Avg.")
    gas, die = _col(cur, "Regular"), _col(cur, "Diesel")
    if not gas or not die or gas <= 0 or die <= 0:
        raise ValueError("AAA sem preço válido")
    yes = rows.get("Yesterday Avg.")
    g0, d0 = _col(yes, "Regular"), _col(yes, "Diesel")
    return {"gas": gas, "gas_chg": round(gas - g0, 4) if g0 else None,
            "diesel": die, "diesel_chg": round(die - d0, 4) if d0 else None,
            "day": day, "src": "AAA Fuel Prices", "ts": time.time()}

# ------------------- FETCH · CDS 5 ANOS BRASIL (WGB) ------------------------
def _wgb_payload_from_page():
    """Reextrai o payload jsGlobalVars da página do Brasil — usado quando o
    payload embutido deixa de ser aceito (contrato pode mudar sem aviso)."""
    html = _http_get(WGB_PAGE_URL, {"User-Agent": BROWSER_UA,
                                    "Accept-Language": "en-US,en;q=0.9"}
                     ).decode("utf-8", "replace")
    m = re.search(r"var\s+jsGlobalVars\s*=\s*(\{.*?\});", html, re.S)
    if not m:
        raise ValueError("página WGB sem jsGlobalVars")
    return json.loads(m.group(1))

def _wgb_cell(c):
    t = re.sub(r"<[^>]+>", " ", c)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip()

def _parse_cds_resp(d):
    """Resposta do REST do WGB -> {bps, w_pct, m_pct, y_pct, pd_pct, dt}.
    A tabela cdsTableHtml traz a linha "5 Years CDS" (o tenor que eles
    reportam); se o layout mudar, usa os campos soltos lastCds/
    lastCdsDefaultProb (sem variações)."""
    if not d.get("success"):
        raise ValueError("WGB success=False")
    out = {"dt": d.get("lastTimeValDesc") or d.get("lastDataValDesc"),
           "src": "WGB"}
    head, row5 = None, None
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", d.get("cdsTableHtml") or "",
                         re.S):
        cells = [_wgb_cell(c) for c in
                 re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if not any(cells):
            continue
        if head is None and any("CDS Value" in c for c in cells):
            head = cells
        elif any(c.startswith("5 Year") for c in cells[:2]):
            row5 = cells
            break
    if head and row5:
        def col(frag):
            for i, c in enumerate(head):
                if frag in c:
                    return i
            return None
        for frag, key in (("CDS Value", "bps"), ("1W", "w_pct"),
                          ("1M", "m_pct"), ("1Y", "y_pct"),
                          ("Implied PD", "pd_pct")):
            i = col(frag)
            out[key] = (_to_float(row5[i].replace("%", "").strip())
                        if i is not None and i < len(row5) else None)
    if not out.get("bps"):
        # layout da tabela mudou: campos soltos da resposta (sem variações)
        out["bps"] = _to_float(d.get("lastCds"))
        if not out.get("pd_pct"):
            out["pd_pct"] = _to_float(d.get("lastCdsDefaultProb"))
    if not out.get("bps") or out["bps"] <= 0:
        raise ValueError("WGB sem valor de CDS")
    return out

def _inv_price_block(node):
    """1º dict do SSR do Investing que traz cotação (last + lastUpdateTime).
    Busca genérica: o caminho no __NEXT_DATA__ pode mudar sem aviso."""
    if isinstance(node, dict):
        if "lastUpdateTime" in node and _to_float(node.get("last")):
            return node
        for v in node.values():
            b = _inv_price_block(v)
            if b:
                return b
    elif isinstance(node, list):
        for v in node:
            b = _inv_price_block(v)
            if b:
                return b
    return None

def _fetch_cds_investing():
    """Fallback do CDS: SSR da página do instrumento no Investing.com —
    JSON embutido no __NEXT_DATA__ do HTML (urllib puro, sem chave).
    BRGV5YUSAC=R em USD, EOD (isDelayed): cotação do fechamento do dia
    anterior, por isso o check no lastUpdateTime (epoch ms em string):
    acima de CDS_INV_MAX_AGE = feed congelado -> não renova o cache.
    lastClose do SSR vem corrompido (190.23 com last 121.08); fechamento
    anterior real = last - change. PD implícita na mesma fórmula do WGB:
    1 - exp(-s/(1-R)), rec. 40% (confere com o lastCdsDefaultProb deles)."""
    html = _http_get(INV_CDS_URL, {"User-Agent": BROWSER_UA,
                                   "Accept-Language": "en-US,en;q=0.9"},
                     timeout=20).decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("página sem __NEXT_DATA__")
    blk = _inv_price_block(json.loads(m.group(1)))
    if not blk:
        raise ValueError("SSR sem bloco de cotação")
    bps = _to_float(blk.get("last"))
    if not bps or bps <= 0 or bps > 100000:
        raise ValueError("sem preço válido")
    lut = _to_float(blk.get("lastUpdateTime"))       # epoch ms (string)
    if not lut:
        raise ValueError("sem lastUpdateTime")
    age = time.time() - lut / 1000.0
    if age > CDS_INV_MAX_AGE:
        raise ValueError(f"cotação velha ({age / 86400:.1f} d) — feed congelado")
    s = bps / 10000.0
    return {"bps": bps,
            "d_pct": _to_float(blk.get("changePcr")),
            "pd_pct": (1.0 - math.exp(-s / 0.6)) * 100.0,
            "dt": datetime.fromtimestamp(lut / 1000.0, timezone.utc
                                         ).strftime("%Y-%m-%d %H:%M UTC"),
            "src": "Investing.com"}

def fetch_cds_br():
    """CDS soberano de 5 anos do Brasil (bps) + variação 1 semana/mês/ano +
    PD implícita (40% de recuperação). Cadeia (v5.8): WGB intraday (POST
    com payload embutido -> payload reextraído da página do país) ->
    Investing.com (SSR, EOD ~1 dia, check no lastUpdateTime)."""
    errs = []
    for tag, payload in (("payload embutido", WGB_PAYLOAD),
                         ("payload da página", None)):
        try:
            if payload is None:
                payload = _wgb_payload_from_page()
            d = json.loads(_http_post_json(WGB_POST_URL,
                                           {"GLOBALVAR": payload},
                                           WGB_HEADERS))
            return {**_parse_cds_resp(d), "ts": time.time()}
        except Exception as e:
            errs.append(f"WGB {tag}: {e}")
    try:
        return {**_fetch_cds_investing(), "ts": time.time()}
    except Exception as e:
        errs.append(f"Investing.com: {e}")
    raise RuntimeError("CDS Brasil sem fonte (" + "; ".join(errs) + ")")

def collect_china(last):
    """REMOVIDO a pedido do usuário (2026-09-17): China/COMEX desativados.
    Mantém apenas o FX (necessário p/ derivar o BRL). Não busca Sina,
    Eastmoney, jijinhao, xxapi nem Yahoo-GC. Retorna None (sem sina_xau).
    Spot passa a usar goldprice.dev -> goldprice.org."""
    try:
        last["fx"] = fetch_fx()
    except Exception as e:
        log(f"FX awesomeapi (USD/CNY) indisponível: {e}")
    last.pop("china", None)
    return None

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

# -------------------- POPUP DE GRAFICO (v6.0, Canvas puro) --------------------
if tk is not None:
    class HistoryPopup(tk.Toplevel):
        """Popup com o grafico do ativo no periodo escolhido.

        Desenho em Canvas puro (sem matplotlib): linha + grade + rotulos.
        Busca em thread; botoes 7D/1M/3M/6M/1A conforme o suporte do ativo.
        """
        def __init__(self, app, key):
            super().__init__(app.root)
            self.app = app
            self.key = key
            meta = app._hist_meta(key)
            self.meta = meta
            self.days = 30 if 30 in meta["ranges"] else meta["ranges"][0]
            self.series = None
            self.src = ""
            self.note = None
            self._draw_job = None
            self.title(f"Grafico — {meta['title']}")
            try:
                self.configure(bg=BG)
                self.attributes("-type", "normal")
            except Exception:
                pass
            try:
                self.attributes("-topmost", True)
            except Exception:
                pass
            hdr = tk.Label(self, text=meta["title"], bg=BG, fg=TITLE,
                           font=("DejaVu Sans", 10, "bold"), anchor="w")
            hdr.pack(anchor="w", padx=12, pady=(10, 0))
            self.l_info = tk.Label(self, text="", bg=BG, fg=TXT_DIM,
                                   font=("DejaVu Sans", 8), anchor="w")
            self.l_info.pack(anchor="w", padx=12)
            brow = tk.Frame(self, bg=BG)
            brow.pack(anchor="w", padx=12, pady=(6, 0))
            self._btns = {}
            lbls = {7: "7D", 30: "1M", 90: "3M", 180: "6M", 365: "1A"}
            for d in meta["ranges"]:
                b = tk.Button(
                    brow, text=lbls.get(d, f"{d}D"),
                    bg=BORDER if d == self.days else "#1a2029",
                    fg="#0b0e12" if d == self.days else TXT_DIM,
                    activebackground=BORDER, relief="flat",
                    font=("DejaVu Sans", 8, "bold"), padx=10, pady=2,
                    command=lambda dd=d: self.set_range(dd))
                b.pack(side="left", padx=(0, 6))
                self._btns[d] = b
            self.canvas = tk.Canvas(self, width=560, height=300, bg="#0b0e12",
                                    highlightthickness=1,
                                    highlightbackground=BORDER)
            self.canvas.pack(fill="both", expand=True, padx=12, pady=8)
            self.l_status = tk.Label(self, text="carregando…", bg=BG, fg=TXT_DIM,
                                     font=("DejaVu Sans", 7), anchor="w")
            self.l_status.pack(anchor="w", padx=12, pady=(0, 10))
            self.canvas.bind("<Configure>", self._on_resize)
            self.bind("<Escape>", lambda e: self.destroy())
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass
            self._load()

        def set_range(self, days):
            if days == self.days and self.series:
                return
            self.days = days
            for d, b in self._btns.items():
                try:
                    b.configure(bg=BORDER if d == days else "#1a2029",
                                fg="#0b0e12" if d == days else TXT_DIM)
                except Exception:
                    pass
            self._load()

        def _on_resize(self, e):
            if not self.series:
                return
            if self._draw_job:
                try:
                    self.after_cancel(self._draw_job)
                except Exception:
                    pass
            self._draw_job = self.after(150, self._draw)

        def _load(self):
            try:
                self.l_status.config(text="carregando…")
            except Exception:
                pass
            key, days = self.key, self.days

            def work():
                try:
                    res = self.app.fetch_history_cached(key, days)
                    self.app.root.after(0, lambda: self._done(res, None))
                except Exception as ex:
                    self.app.root.after(0, lambda: self._done(None, ex))

            threading.Thread(target=work, daemon=True).start()

        def _done(self, res, err):
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            if err is not None or not res or not res.get("points"):
                try:
                    self.l_status.config(text=f"falhou: {err or 'sem dados'}")
                except Exception:
                    pass
                return
            self.series = res["points"]
            self.src = res.get("src") or ""
            self.note = res.get("note")
            p0, p1 = self.series[0][1], self.series[-1][1]
            chg = (p1 / p0 - 1.0) * 100.0 if p0 else 0.0
            try:
                cur = self.meta["fmt"](p1)
            except Exception:
                cur = f"{p1}"
            try:
                mn = self.meta["fmt"](min(v for _, v in self.series))
                mx = self.meta["fmt"](max(v for _, v in self.series))
            except Exception:
                mn = mx = ""
            arrow = "▲" if chg >= 0 else "▼"
            try:
                self.l_info.config(
                    text=(f"{cur}   {arrow} {abs(chg):.2f}% no periodo"
                          f"   ·   min {mn}   ·   max {mx}"),
                    fg=UP_COLOR if chg >= 0 else DOWN_COLOR)
            except Exception:
                pass
            st = self.src
            if self.note:
                st += f"  ·  {self.note}"
            try:
                self.l_status.config(text=st)
            except Exception:
                pass
            self._draw()

        def _draw(self):
            cv = self.canvas
            try:
                if not self.winfo_exists():
                    return
            except Exception:
                return
            pts = self.series or []
            W = max(200, cv.winfo_width() - 4)
            H = max(120, cv.winfo_height() - 4)
            cv.delete("all")
            if len(pts) < 2:
                cv.create_text(W // 2, H // 2, text="sem dados", fill=TXT_DIM)
                return
            vals = [v for _, v in pts]
            vmin, vmax = min(vals), max(vals)
            if vmax - vmin < 1e-9:
                vmin -= 1.0
                vmax += 1.0
            pad = (vmax - vmin) * 0.08
            vmin -= pad
            vmax += pad
            L, R, T, B = 64, 12, 12, 24

            def X(i):
                return L + (W - L - R) * i / (len(pts) - 1)

            def Y(v):
                return T + (H - T - B) * (1.0 - (v - vmin) / (vmax - vmin))

            yfmt = self.meta.get("yfmt", lambda x: f"{x:,.2f}")
            for g in range(5):
                y = T + (H - T - B) * g / 4
                cv.create_line(L, y, W - R, y, fill="#232830")
                vv = vmax - (vmax - vmin) * g / 4
                try:
                    lab = yfmt(vv)
                except Exception:
                    lab = ""
                cv.create_text(L - 6, y, text=lab, anchor="e", fill=TXT_DIM,
                               font=("DejaVu Sans", 7))
            idxs = dict.fromkeys([0, len(pts) // 2, len(pts) - 1])
            for i in idxs:
                dt = pts[i][0]
                lab = dt[5:] if len(dt) >= 10 else dt
                cv.create_text(X(i), H - 8, text=lab, fill=TXT_DIM,
                               font=("DejaVu Sans", 7))
            xy = []
            for i, (_, v) in enumerate(pts):
                xy += [X(i), Y(v)]
            cv.create_line(*xy, fill="#c9a227", width=2)
            cv.create_oval(xy[-2] - 3, xy[-1] - 3, xy[-2] + 3, xy[-1] + 3,
                           fill="#c9a227", outline="")
else:
    HistoryPopup = None


# ------------------------------- WIDGET ----------------------------------
class GoldWidget:
    def __init__(self, root):
        self.root = root
        self.stop = threading.Event()
        self._hist_cache = {}
        self._hist_keys = {}
        self._popups = {}
        self._press_xy = (0, 0)
        self._press_t = 0.0
        self._dragged = False
        self._click_job = None
        try:
            self._hist_log = load_hist_log()
        except Exception:
            self._hist_log = {}
        self.last = load_cache() or {}
        # REMOVIDO (2026-09-17): limpa resíduos de COMEX/China do cache antigo
        self.last.pop("china", None)
        self.last.pop("gc_fut", None)
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

        # REMOVIDO a pedido do usuário (2026-09-17): seção COMEX · FUTURO (GC=F)
        # REMOVIDO a pedido do usuário (2026-09-17): seção CHINA
        # (BOLSAS SGE/SHFE + REFERÊNCIA Base China Gold + BARRAS DE BANCO)

        # --------------- seção EUA · COMBUSTÍVEL (média de varejo) ---------
        self.us_frame = tk.Frame(self.frame, bg=BG)
        self.us_frame.pack(anchor="w", padx=12, fill="x")
        self._us_sig = None
        self._us_refs = []
        self.l_us_sub = tk.Label(self.frame, text="", bg=BG, fg=TXT_DIM,
                                 font=("DejaVu Sans", 7))
        self.l_us_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ---------------- seção BRASIL · CDS 5 ANOS (v5.7) ----------------
        self.cds_frame = tk.Frame(self.frame, bg=BG)
        self.cds_frame.pack(anchor="w", padx=12, fill="x")
        self._cds_sig = None
        self._cds_refs = []
        self.l_cds_sub = tk.Label(self.frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 7))
        self.l_cds_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # --------------- seção NYMEX · DIESEL HO=F (v6.1) -----------------
        self.ho_frame = tk.Frame(self.frame, bg=BG)
        self.ho_frame.pack(anchor="w", padx=12, fill="x")
        self._ho_sig = None
        self._ho_refs = []
        self.l_ho_sub = tk.Label(self.frame, text="", bg=BG, fg=TXT_DIM,
                                 font=("DejaVu Sans", 7))
        self.l_ho_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # -------------- seção BRENT · CRUDE (benchmark, v6.3) --------------
        self.brent_frame = tk.Frame(self.frame, bg=BG)
        self.brent_frame.pack(anchor="w", padx=12, fill="x")
        self._brent_sig = None
        self._brent_refs = []
        self.l_brent_sub = tk.Label(self.frame, text="", bg=BG, fg=TXT_DIM,
                                    font=("DejaVu Sans", 7))
        self.l_brent_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # --------------- seção RÚSSIA · CRUDE URALS (v6.2) ----------------
        self.urals_frame = tk.Frame(self.frame, bg=BG)
        self.urals_frame.pack(anchor="w", padx=12, fill="x")
        self._urals_sig = None
        self._urals_refs = []
        self.l_urals_sub = tk.Label(self.frame, text="", bg=BG, fg=TXT_DIM,
                                    font=("DejaVu Sans", 7))
        self.l_urals_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ----------------------- menu de botão direito ----------------------
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Atualizar agora", command=self.update_now)
        try:
            gmenu = tk.Menu(self.menu, tearoff=0)
            for _lbl, _hk in (
                    ("Ouro spot USD", "spot_usd"),
                    ("Ouro spot BRL", "spot_brl"),
                    ("Gasolina EUA", "fuel_gas"),
                    ("Diesel EUA", "fuel_diesel"),
                    ("CDS Brasil 5 anos", "cds_5y"),
                    ("Diesel NYMEX", "ho_f"),
                    ("Brent (benchmark)", "brent"),
                    ("Urals (Rússia)", "urals")):
                gmenu.add_command(label=_lbl,
                                  command=lambda k=_hk: self.open_history(k))
            self.menu.add_cascade(label="Ver grafico", menu=gmenu)
        except Exception:
            pass
        self.menu.add_checkbutton(label="Manter no topo",
                                  variable=self.var_top,
                                  command=self._toggle_top)
        self.menu.add_command(label="Encostar no canto", command=self.snap_corner)
        self.menu.add_separator()
        self.menu.add_command(label="Sair", command=self.quit)

        # ----------------------- arrastar com o mouse ------------------------
        self._drag_off = (0, 0)
        self._user_moved = False
        for w, hk in ((root, None), (self.frame, None), (self.l_title, None),
                         (self.l_usd, "spot_usd"),
                         (self.l_usd_var, "spot_usd"),
                         (self.l_usd_var_week, "spot_usd"),
                         (self.l_brl, "spot_brl"),
                         (self.l_brl_var, "spot_brl"),
                         (self.l_brl_var_week, "spot_brl"),
                         (self.l_sub, None),
                         (self.l_us_sub, None), (self.l_cds_sub, None),
                         (self.l_ho_sub, None), (self.l_brent_sub, None),
                         (self.l_urals_sub, None)):
            self._bind(w, hk)

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

    def _bind(self, w, hist_key=None):
        if hist_key:
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass
            try:
                self._hist_keys[str(w)] = hist_key
            except Exception:
                pass
        else:
            try:
                self._hist_keys.pop(str(w), None)
            except Exception:
                pass
        w.bind("<Button-1>",         self._on_press)
        w.bind("<B1-Motion>",        self._on_drag)
        w.bind("<ButtonRelease-1>",  self._on_release)
        w.bind("<Button-3>",         self._on_menu)
        w.bind("<Double-Button-1>",  self._on_double)

    @staticmethod
    def _china_hist_key(name):
        if name.startswith("SGE Au99.99"):
            return "sge_au9999"
        if name.startswith("SGE Au(T+D)"):
            return "sge_autd"
        if name.startswith("SHFE"):
            return "shfe"
        if name.startswith("Base China"):
            return "base_cn"
        return f"bank:{name}"

    @staticmethod
    def _us_hist_key(name):
        if name.startswith("Gasolina"):
            return "fuel_gas"
        return "fuel_diesel"

    def _hist_meta(self, key):
        if key.startswith("bank:"):
            return {"title": f"{key.split(':', 1)[1]} (R$/g) · ref. SGE",
                    "fmt": lambda v: f"R$ {fmt_brl(v)}/g",
                    "yfmt": lambda v: fmt_brl(v).split(",")[0],
                    "ranges": (7, 30, 90, 180, 365)}
        m = HIST_META.get(key)
        if m:
            return m
        return {"title": key, "fmt": lambda v: f"{v}",
                "yfmt": lambda v: f"{v}", "ranges": (7, 30)}

    def fetch_history_cached(self, key, days):
        now = time.time()
        ck = (key, int(days))
        hit = self._hist_cache.get(ck)
        if hit and now - hit[0] < HIST_CACHE_TTL:
            return hit[1]
        res = fetch_history(key, int(days), self._hist_log)
        self._hist_cache[ck] = (now, res)
        return res

    def open_history(self, key):
        if not key or tk is None:
            return
        try:
            w = self._popups.get(key)
            if w is not None and w.winfo_exists():
                w.lift()
                try:
                    w.focus_force()
                except Exception:
                    pass
                return
        except Exception:
            pass
        try:
            pop = HistoryPopup(self, key)
            self._popups[key] = pop
            pop.bind("<Destroy>",
                     lambda e, k=key: self._popups.pop(k, None))
        except Exception as e:
            log(f"falha ao abrir grafico {key}: {e}")

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

    def _cancel_click(self):
        if self._click_job:
            try:
                self.root.after_cancel(self._click_job)
            except Exception:
                pass
            self._click_job = None

    def _on_press(self, e):
        self._cancel_click()
        self._drag_off = (e.x_root - self.root.winfo_x(),
                          e.y_root - self.root.winfo_y())
        self._press_xy = (e.x_root, e.y_root)
        self._press_t = time.time()
        self._dragged = False

    def _on_drag(self, e):
        self._user_moved = True
        try:
            dx = e.x_root - self._press_xy[0]
            dy = e.y_root - self._press_xy[1]
            if dx * dx + dy * dy > 36:
                self._dragged = True
                self._cancel_click()
        except Exception:
            pass
        x = e.x_root - self._drag_off[0]
        y = e.y_root - self._drag_off[1]
        self.root.geometry(f"+{x}+{y}")

    def _on_release(self, e):
        try:
            if self._dragged:
                return
            if time.time() - self._press_t > 0.6:
                return
            dx = e.x_root - self._press_xy[0]
            dy = e.y_root - self._press_xy[1]
            if dx * dx + dy * dy > 36:
                return
            key = self._hist_keys.get(str(e.widget))
            if not key:
                return
            self._cancel_click()
            self._click_job = self.root.after(
                260, lambda: self.open_history(key))
        except Exception:
            pass

    def _on_double(self, e):
        self._cancel_click()
        self.snap_corner()

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

        # REMOVIDO a pedido do usuário (2026-09-17): China + COMEX GC=F
        # desativados. Apenas FX (p/ derivar BRL). Sem Sina/Eastmoney/
        # jijinhao/xxapi/Yahoo-GC.
        collect_china(self.last)
        fx = self.last.get("fx")
        self.last.pop("china", None)
        self.last.pop("gc_fut", None)

        # ---- EUA · combustível (AAA, diário): falha isolada + refetch 1/h ----
        uf = self.last.get("us_fuel")
        if _due("fuel", uf, FUEL_REFETCH):
            try:
                self.last["us_fuel"] = fetch_us_fuel()
                _cooldown_clear("fuel")
            except Exception as e:
                log(f"combustível EUA indisponível ({e}); mantendo cache")
                _cooldown("fuel", FUEL_REFETCH, str(e))
        # combustível: cache vence após 14 dias — evita preço velho na tela
        uf = self.last.get("us_fuel")
        if uf and time.time() - uf.get("ts", 0) > FUEL_MAX_AGE:
            self.last.pop("us_fuel", None)
            log("combustível EUA: cache >14 dias sem fonte; removido")

        # ---- Brasil · CDS 5 anos (v5.7): dado lento, cadência própria ----
        cds = self.last.get("cds_br")
        if _due("cds", cds, CDS_POLL_SECONDS):
            try:
                self.last["cds_br"] = fetch_cds_br()
                _cooldown_clear("cds")
            except Exception as e:
                log(f"CDS Brasil indisponível ({e}); mantendo cache")
                _cooldown("cds", CDS_POLL_SECONDS, str(e))
        cds = self.last.get("cds_br")
        if cds and time.time() - cds.get("ts", 0) > CDS_MAX_AGE:
            self.last.pop("cds_br", None)
            log("CDS Brasil: cache >7 dias sem fonte; removido")

        # ---- NYMEX · Diesel HO=F (v6.1): refetch no máx. 1/5min; falha
        #      isolada (Yahoo -> FXEmpire -> TradingEconomics -> cache) ----
        ho = self.last.get("ho_fut")
        if _due("ho", ho, HO_REFETCH):
            try:
                self.last["ho_fut"] = fetch_ho_future()
                _cooldown_clear("ho")
            except Exception as e:
                log(f"diesel NYMEX indisponível ({e}); mantendo cache")
                _cooldown("ho", HO_REFETCH, str(e))
        ho = self.last.get("ho_fut")
        if ho and time.time() - ho.get("ts", 0) > HO_MAX_AGE:
            self.last.pop("ho_fut", None)
            log("diesel NYMEX: cache >4 dias sem fonte; removido")

        # ---- Rússia · Crude Urals (v6.2): dado 1-2 dias atrasado,
        #      refetch no máx. 1/h; falha isolada (tabela -> freewidgets
        #      -> cache) ----
        ur = self.last.get("urals")
        if _due("urals", ur, URALS_REFETCH):
            try:
                self.last["urals"] = fetch_urals()
                _cooldown_clear("urals")
            except Exception as e:
                log(f"crude Urals indisponível ({e}); mantendo cache")
                _cooldown("urals", URALS_REFETCH, str(e))

        # ---- Brent · benchmark global (v6.3): intraday, refetch no
        #      máx. 1/5min; cadeia Yahoo -> FXEmpire -> OilPrice ->
        #      freewidgets -> cache; falha isolada das demais seções ----
        br = self.last.get("brent")
        if _due("brent", br, BRENT_REFETCH):
            try:
                self.last["brent"] = fetch_brent()
                _cooldown_clear("brent")
            except Exception as e:
                log(f"brent indisponível ({e}); mantendo cache")
                _cooldown("brent", BRENT_REFETCH, str(e))
        br = self.last.get("brent")
        if br and time.time() - br.get("ts", 0) > BRENT_MAX_AGE:
            self.last.pop("brent", None)
            log("brent: cache >4 dias sem fonte; removido")
        ur = self.last.get("urals")
        if ur and time.time() - ur.get("ts", 0) > URALS_MAX_AGE:
            self.last.pop("urals", None)
            log("crude Urals: cache >7 dias sem fonte; removido")

        usd_ok = False
        if usd:
            self.last["usd_price"] = usd["price"]
            self.last["usd_bid"]   = usd["bid"]
            self.last["usd_ask"]   = usd["ask"]
            self.last["usd_src"]   = "goldprice.dev"
            usd_ok = True
        else:           # última linha: goldprice.org (Sina removida a pedido do usuário)
            try:
                g = fetch_goldprice_org("USD")
                self.last["usd_price"] = g["price"]
                self.last["usd_bid"]   = None
                self.last["usd_ask"]   = None
                self.last["usd_src"]   = "goldprice.org"
                usd_ok = True
                log("goldprice.dev falhou; usando goldprice.org")
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

        if usd_ok or brl_ok:
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

        # Cache é salvo sempre.
        try:
            _L = self.last
            _H = self._hist_log
            if _L.get("usd_price"):
                log_hist_point(_H, "spot_usd", _L["usd_price"])
            if _L.get("brl_price"):
                log_hist_point(_H, "spot_brl", _L["brl_price"])
            _uf = _L.get("us_fuel") or {}
            if _uf.get("gas"):
                log_hist_point(_H, "fuel_gas", _uf["gas"])
            if _uf.get("diesel"):
                log_hist_point(_H, "fuel_diesel", _uf["diesel"])
            _cds = _L.get("cds_br") or {}
            if _cds.get("bps"):
                log_hist_point(_H, "cds_5y", _cds["bps"])
            _ho = _L.get("ho_fut") or {}
            if _ho.get("price"):
                log_hist_point(_H, "ho_f", _ho["price"])
            _ur = _L.get("urals") or {}
            if _ur.get("price"):
                log_hist_point(_H, "urals", _ur["price"])
            _br = _L.get("brent") or {}
            if _br.get("price"):
                log_hist_point(_H, "brent", _br["price"])
            save_hist_log(_H)
        except Exception as e:
            log(f"falha no log de historico: {e}")
        save_cache(self.last)
        self.root.after(0, self._set_spot_offline,
                        not (usd_ok or brl_ok))
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
                wait = POLL_SECONDS + random.uniform(0, 10)  # v6.4: jitter
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

        # REMOVIDO (2026-09-17): COMEX + China não renderizam mais
        self.last.pop("china", None)
        self.last.pop("gc_fut", None)

        # seção EUA · combustível (v5.4 local)
        self._render_us()
        self._render_us_sub()

        # seção BRASIL · CDS 5 anos (v5.7)
        self._render_cds()
        self._render_cds_sub()

        # seção NYMEX · diesel HO=F (v6.1)
        self._render_ho()
        self._render_ho_sub()

        # seção BRENT · crude benchmark (v6.3)
        self._render_brent()
        self._render_brent_sub()

        # seção RÚSSIA · crude Urals (v6.2)
        self._render_urals()
        self._render_urals_sub()

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
        return "GC=F (removido)"

    def _render_fut(self):
        return

    # --------------------- exibição · seção CHINA (v5) --------------------
    def _china_rows(self):
        return []

    def _render_china(self):
        return

    def _render_china_sub(self):
        return

    # ----------------- exibição · seção EUA · COMBUSTÍVEL (local) ---------
    def _us_rows(self):
        d = self.last.get("us_fuel") or {}
        rows = []
        if d.get("gas") or d.get("diesel"):
            rows.append((("h", "── EUA · COMBUSTÍVEL (VAREJO · DIÁRIO) ──"),
                         None, None))
            if d.get("gas"):
                rows.append((("r", "Gasolina (regular)", True),
                             f"US$ {d['gas']:,.3f}/gal",
                             _chg_pct(d.get("gas"), d.get("gas_chg"))))
            if d.get("diesel"):
                rows.append((("r", "Diesel (nacional)", True),
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
                    _hk = self._us_hist_key(r[0][1])
                    for w in (ln, lp, lv):
                        self._bind(w, _hk)
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
        if d.get("day"):
            parts.append(f"diário {d['day']} · Δ vs ontem · "
                         f"{d.get('src', 'AAA')}")
        ts = d.get("ts")
        if ts:
            age = max(0, int(time.time() - ts))
            parts.append(f"atualizado há {age}s")
        self.l_us_sub.config(text=" · ".join(parts), fg=TXT_DIM)

    # ---------------- exibição · seção BRASIL · CDS 5 ANOS (v5.7) ----------
    def _cds_rows(self):
        """Linhas: ((tipo, nome), preço_str, pct|None, sufixo_pct).
        pct aqui é variação de 1 SEMANA (dado do WGB)."""
        d = self.last.get("cds_br") or {}
        rows = []
        if d.get("bps"):
            rows.append((("h", "── BRASIL · RISCO SOBERANO (CDS) ──"),
                         None, None, None))
            w = d.get("w_pct")
            suf = " 1s"
            if w is None and d.get("d_pct") is not None:
                w = d["d_pct"]          # Investing é EOD: só há variação do dia
                suf = " 1d"
            rows.append((("r", "CDS 5 anos"),
                         f"{fmt_bps(d['bps'])} bps",
                         w, suf))
            pd = d.get("pd_pct")
            if pd:
                rows.append((("r", "PD implícita (rec. 40%)"),
                             f"{pd:.2f}%".replace(".", ","), None, None))
        return rows

    def _render_cds(self):
        rows = self._cds_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._cds_sig:
            for w in self.cds_frame.winfo_children():
                w.destroy()
            self._cds_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.cds_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._cds_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.cds_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.cds_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.cds_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, "cds_5y")
                    self._cds_refs.append(("r", ln, lp, lv))
                grid += 1
            self.cds_frame.columnconfigure(0, weight=1)
            self._cds_sig = sig

        for ref, r in zip(self._cds_refs, rows):
            if ref[0] == "h":
                continue
            _, lp, lv = ref[1], ref[2], ref[3]
            price_str, pct, suf = r[1], r[2], r[3]
            lp.config(text=price_str, fg=TXT_USD)
            if pct is None:
                lv.config(text="")
            else:
                lv.config(text=f"{fmt_pct(pct)}{suf}",
                          fg=UP_COLOR if pct >= 0 else DOWN_COLOR)

    def _render_cds_sub(self):
        d = self.last.get("cds_br") or {}
        parts = []
        if d.get("dt"):
            parts.append(f"{d.get('src') or 'WGB'} {d['dt']}")
        ts = d.get("ts")
        if ts:
            age = max(0, int(time.time() - ts))
            parts.append(f"há {age}s")
            if age > CDS_POLL_SECONDS * 2:
                parts.append("(cache)")
        self.l_cds_sub.config(text=" · ".join(parts), fg=TXT_DIM)

    # ---------------- exibição · seção NYMEX · DIESEL HO=F (v6.1) ----------
    def _ho_label(self, rec=None):
        """Rótulo da linha: 'HO=F · nov/26' (+ ' · (cache)' após FUT_STALE).
        Mês vem do Yahoo (shortName 'Heating Oil Nov 26') ou do FXEmpire
        (futuresMonth 'Nov 2026'); sem mês, fica só 'HO=F'."""
        rec = rec or {}
        nome = "HO=F"
        month = rec.get("month") or ""
        if not month:
            parts = (rec.get("name") or "").split()
            if len(parts) >= 3:
                month = f"{parts[-2]} {parts[-1]}"
        pm = month.split()
        if len(pm) == 2 and pm[0] in MONTH_PT:
            yr = pm[1][-2:] if len(pm[1]) == 4 else pm[1]
            nome += f" · {MONTH_PT[pm[0]]}/{yr}"
        elif month:
            nome += f" · {month}"
        if rec.get("ts") and time.time() - rec["ts"] > FUT_STALE:
            nome += " · (cache)"
        return nome

    def _ho_rows(self):
        d = self.last.get("ho_fut") or {}
        rows = []
        if d.get("price"):
            rows.append((("h", "── NYMEX · DIESEL (HO=F · ATACADO) ──"),
                         None, None))
            rows.append((("r", self._ho_label(d)),
                         f"US$ {d['price']:,.3f}/gal",
                         d.get("pct")))
        return rows

    def _render_ho(self):
        rows = self._ho_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._ho_sig:
            for w in self.ho_frame.winfo_children():
                w.destroy()
            self._ho_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.ho_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._ho_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.ho_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.ho_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.ho_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, "ho_f")
                    self._ho_refs.append(("r", ln, lp, lv))
                grid += 1
            self.ho_frame.columnconfigure(0, weight=1)
            self._ho_sig = sig

        for ref, r in zip(self._ho_refs, rows):
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

    def _render_ho_sub(self):
        d = self.last.get("ho_fut") or {}
        parts = []
        if d.get("price"):
            # escala US$/barril (x42) — como o gráfico da foto cotava
            parts.append(f"front-month · US$ {fmt_usd(d['price'] * 42)}/bbl")
            if d.get("oi"):
                parts.append(f"OI {d['oi']:,.0f}")
            if d.get("vendor_ts"):
                parts.append(str(d["vendor_ts"]).replace("T", " ")[:16] + "Z")
        ts = d.get("ts")
        if ts:
            parts.append(f"{d.get('src', '?')} há {max(0, int(time.time() - ts))}s")
        self.l_ho_sub.config(text=" · ".join(parts), fg=TXT_DIM)

    # ------------- exibição · seção BRENT · CRUDE (v6.3) --------------------
    def _brent_label(self, rec=None):
        """Rótulo da linha: 'BZ=F · nov/26' (+ ' · (cache)' após
        FUT_STALE). Mês vem do shortName do Yahoo (ex.: 'Brent Crude Oil
        Nov 26'); CFD da FXEmpire não traz mês -> fica só 'BZ=F'."""
        rec = rec or {}
        nome = "BZ=F"
        parts = (rec.get("name") or "").split()
        if len(parts) >= 3 and parts[-2] in MONTH_PT:
            nome += f" · {MONTH_PT[parts[-2]]}/{parts[-1]}"
        if rec.get("ts") and time.time() - rec["ts"] > FUT_STALE:
            nome += " · (cache)"
        return nome

    def _brent_rows(self):
        d = self.last.get("brent") or {}
        rows = []
        if d.get("price"):
            rows.append((("h", "── BRENT · CRUDE (BENCHMARK) ──"), None, None))
            rows.append((("r", self._brent_label(d)),
                         f"US$ {fmt_usd(d['price'])}/bbl",
                         d.get("pct")))
        return rows

    def _render_brent(self):
        rows = self._brent_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._brent_sig:
            for w in self.brent_frame.winfo_children():
                w.destroy()
            self._brent_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.brent_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._brent_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.brent_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.brent_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.brent_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, "brent")
                    self._brent_refs.append(("r", ln, lp, lv))
                grid += 1
            self.brent_frame.columnconfigure(0, weight=1)
            self._brent_sig = sig

        for ref, r in zip(self._brent_refs, rows):
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

    def _render_brent_sub(self):
        d = self.last.get("brent") or {}
        parts = []
        if d.get("price"):
            if d.get("high") is not None and d.get("low") is not None:
                parts.append(f"dia {d['low']:.2f}-{d['high']:.2f}")
            if d.get("delay"):
                parts.append(f"delay {d['delay']}")
            if d.get("day"):
                parts.append(f"dado {d['day']}")
        ts = d.get("ts")
        if ts:
            parts.append(f"{d.get('src', '?')} há {max(0, int(time.time() - ts))}s")
            if time.time() - ts > BRENT_REFETCH * 2:
                parts.append("(cache)")
        self.l_brent_sub.config(text=" · ".join(parts), fg=TXT_DIM)

    # --------------- exibição · seção RÚSSIA · CRUDE URALS (v6.2) ----------
    def _urals_rows(self):
        d = self.last.get("urals") or {}
        rows = []
        if d.get("price"):
            rows.append((("h", "── RÚSSIA · CRUDE URALS ──"), None, None))
            rows.append((("r", "Urals (FOB)"),
                         f"US$ {fmt_usd(d['price'])}/bbl",
                         d.get("pct")))
        return rows

    def _render_urals(self):
        rows = self._urals_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._urals_sig:
            for w in self.urals_frame.winfo_children():
                w.destroy()
            self._urals_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.urals_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._urals_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.urals_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.urals_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.urals_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, "urals")
                    self._urals_refs.append(("r", ln, lp, lv))
                grid += 1
            self.urals_frame.columnconfigure(0, weight=1)
            self._urals_sig = sig

        for ref, r in zip(self._urals_refs, rows):
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

    def _render_urals_sub(self):
        d = self.last.get("urals") or {}
        parts = []
        if d.get("price"):
            if d.get("delay"):
                parts.append(f"avaliação spot · delay {d['delay']}")
            if d.get("day"):
                parts.append(f"dado {d['day']}")
        ts = d.get("ts")
        if ts:
            parts.append(f"{d.get('src', '?')} há {max(0, int(time.time() - ts))}s")
            if time.time() - ts > URALS_REFETCH * 2:
                parts.append("(cache)")
        self.l_urals_sub.config(text=" · ".join(parts), fg=TXT_DIM)

    def _tick(self):
        if self.stop.is_set():
            return
        self._render_sub()
        self._render_us_sub()
        self._render_cds_sub()      # reavalia idade/cache do CDS
        self._render_ho_sub()       # reavalia idade/cache do HO=F
        self._render_brent_sub()    # reavalia idade/cache do Brent
        self._render_urals_sub()    # reavalia idade/cache do Urals
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

    collect_china(last)
    print("Sina/China/COMEX GC=F: REMOVIDOS a pedido do usuário (sem busca)")

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
        chg_s = f" (Δ dia: {', '.join(chgs)})" if chgs else ""
        print(f"US FUEL [{f.get('src', 'AAA')}]: "
              f"{' · '.join(precos)} (dia {f.get('day')}){chg_s}")
    except Exception as e:
        print(f"US FUEL: FALHOU ({e})")

    try:
        c = fetch_cds_br()
        last["cds_br"] = c
        vars_ = []
        for lbl, k in (("1d", "d_pct"), ("1s", "w_pct"),
                       ("1m", "m_pct"), ("1a", "y_pct")):
            if c.get(k) is not None:
                vars_.append(f"{lbl} {c[k]:+.2f}%")
        pd_s = (f" · PD implícita {c['pd_pct']:.2f}%".replace(".", ",")
                if c.get("pd_pct") else "")
        print(f"CDS BR 5Y [{c.get('src', 'WGB')}]: {c['bps']:.2f} bps "
              f"({', '.join(vars_)}){pd_s} — {c.get('dt', '')}")
    except Exception as e:
        print(f"CDS BR 5Y: FALHOU ({e})")

    try:
        h = fetch_ho_future()
        last["ho_fut"] = h
        extra = []
        if h.get("pct") is not None:
            extra.append(f"{h['pct']:+.2f}%")
        if h.get("oi"):
            extra.append(f"OI {h['oi']:,.0f}")
        if h.get("month"):
            extra.append(f"contrato {h['month']}")
        print(f"NYMEX DIESEL [{h['src']}]: {h['price']:.4f} US$/gal "
              f"(= US$ {h['price'] * 42:,.2f}/bbl · {', '.join(extra)})")
    except Exception as e:
        print(f"NYMEX DIESEL: FALHOU ({e})")

    try:
        b = fetch_brent()
        last["brent"] = b
        extra = []
        if b.get("pct") is not None:
            extra.append(f"{b['pct']:+.2f}%")
        if b.get("day_chg") is not None:
            extra.append(f"Δ {b['day_chg']:+.2f}")
        if b.get("delay"):
            extra.append(f"delay {b['delay']}")
        ref = b.get("day") or str(b.get("vendor_ts") or "").replace("T", " ")[:16]
        print(f"BRENT [{b['src']}]: {b['price']:,.2f} US$/bbl "
              f"({', '.join(extra) if extra else '—'} · dado {ref or '?'})")
    except Exception as e:
        print(f"BRENT: FALHOU ({e})")

    try:
        u = fetch_urals()
        last["urals"] = u
        extra = []
        if u.get("pct") is not None:
            extra.append(f"{u['pct']:+.2f}%")
        if u.get("day_chg") is not None:
            extra.append(f"Δ {u['day_chg']:+.2f}")
        if u.get("delay"):
            extra.append(f"delay {u['delay']}")
        print(f"CRUDE URALS [{u['src']}]: {u['price']:,.2f} US$/bbl "
              f"({', '.join(extra) if extra else '—'} · dado {u.get('day', '?')})")
    except Exception as e:
        print(f"CRUDE URALS: FALHOU ({e})")

    print("\nCHINA/COMEX: removidos a pedido do usuário")
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

    log("iniciando widget (v6.5: COMEX GC=F + China removidos a pedido do usuario)")
    root = tk.Tk()
    GoldWidget(root)
    root.mainloop()
    log("widget encerrado")
    return 0

if __name__ == "__main__":
    sys.exit(main())
