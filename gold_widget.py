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
 v6.6 (ESTA VERSAO, a pedido do usuário):
     * NOVO — seção "FERTILIZANTE · UREIA", 2 linhas em US$/t:
         - "Uréia (spot intl.)"  : diário. O TE espelha o granular FOB
           GOLFO EUA (conferido: TE 460.00 == futuro CBOT UFV1! 460.0 no
           mesmo dia; por isso o rótulo não fala "Oriente Médio").
         - "Uréia CFR Brasil"    : futuro CBOT/CME "Urea (Granular) CFR
           Brazil" (UFB=F) — preço da ureia chegando no porto brasileiro.
     * Cadeias de fallback (cada fonte com cooldown próprio, igual v6.4):
         - spot : TradingEconomics (scrape market_last, mesmo scraper do
                  HO=F) -> TradingView scanner (POST JSON público, contínuo
                  CBOT:UFV1! — a MESMA base do TE) -> World Bank Pink Sheet
                  (xlsx mensal parseado com stdlib: zip + XML; série "Urea"
                  f.o.b. Oriente Médio, US$/mt — BASE DIFERENTE, por isso o
                  rodapé mostra "mensal") -> cache 14d.
         - CFR  : Yahoo UFB=F (chart API, q1 -> q2 em 429) -> TradingView
                  (CBOT:UFB1!) -> cache 14d.
         - Investigações que MORRERAM no teste (não viram degrau): CEPEA
           (sem indicador de ureia), FMI/PCPS (não tem ureia), FRED (só
           índice PPI), Investing/Barchart/CME (403/challenge), DBnomics
           (sem PCPS). Pink Sheet: a URL do xlsx muda de "safra" p/ safra
           -> descobre na página oficial (fallback: URL conhecida).
     * Refetch no máx. 1/h (dado diário; martelada não adianta); cooldown
       por fonte + por seção; cache vence em 14 dias.
      * Grafico no clique: ureia spot usa o Pink Sheet (mensal: 1M/3M/6M/1A;
        janela < ~2 meses cai no log local); CFR Brasil so tem o log local
        (1M). Menu "Ver grafico" ganhou as duas entradas. Falha isolada.
 v6.7 (ESTA VERSAO, a pedido do usuário):
      * NOVO — seção "ENXOFRE · SPOT CN": enxofre elemental (granular,
        spot da China — NÃO existe público em US$/t: Pink Sheet SEM série
        sulfur (conferido no xlsx), IMF/FRED/Yahoo/OilPrice/Investing
        sem, futuro não tem em bolsa nenhuma). As DUAS fontes vivas
        publicam CNY/t e espelham o MESMO mercado (conferido: SunSirs
        09-16 = 7704.00 == fech. anterior do TE):
          - TradingEconomics /commodity/sulfur (scrape market_last) [1º]
          - SunSirs EN prodetail-427 (tabela diária com 6 dias; o site
            tem anti-bot JS que seta o cookie HW_CHECK=<hash> e
            recarrega — replicado com urllib em 2 GETs)      [2º]
          - cache local, "(cache)" após 2h, expira em 14 dias.
      * Exibição em US$/t: price CNY ÷ USDCNY (USDCNY = USDBRL ÷ CNYBRL,
        3 fontes via fetch_fx). Câmbio velho (>FX_MAX_AGE) = mostra o
        CNY/t cru (rodapé avisa). Log do gráfico SÓ em US$/t (escala
        consistente; CNY cru não entra no histórico).
      * Gráfico no clique: 7D = tabela do SunSirs (6 pontos reais,
        convertidos com o USDCNY de agora, anotado no rodapé); 1M+
        = log local. Falha isolada das demais seções.
 v6.8 (ESTA VERSAO, a pedido do usuário):
      * NOVO — seção "CHINA · CRUDE SC (XANGAI)": futuro de crude da INE
        (Shanghai International Energy Exchange, o "Shanghai oil"), CNY/bbl
        exibido em US$/bbl. Investigação ao vivo (2026-09-17):
          - Yahoo NÃO tem SC=F (404 validado contra BZ=F 200 na mesma rota)
          - TradingView scanner não cobre futuros da INE (0 resultados)
          - SunSirs "Crude oil" (prodetail-1127) é o fechamento do BRENT em
            US$/bbl (105,83 == BZ=F), base errada p/ o SC -> fora
        Cadeia (cooldown por fonte, padrão v6.4):
          - Sina nf_SC0 [principal]: realtime-ish (sessão noturna 21:00-
            02:30 BJT); f[8] last, f[27] 昨结算 (settlement). PEGADINHA:
            f[10] (805,0) é o LIMITE-UP — nunca usar como fechamento
          - Eastmoney futsseapi /static/142_scm_qt (p vs j settlement)
          - Eastmoney push2delay 142.scm (f43/10, tick 0.1 CNY; o f170
            calcula vs limite-up -> NÃO serve como pct; degrau sem pct)
          - cache local, "(cache)" após FUT_STALE (10 min), expira 4 dias
        Variação do dia = convenção chinesa (vs settlement anterior, hoje
        -0,94%); Sina e futsseapi batem entre si. Conversão US$/bbl SÓ com
        USDCNY fresco (padrão do enxofre); sem câmbio: CNY/bbl cru.
        Gráfico no clique: kline diário 142.scm convertido ÷USDCNY de hoje,
        fallback no log local. Falha isolada das demais seções.
  v6.9 (ESTA VERSAO, a pedido do usuário):
      * NOVO — seção "EMIRADOS · CRUDE MURBAN": preço do Murban (blend de
        exportação de Abu Dhabi, precificado pela ADNOC; benchmark asiático
        oficial desde a ICE Futures Abu Dhabi). US$/bbl com variação do dia.
        Investigação ao vivo (2026-09-17): Yahoo NÃO tem MU=F/MOF=F/MURBAN
        (404/Not Found validado), TV scanner sem o ativo (0 resultados,
        testados ICEEUR:MURBAN/MOF1!/ADNOC:MURBAN1!), FXEmpire 404 e
        TradingEconomics /commodity/murban SEM cotação (página sem
        market_last). O Murban vive no OilPrice.com, mesma infra do Urals:
          - oil-price-charts: linha data-name 'Murban-Crude' (blend_id
            4464; GET puro; avaliação c/ delay de minutos — conferido:
            16-Minute Delay)                          [principal]
          - /freewidgets/json_get_oilprices (blend_id=4464; CSRF +
            X-Requested-With, como no Urals/Brent)    [fallback 1]
          - cache local, etiqueta "(cache)", expiração em 7 dias
            (padrão Urals: avaliação com atraso).
      * Refetch no máx. 1/h (dado de avaliação; martelada não adianta).
        Cooldown por fonte + por seção (padrão v6.4). A tabela do
        OilPrice.com agora serve Urals + Brent + Murban (cache 2 min já
        existente evita request duplicado entre as três seções).
      * Gráfico no clique (7D/1M/3M/6M/1A): séries do freewidgets (mesmos
        períodos do Urals: 4=1M, 6=3M, 5=1A), com fallback no log local.
        Falha isolada das demais seções.
  v7.0 (ESTA VERSAO, a pedido do usuário):
      * URALS com delay HALVO: investigação ao vivo (17/09/2026) achou a
        MESMA avaliação spot republicada em T+1 (o OilPrice.com repassa
        T+2 — conferido no mesmo instante: OilPrice 111.77/stamp 15-09
        vs TE e minfin 121.61/16-09). Cadeia nova, cada fonte com
        cooldown próprio (padrão v6.4):
          - TradingEconomics /commodity/urals-oil (scrape market_last,
            o MESMO scraper do HO=F/ureia/sulfur; data real do dado
            parseada do resumo '... USD/Bbl on September 16, 2026')
                                                        [1º, T+1]
          - minfin.com.ua /markets/oil/urals/ (tabela diária dd.mm.yyyy,
            GET puro sem chave, decimal com vírgula)    [2º, T+1]
          - OilPrice.com tabela (GET, como antes)        [3º, T+2]
          - OilPrice.com freewidgets (CSRF + XHR)        [4º, T+2]
        O delay do rodapé agora vem da DATA REAL do dado (diff em dias),
        não de texto fixo da fonte.
      * Investigação que MORREU (não viram degrau): Investing RU congelado
        desde 25/02/2026; CBR /hd_base/urals/ = 404 (série diária retirada
        do ar); SPIMEX (bolsa física/futuro FOB Primorsk, cotação de bolsa
        com 15 min de delay, em RUB) geo-bloqueia fora da Rússia (HTTP 000
        e transport error testados); ProFinance sem Urals; FRED/EIA/IMF/
        Pink Sheet mensais. Tempo real verdadeiro exige terminal pago
        (Bloomberg/Reuters/Argus/Platts).
  v7.1 (a pedido do usuário):
      * NOVO — janela REDIMENSIONÁVEL: arrastar a borda/canto invisível
        (6px nas bordas, 14px nos cantos; cursor muda por direção; nada
        aparece na UI). Resize DIRECIONAL: bordas oeste/norte movem a
        janela e ancoram o lado oposto (clamp reposiciona junto). Mínimo
        200x150 ("só o título visível"), máximo = tela. O TEXTO NÃO
        ESCALA: o conteúdo só reflowa.
      * NOVO — rolagem OCULTA: todo o conteúdo vive num frame interno
        dentro de um Canvas (body). SEM scrollbar na UI; quando o
        conteúdo não couber, a roda do mouse rola (wheel p/ vertical,
        Shift+wheel p/ horizontal; 1 passo = 1/10 da janela). Sem
        overflow: wheel ignorado e view presa no topo. Bind no toplevel
        cobre os labels criados dinamicamente; popups de gráfico (outro
        Toplevel) não são afetados.
      * NOVO — tamanho PERSISTENTE: last["win"] = {w,h} no cache normal
        (save_cache atômico já existente); restaurado no boot com clamp
        de tela. "Encostar no canto" (menu/duplo-clique) respeita o
        tamanho escolhido.
      * Nota de implementação: alças de resize são Frames translúcidos
        (bg igual ao fundo) filhos do frame da borda, com nome Tk
        explícito (edge_r/l/b/t, grip_se/sw/ne/nw) para debug/hit-test;
        guardas _resizing nos handlers de arraste (bindtags do toplevel
        disparavam o mover-janela junto com o resize).
 v7.2 (ESTA VERSAO, a pedido do usuário):
      * NOVO — seção "COBRE · COMEX (HG=F)": futuro contínuo do cobre
        (benchmark global do metal, US$/lb), cotação intraday com
        variação vs fechamento anterior. Posição: logo abaixo do
        OURO · SPOT (metal junto de metal).
      * Cadeia (cada fonte com cooldown próprio, padrão v6.4):
          - Yahoo HG=F (chart API, q1 -> q2 em 429)      [principal]
          - FXEmpire /commodities/copper (blob react-query do SSR;
            marker "vendorSymbol":"HG" único na página; quote direto no
            data, NÃO em prices[...] como o Brent). O top-level espelha
            o contrato MAIS LÍQUIDO (dez/26, OI 171.866 — conferido ao
            vivo; o front set/26 tem OI 1.363), por isso NÃO usamos o
            front-pick do HO=F: aqui o benchmark É o mais ativo.
            Mesma base do TE (conferido no mesmo instante: FXE 6.836
            vs TE 6.8306)                            [fallback 1]
          - TradingEconomics /commodity/copper (scrape market_last,
            mesmo scraper do HO=F/ureia/sulfur/urals) [fallback 2]
          - cache local, etiqueta "(cache)" após FUT_STALE (10 min) e
            expiração em 4 dias (cobre o fim de semana sem pregão).
      * Refetch no máx. 1/5min (intraday, igual HO/Brent; o throttle
        global de 1,5s do Yahoo e o 429 = falha dupla já protegem o
        HG=F, que disputa o mesmo IP do GC/HO/BZ). Gráfico no clique:
        série diária do Yahoo HG=F (7D-1A), fallback no log local.
        Falha isolada das demais seções.
  v7.3 (ESTA VERSAO, a pedido do usuário):
      * NOVO — linha "CU0 · SHFE" dentro da seção COBRE: o cobre da CHINA
        (contrato principal contínuo CU0 = 沪铜主连 da Shanghai Futures
        Exchange, CNY/t com tick 10; ~US$ 7.1/lb hoje vs US$ 6.8/lb do
        COMEX). MESMA UNIDADE da linha de cima (US$/lb) p/ comparar o
        prêmio SHFE de graça. Investigação ao vivo (2026-09-22): a Sina
        CU0 == CU2611 (contrato principal REAL, flag is-main=1; OI 23.3k)
        e o EM 113.cum é a série EMENDADA (nível ~0,4% diferente do
        contrato cru, pct próprio consistente). Cadeia (mesma infra
        validada do SC v6.8; cada fonte com cooldown próprio):
          - Sina nf_CU0 [principal]: realtime-ish (sessão noturna 21:00-
            01:00 BJT; a cotação "do dia" entra com a data do pregão
            seguinte); f[8]=último, f[27]=昨结算 (settlement — base da
            variação do dia, convenção chinesa)
          - Eastmoney futsseapi 113_cum_qt [2º]: p=último, j=昨结算
          - Eastmoney push2delay 113.cum [3º]: f43 na escala f152 (preço
            puro — o f170 calcula vs limite, não serve pct)
          - cache local, "(cache)" após FUT_STALE (10 min), expira 4 dias
        US$/lb = CNY/t ÷ USDCNY ÷ 2204.62262 (lb/t) — USDCNY FRESH do
        fetch_fx (3 fontes, ≤ 15 min); sem câmbio fresco: CNY/t cru
        (nunca com taxa velha). Var % calculada em CNY (idêntica em US$:
        a taxa é constante dentro do dia). Gráfico no clique: kline
        diário 113.cum (== Sina kline CU0, conferido: fech. 22/09
        111.320 nas duas) ÷ USDCNY ÷ lb, fallback no log local (US$/lb
        desde a v7.3). Falha isolada das demais seções.
  v8.0 (ESTA VERSAO, a pedido do usuário):
      * NOVO — seção "BRASIL · YIELD GOVERNO (NOMINAL)": curva nominal
        LTN/NTN em % a.a. (a do noticiário: 14,17% 10y). NÃO é a NTN-B
        real do WGB (7,38% 10y) — bases DIFERENTES, não misturam; o
        usuário escolheu SÓ a nominal. UMA linha exibida, com DROPDOWN
        ▾ para selecionar o vencimento (3m/6m/9m/1a/2a/3a/5a/8a/10a;
        seleção persiste no cache) + Δ do dia em PONTOS PERCENTUAIS
        (não % relativo — yield não se lê em % de %) + rodapé com a
        curva inteira. Posição: logo abaixo do CDS (Brasil c/ Brasil).
      * Cadeia (5 degraus, cooldown por fonte, padrão v6.4):
          - Investing tabela SSR /rates-bonds/brazil-government-bonds
            (GET puro; cada <tr id="pair_N"> tem pid-N-last, -last_close,
            -pc (Δ pp) e data epoch; vencimento do title 'Brazil
            10-Year' — o SLUG DISCORDA do título no 8y ('brazil-6-
            year-bond-yield' com title 'Brazil 8-Year'), por isso o
            título manda)                                [principal]
          - a mesma tabela no host m. (reserva de host)  [fallback 1]
          - TradingEconomics /brazil/government-bond-yield (SÓ 10y — os
            slugs 1y/2y/3y do TE são 404 genérico, validado; o Pchg do
            TE em títulos É Δ pp: -0.02 == '0.02 percentage points
            decrease' na própria descrição deles; data real do resumo
            '... eased to 14.17% on September 22, 2026')  [fallback 2;
            pulado quando o vencimento selecionado não é 10a]
          - Investing página do instrumento (SSR __NEXT_DATA__, mesmo
            padrão do CDS v5.8; bloco único com last/lastUpdateTime;
            EOD/delayed — last pode ser o fech. anterior) [fallback 3]
          - Investing API financialdata/historical (a MESMA do CDS
            v7.1; linha de HOJE da série diária — conferido vivo:
            1ª row do dia = 14.17)                        [fallback 4]
          - cache local 4d (cobre fds), "(cache)" após 2 refetches.
        pair IDs por vencimento fixados no código (capturados da
        tabela ao vivo 23/09/2026: 3M 1052514, 6M 1052515, 9M 24023,
        1Y 24024, 2Y 24025, 3Y 24026, 5Y 24027, 8Y 24028, 10Y 24029).
      * Gráfico no clique: série diária da API historical (7D/1M/3M/
        6M/1A), fallback no log local — que acumula TODOS os vencimentos
        do dropdown a cada ciclo. Δ em pp (não %). Falha isolada das
        demais seções.
  v8.1 (ESTA VERSAO, a pedido do usuário):
    * NOVO — seção "EUA · YIELD GOVERNO (TREASURY)": curva nominal UST
      em % a.a. (a do noticiário: 10y ~5,12%). Só a nominal — TIPS/real
      fica FORA (mesma regra da NTN-B no BR: bases não se misturam).
      Vencimentos padrão de mercado: 1m/3m/6m/1a/2a/3a/5a/7a/10a/20a/
      30a, MISTURANDO bills (≤1a, taxa de desconto), notes (2-10a) e
      bonds (20-30a) como o noticiário — com o tipo (bill/note/bond) no
      NOME do vencimento. UMA linha exibida, com DROPDOWN ▾ (seleção
      persiste no cache como 'us_yield_sel') + Δ do dia em PONTOS
      PERCENTUAIS + rodapé com a curva inteira. Posição: logo abaixo do
      yield BR (Brasil com EUA). Default: 10a.
    * Cadeia (6 degraus, cooldown por fonte, padrão v6.4; os nomes das
      fontes têm prefixo US p/ não colidir com o cooldown do BR):
          - Investing tabela SSR /rates-bonds/usa-government-bonds
            (o path dos EUA é 'usa-…', NÃO 'us-…'; cada <tr id="pair_N">
            tem pid-N-last, -pc (Δ pp) e -time; vencimento do title
            'United States 10-Year' no <a> — o 20y tem slug 'us-20-year-
            bond-yield' sem os pontos de 'u.s.-…' dos demais, por isso o
            título manda; 2m e 4m existem na tabela e ficam FORA da
            curva pedida)                                 [principal]
          - a mesma tabela no host m.                    [fallback 1]
          - TradingEconomics — SÓ os vencimentos com página própria
            validados 23/09/2026: 3m ('3-month-bill-yield'), 6m ('6-
            month-bill-yield'), 10a ('government-bond-yield' — o slug
            '10-year-bond-yield' do TE é 404), 20a ('20-year-bond-
            yield'), 30a ('30-year-bond-yield'); os demais são 404
            genérico                                        [fallback 2]
          - Investing página do instrumento (/rates-bonds/u.s.-10-year-
            bond-yield, SSR __NEXT_DATA__, padrão CDS)     [fallback 3]
          - Investing API financialdata/historical (linha de HOJE)  [4]
          - FRED DGS* (Treasury CMT oficial, EOD; curva inteira numa
            chamada fredgraph.csv: DGS1MO/DGS3MO/DGS6MO/DGS1/DGS2/
            DGS3/DGS5/DGS7/DGS10/DGS20/DGS30; completa o que os degraus
            de vencimento único não trouxeram, sem sobrescrever)  [5]
          - cache local 4d (cobre fds), "(cache)" após 2 refetches.
        pair IDs por vencimento fixados no código (capturados da tabela
        ao vivo 23/09/2026: 1M 23697, 3M 23698, 6M 23699, 1Y 23700,
        2Y 23701, 3Y 23702, 5Y 23703, 7Y 23704, 10Y 23705, 20Y 1161827,
        30Y 23706).
    * Gráfico no clique: série diária da API historical (7D/1M/3M/6M/1A)
      com fallback FRED e no log local (que acumula TODOS os vencimentos
      do dropdown a cada ciclo). Δ em pp. Falha isolada das demais seções.
  v8.2 (ESTA VERSAO, a pedido do usuário):
    * NOVO — seção "CÂMBIO · USD/BRL": linha visível com SÓ o valor do
      dólar em reais ("US$ 1 = R$ 5,1526", mid, 4 decimais pt-BR), estilo
      do spot do ouro. Posição: logo abaixo do OURO · SPOT. Não entra nas
      derivações (fetch_fx continua como estava, intacto).
    * fetch_usdbrl() SEPARADO com cadeia de 10 degraus — cada falha cai
      AUTOMATICAMENTE no próximo degrau, e se o próximo falhar cai em
      outro, até acabar; no fim cache 24h e senão "—". Mid = (compra+
      venda)/2 ou (bid+ask)/2; fonte de 1 número usa o número direto.
      Ordem validada ao vivo 24/09/2026 (intraday primeiro — o BCB/PTAX é
      fechamento DIÁRIO e fica ~0,5% atrás do intraday em horário de
      pregão; oficial entra como fallback):
          1. awesomeapi (bid/ask; /json/last/USD-BRL, reserva /json/all)
          2. Yahoo USDBRL=X (chart q2->q1; regularMarketPrice)
          3. TradingEconomics /brazil/currency (scrape market_last)
          4. floatrates (usd.json -> brl.rate)
          5. currency-api (pages.dev FRESCO -> jsDelivr, que fica preso
             na versão do pacote e serve cotação velha; reserva
             1/brl.usd)
          6. open.er-api.com (rates.BRL)
          7. frankfurter.dev (rates.BRL; .app redireciona p/ .dev)
          8. BCB SGS (10813 compra + 1 venda -> mid; api.bcb.gov.br)
          9. Olinda PTAX (CotacaoDolarDia -> CotacaoDolarPeriodo ->
             compra/venda -> mid)
         10. BCB SOAP www3 (getUltimoValorVO séries 1+10813 -> mid)
      Cooldown POR FONTE (padrão v6.4): fallback não anistia a fonte
      morta. Refetch 90s. Também sai no --dump. Falha isolada das demais
      seções.
  v8.3 (ESTA VERSAO, a pedido do usuário):
    * NOVO — BANDEJA DO SISTEMA (system tray): o widget agora SEMPRE inicia
      minimizado na bandeja (topo do GNOME, extensão AppIndicators ativa) e
      só aparece quando o usuário manda mostrar. Polling/cache/log seguem
      rodando em segundo plano mesmo com a janela oculta.
    * v8.3.1 — pump do loop GLib no _tick: o AppIndicator precisa do
      despacho GLib para manter o registro SNI vivo; sem bombear, o ícone
      sumia ~5s após o boot (set_status ACTIVE sozinho não segura). O pump
      é main_context_iteration(False) — só despacha o pendente, nunca
      bloqueia o Tk; falha aqui nunca quebra o widget.
    * Implementação: AyatanaAppIndicator3 via GI (pacote do sistema,
      gir1.2-ayatana-appindicator3 — zero dependência pip nova; stdlib do
      widget continua intacto). Ícone: círculo dourado gerado com Pillow
      (já instalado 10.2) em ~/.local/share/gold-widget/tray-gold.png,
      com fallback para ícone do tema se o Pillow/geração falhar.
    * Limitação REAL do Ayatana no GNOME (validada no ambiente): o clique
      no ícone SEMPRE abre o menu — não há sinal de clique-esquerdo para
      interceptar (por isso "clique alterna" virou item "Mostrar/Ocultar"
      no menu, que é 100% confiável). Label ao lado do ícone mostra o
      spot em BRL (R$/g, v8.4); título/tooltip mostra BRL + USD.
    * Menu da bandeja (Gtk, thread-safe via GLib.idle_add): Mostrar/Ocultar
      + Atualizar agora + Ver gráfico (mesmas entradas do menu da janela)
      + Sair. O menu da JANELA (botão direito) ganha "Minimizar p/ bandeja".
      Fechar/X continua encerrando (pedido do usuário: SÓ o item de menu
      minimiza). Flag de fuga --show inicia visível (debug). Se o Ayatana
      falhar por qualquer motivo, o app NUNCA quebra: loga e segue visível
      como antes, com o item de menu tornando-se no-op seguro.
  v8.4 (ESTA VERSAO, a pedido do usuário):
    * CORREÇÃO — label da BANDEJA agora em BRL (R$/g, "R$ 714,32/g",
      igual ao widget), não mais em USD. O USD só aparece no label se
      LITERALMENTE todos os fallbacks do BRL falharem (goldprice.dev +
      derivado USDxBRL + goldprice.org/BRL sem dado): aí mostra o USD
      temporário ("US$ 4.266,16") até o BRL voltar.
    * Tooltip/título da bandeja mantém USD+BRL mas INVERTE a ordem:
      BRL primeiro ("R$ 714,32/g · US$ 4,266.16").
    * Refresh da bandeja amarrado em TODO ciclo de poll (via
      _tray_refresh_soon no fim do _poll_once_impl) + tick de 5 s
      (_tray_refresh_tick) + _render: o valor da barra acompanha o
      widget periodicamente, como o usuário exigiu.
  Fonte principal do spot: goldprice.dev. Stdlib apenas (tkinter+urllib).
  """

import errno
import fcntl
import io
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
import xml.etree.ElementTree as ET
import zipfile
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

# ------------- CONFIG · USD/BRL (campo visível, v8.2) ---------------------
# Cadeia do campo "CÂMBIO · USD/BRL" (só o valor, mid). 10 degraus, cada
# falha cai no próximo e se o próximo falhar cai em outro. Intraday antes
# do BCB oficial (PTAX = fechamento diário, ~0,5% atrás do intraday em
# horário de pregão). Fontes gratuitas sem chave, validadas 24/09/2026.
USDBRL_REFETCH = 90                             # igual o poll do spot
USDBRL_MAX_AGE  = 24 * 3600                     # cache vale 24h se a cadeia cair
AAPI_USDBRL     = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
AAPI_ALL        = "https://economia.awesomeapi.com.br/json/all"
YAHOO_UBRL_Q2   = ("https://query2.finance.yahoo.com/v8/finance/chart/USDBRL=X"
                   "?range=1d&interval=5m")
YAHOO_UBRL_Q1   = ("https://query1.finance.yahoo.com/v8/finance/chart/USDBRL=X"
                   "?range=1d&interval=5m")
TE_USDBRL_URL   = "https://tradingeconomics.com/brazil/currency"
FLOATRATES_URL  = "https://www.floatrates.com/daily/usd.json"
FX_JSD_PAGES    = ("https://latest.currency-api.pages.dev/v1/currencies/usd.json")
FX_JSD_BRL_PG   = ("https://latest.currency-api.pages.dev/v1/currencies/brl.json")
FX_FRA          = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=BRL"
BCB_SGS_ULT     = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}"
                   "/dados/ultimos/1?formato=json")
OLINDA_DIA      = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
                   "CotacaoDolarDia(dataCotacao=@dataCotacao)"
                   "?@dataCotacao='{date}'&$format=json")
OLINDA_PER      = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
                   "CotacaoDolarPeriodo(dataInicial=@dataInicial,"
                   "dataFinalCotacao=@dataFinalCotacao)"
                   "?@dataInicial='{d0}'&@dataFinalCotacao='{d1}'&$format=json")
BCB_SOAP_URL    = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS"
SGS_COMPRA      = 10813                         # dólar comercial compra (PTAX)
SGS_VENDA       = 1                             # dólar comercial venda (PTAX)
STATE_DIR     = os.path.expanduser("~/.local/share/gold-widget")
CACHE_FILE    = os.path.join(STATE_DIR, "last_price.json")
LOG_FILE      = os.path.join(STATE_DIR, "widget.log")
# v8.4.1 — trava anti-instância-dupla: flock(LOCK_EX|LOCK_NB) neste arquivo.
# O lock morre com o processo (inclusive SIGKILL): NUNCA fica stale.
# SÓ a GUI segura o lock; --dump NUNCA trava (livre p/ teste/cron).
LOCK_FILE     = os.path.join(STATE_DIR, "widget.lock")
TRAY_ICON_FILE = os.path.join(STATE_DIR, "tray-gold.png")  # v8.3: ícone da bandeja
MARGIN        = 16                                 # distância da borda lateral
MARGIN_Y      = 40                                 # abaixo da barra do topo
TROY_OZ_GRAMS = 31.1034768                         # 1 onça troy em gramas
# v7.1 — janela redimensionável (arrastar borda/canto INVISÍVEL) + rolagem
# oculta (wheel, sem barra na UI) quando o conteúdo não couber. O texto NÃO
# muda de tamanho: a janela apenas revela/esconde conteúdo via rolagem.
MIN_W         = 200                                # largura mínima (só o título visível)
MIN_H         = 150                                # altura mínima
EDGE_PX       = 6                                  # espessura da área de resize (invisível)

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

# ------------- CONFIG · YIELD BRASIL NOMINAL (LTN/NTN, v8.0) -----------------
# Curva nominal do governo brasileiro (LTN/NTN, % a.a. — a que aparece no
# noticiário: 10y ~14%). Diferente da NTN-B real (WGB, 10y ~7,38%): bases
# não se misturam, o usuário escolheu SÓ a nominal. Cadeia (cada fonte com
# cooldown próprio, padrão v6.4):
#   1º Investing tabela SSR (curva inteira, intraday, host www)
#   2º Investing tabela SSR host m. (mesma página, host reserva)
#   3º TradingEconomics /brazil/government-bond-yield (SÓ o 10y; os
#      slugs 1y/2y/3y do TE são 404 genérico — validado 23/09/2026)
#   4º Investing página do instrumento (SSR __NEXT_DATA__, padrão CDS)
#   5º Investing API financialdata/historical (linha de hoje da série)
#   6º cache local (4d)
INV_BR_BONDS_URL   = "https://www.investing.com/rates-bonds/brazil-government-bonds"
INV_BR_BONDS_URL_M = "https://m.investing.com/rates-bonds/brazil-government-bonds"
TE_BR_YIELD_URL    = "https://tradingeconomics.com/brazil/government-bond-yield"
YIELD_MATS = {                  # vencimento -> pair id + slug (capturado 23/09/2026)
    "3m":  {"ordem": 0, "nome": "3 meses", "pair": "1052514", "slug": "brazil-3-month"},
    "6m":  {"ordem": 1, "nome": "6 meses", "pair": "1052515", "slug": "brazil-6-month"},
    "9m":  {"ordem": 2, "nome": "9 meses", "pair": "24023",   "slug": "brazil-9-month-bond-yield"},
    "1a":  {"ordem": 3, "nome": "1 ano",   "pair": "24024",   "slug": "brazil-1-year-bond-yield"},
    "2a":  {"ordem": 4, "nome": "2 anos",  "pair": "24025",   "slug": "brazil-2-year-bond-yield"},
    "3a":  {"ordem": 5, "nome": "3 anos",  "pair": "24026",   "slug": "brazil-3-year-bond-yield"},
    "5a":  {"ordem": 5.1, "nome": "5 anos", "pair": "24027",  "slug": "brazil-5-year-bond-yield"},
    "8a":  {"ordem": 6, "nome": "8 anos",  "pair": "24028",   "slug": "brazil-6-year-bond-yield"},
    "10a": {"ordem": 7, "nome": "10 anos", "pair": "24029",   "slug": "brazil-10-year-bond-yield"},
}
YIELD_DEFAULT   = "10a"
YIELD_LO        = 0.5                   # sanidade % a.a. (nominal nunca < 0,5)
YIELD_HI        = 35.0                  # teto (hist LTN 2015-16 ~16%)
YIELD_REFETCH   = 15 * 60               # intraday-ish: refetch no máx. 1/15min
YIELD_MAX_AGE   = 4 * 86400             # cache vence (4 dias; cobre fds)

# ------------- CONFIG · YIELD EUA NOMINAL (UST, v8.1) -------------------
# Curva nominal do Tesouro americano (bills/notes/bonds, % a.a. — a que
# aparece no noticiário: 10y ~5%). Só a nominal: TIPS/real fica FORA
# (mesma regra da NTN-B no BR). Bills (≤1a) são taxa de desconto e
# notes/bonds (2-30a) são coupon yield — misturados como no noticiário,
# com o tipo no NOME de cada vencimento. Cadeia (cada fonte com cooldown
# próprio, prefixo USYIELD p/ não colidir com o do BR):
#   1º Investing tabela SSR (curva inteira, intraday, host www)
#   2º Investing tabela SSR host m. (mesma página, host reserva)
#   3º TradingEconomics (SÓ 3m/6m/10a/20a/30a — validado 23/09/2026)
#   4º Investing página do instrumento (SSR __NEXT_DATA__, padrão CDS)
#   5º Investing API financialdata/historical (linha de hoje da série)
#   6º FRED DGS* (CMT oficial, EOD — completa a curva inteira)
#   7º cache local (4d)
INV_US_BONDS_URL   = "https://www.investing.com/rates-bonds/usa-government-bonds"
INV_US_BONDS_URL_M = "https://m.investing.com/rates-bonds/usa-government-bonds"
TE_US_YIELD_FMT    = "https://tradingeconomics.com/united-states/{slug}"
US_YIELD_MATS = {   # vencimento -> pair + slug Investing + série FRED + slug TE
    "1m":  {"ordem": 0,  "nome": "1 mês (bill)",   "pair": "23697",
            "slug": "u.s.-1-month-bond-yield",  "fred": "DGS1MO", "te": None},
    "3m":  {"ordem": 1,  "nome": "3 meses (bill)", "pair": "23698",
            "slug": "u.s.-3-month-bond-yield",  "fred": "DGS3MO",
            "te": "3-month-bill-yield"},
    "6m":  {"ordem": 2,  "nome": "6 meses (bill)", "pair": "23699",
            "slug": "u.s.-6-month-bond-yield",  "fred": "DGS6MO",
            "te": "6-month-bill-yield"},
    "1a":  {"ordem": 3,  "nome": "1 ano (bill)",   "pair": "23700",
            "slug": "u.s.-1-year-bond-yield",   "fred": "DGS1",   "te": None},
    "2a":  {"ordem": 4,  "nome": "2 anos (note)",  "pair": "23701",
            "slug": "u.s.-2-year-bond-yield",   "fred": "DGS2",   "te": None},
    "3a":  {"ordem": 5,  "nome": "3 anos (note)",  "pair": "23702",
            "slug": "u.s.-3-year-bond-yield",   "fred": "DGS3",   "te": None},
    "5a":  {"ordem": 6,  "nome": "5 anos (note)",  "pair": "23703",
            "slug": "u.s.-5-year-bond-yield",   "fred": "DGS5",   "te": None},
    "7a":  {"ordem": 7,  "nome": "7 anos (note)",  "pair": "23704",
            "slug": "u.s.-7-year-bond-yield",   "fred": "DGS7",   "te": None},
    "10a": {"ordem": 8,  "nome": "10 anos (note)", "pair": "23705",
            "slug": "u.s.-10-year-bond-yield",  "fred": "DGS10",
            "te": "government-bond-yield"},
    "20a": {"ordem": 9,  "nome": "20 anos (bond)", "pair": "1161827",
            "slug": "us-20-year-bond-yield",    "fred": "DGS20",
            "te": "20-year-bond-yield"},
    "30a": {"ordem": 10, "nome": "30 anos (bond)", "pair": "23706",
            "slug": "u.s.-30-year-bond-yield",  "fred": "DGS30",
            "te": "30-year-bond-yield"},
}
US_YIELD_DEFAULT = "10a"
US_YIELD_LO      = 0.0                  # UST nominal chegou ~0 em 2020 (piso BR 0,5 rejeitaria!)
US_YIELD_HI      = 20.0                 # teto de sanidade (hist moderno ≤ ~15%)
US_YIELD_REFETCH = 15 * 60              # intraday-ish: refetch no máx. 1/15min
US_YIELD_MAX_AGE = 4 * 86400            # cache vence (4 dias; cobre fds)

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

# ------------------- CONFIG · COBRE COMEX HG=F (v7.2) ------------------------
# Futuro cobre (High Grade) da COMEX — o benchmark global do cobre, em
# US$/lb. Cadeia (Yahoo -> FXEmpire -> TradingEconomics -> cache), todas
# sem chave; cada fonte com cooldown próprio (padrão v6.4):
#   - Yahoo: chart API do contínuo HG=F, igual GC=F/HO=F/BZ=F.
#   - FXEmpire: /commodities/copper — blob react-query no SSR, quote
#     DIRETO no data (marker "vendorSymbol":"HG" único; o Brent usa
#     prices[...] mas este é plano). O top-level espelha o contrato
#     MAIS LÍQUIDO (dez/26, OI 171.866; front set/26 OI 1.363 —
#     conferido ao vivo 22/09/2026), por isso NÃO se faz o front-pick
#     do HO: no cobre o benchmark é o contrato mais ativo, e o TE
#     (6.8306) confirma a MESMA base do FXE top (6.836).
#   - TradingEconomics: scrape market_last (mesmo scraper do HO=F/
#     ureia/sulfur/urals), referência CFD do contrato principal.
YAHOO_HG_URL    = ("https://query1.finance.yahoo.com/v8/finance/chart/HG=F"
                   "?interval=1d&range=5d")   # 5 barras: atual + anteriores
YAHOO_HG_URL_Q2 = ("https://query2.finance.yahoo.com/v8/finance/chart/HG=F"
                   "?interval=1d&range=5d")   # host reserva (mesma API)
FXE_COPPER_URL  = "https://www.fxempire.com/commodities/copper"
TE_COPPER_URL   = "https://tradingeconomics.com/commodity/copper"
HG_REFETCH      = 5 * 60               # intraday: refetch no máx. 1/5min
HG_MAX_AGE      = 4 * 86400            # cache vence (4 dias; cobre fds)
HG_USD_LO       = 0.5                  # sanidade US$/lb (hist ~1.9..6.9)
HG_USD_HI       = 20.0                 # teto folgado (~US$ 44k/t)

# ------------------- CONFIG · COBRE SHFE CU0 (China, v7.3) --------------------
# Cobre da CHINA: contrato principal contínuo CU0 (沪铜主连) da Shanghai
# Futures Exchange, cotado em CNY/t (tick 10 CNY). Sessão noturna 21:00-
# 01:00 BJT (a cotação "do dia" entra com a data do pregão seguinte).
# Cadeia (mesma infra validada do SC v6.8; cada fonte com cooldown):
#   - Sina nf_CU0: realtime-ish; f[8]=último, f[27]=昨结算 (settlement
#     anterior — base da variação do dia, convenção chinesa). O CU0 da
#     Sina É o contrato principal real (conferido 22/09/2026: idêntico ao
#     CU2611, flag is-main=1).
#   - Eastmoney futsseapi 113_cum_qt (沪铜主连): p=último, j=昨结算
#     (série EMENDADA — nível pode divergir ~0,4% do contrato cru; pct
#     próprio consistente).
#   - Eastmoney push2delay 113.cum: preço puro na escala f152 (o f170
#     calcula vs limite -> NÃO vira pct).
# Exibição em US$/lb (comparável com o COMEX HG=F da linha de cima):
#   US$/lb = CNY/t ÷ USDCNY ÷ 2204.62262 — USDCNY só FRESH (fetch_fx,
#   3 fontes, ≤ FX_MAX_AGE); sem câmbio fresco: CNY/t cru (flag 'cny'),
#   nunca com taxa velha. Var % vem do CNY (idêntica em US$).
EM_CU_FUTSSE_URL = ("https://futsseapi.eastmoney.com/static/"
                    "113_cum_qt?token=58b2fa8f5c380ac3ee3494ecc1b6d8e6")
EM_CU_SECID      = "113.cum"
EM_CU_PUSH2_URL  = ("https://push2delay.eastmoney.com/api/qt/stock/get"
                    "?secid={secid}&fields=f43,f152,f170"
                    "&ut=fa5fd1943c7b386f172d6893dbfba10b")
SINA_CU_CODE     = "nf_CU0"
SINA_CU_KLINE_URL = ("https://stock2.finance.sina.com.cn/futures/api/"
                     "jsonp.php/var%20_s=/InnerFuturesNewService"
                     ".getDailyKLine?symbol=CU0")   # kline diário (reserva)
CU_REFETCH       = 5 * 60             # intraday (sessão noturna): 1/5min
CU_MAX_AGE       = 4 * 86400          # cache vence (4 dias; cobre fds)
CU_CNY_LO        = 20000.0            # sanidade CNY/t (kline 2005: ~29k)
CU_CNY_HI        = 300000.0           # teto folgado (hist ~161k em 2025)
CU_PCT_LIMIT     = 15.0               # |pct| além do limite diário = dado ruim
LB_PER_TON       = 2204.62262         # 1 tonelada métrica em libras

# -------------- CONFIG · CRUDE URALS (Rússia, v7.0) --------------------------
# Urals = blend de exportação da Rússia (FOB NW Europe/Primorsk). NÃO é
# cotado em bolsa regular: Yahoo/FRED/Investing/TradingEconomics-comum não
# têm série de spot de bolsa — o valor vem de AVALIAÇÕES (Argus/Platts,
# Dated Brent − desconto) com atraso. Cadeia (v7.0, cada fonte com
# cooldown próprio):
#   1º TE /commodity/urals-oil  [T+1]: scrape market_last (mesmo scraper
#      do HO=F/ureia/sulfur); date real parseada do resumo da página
#   2º minfin.com.ua /markets/oil/urals/  [T+1]: tabela diária, GET puro,
#      sem chave, decimal com vírgula (16.09.2026 = 121,61)
#   3º OilPrice.com oil-price-charts: linha data-name 'Urals-Brent'
#      (blend 4466; T+2 — "(2-Day Delay)" conferido ao vivo)
#   4º OilPrice.com /freewidgets/json_get_oilprices: POST JSON do gráfico
#      (CSRF de /ajax/csrf; exige header X-Requested-With)
OILPRICE_CHARTS_URL = "https://oilprice.com/oil-price-charts/"
OILPRICE_CSRF_URL   = "https://oilprice.com/ajax/csrf"
OILPRICE_JSON_URL   = "https://oilprice.com/freewidgets/json_get_oilprices"
TE_URALS_URL        = "https://tradingeconomics.com/commodity/urals-oil"
MINFIN_URALS_URL    = "https://index.minfin.com.ua/markets/oil/urals/"
URALS_BLEND_ID      = "4466"
URALS_REFETCH       = 3600              # dado atrasado T+1: refetch 1/h
URALS_MAX_AGE       = 7 * 86400         # cache vence (7 dias sem fonte)
OILPRICE_PAGE_TTL   = 120               # tabela serve Urals/Brent/Murban: 2min

# ------------------- CONFIG · CRUDE MURBAN (Emirados, v6.9) ------------------
# Murban = blend de exportação de Abu Dhabi (precificado pela ADNOC;
# benchmark oficial do Oriente Médio na ICE Futures Abu Dhabi). Como o
# Urals, NÃO é spot de bolsa comum acessível (Yahoo sem MU=F/MOF=F/MURBAN
# — 404 validado; TV scanner 0 resultados; FXEmpire 404; TE sem cotação):
# a fonte viva é o OilPrice.com, mesma infra do Urals/Brent:
#   - tabela oil-price-charts: linha data-name='Murban-Crude' (data-id
#     4464), avaliação com delay de minutos (conferido: 16-Minute Delay)
#   - freewidgets json_get_oilprices (blend_id 4464): quote + séries
#     históricas (períodos 4=1M, 6=3M, 5=1A), CSRF + X-Requested-With
MURBAN_BLEND_ID = "4464"
MURBAN_REFETCH  = 3600                # avaliação com delay: refetch 1/h
MURBAN_MAX_AGE  = 7 * 86400           # cache vence (7 dias; padrão Urals)

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

# ------------------- CONFIG · CRUDE SC (Xangai INE, v6.8) --------------------
# Futuro de crude da INE (Shanghai International Energy Exchange) — o
# "Shanghai oil". Cota em CNY/bbl (tick 0,1). Yahoo NÃO tem SC=F (404
# validado) e o scanner do TV não cobre a INE, então a cadeia vive de
# fontes CN: Sina nf_SC0 (contínuo SC0) -> Eastmoney futsseapi 142_scm_qt
# (原油主连) -> Eastmoney push2delay 142.scm -> cache. Layout da Sina p/ o
# SC (verificado ao vivo): f[8]=último, f[10]=LIMITE-UP (nunca usar),
# f[27]=昨结算 (settlement — base da variação do dia, convenção chinesa).
# Exibição US$/bbl com USDCNY fresco (mesma regra do enxofre; sem câmbio
# fresco: CNY/bbl cru). Faixa de sanidade: kline set/26 631..838 CNY/bbl.
EM_SC_FUTSSE_URL = ("https://futsseapi.eastmoney.com/static/"
                    "142_scm_qt?token=58b2fa8f5c380ac3ee3494ecc1b6d8e6")
EM_SC_SECID      = "142.scm"
SINA_SC_CODE     = "nf_SC0"
SINA_SC_KLINE_URL = ("https://stock2.finance.sina.com.cn/futures/api/"
                     "jsonp.php/var%20_s=/InnerFuturesNewService"
                     ".getDailyKLine?symbol=SC0")   # kline diário (reserva)
SC_REFETCH       = 5 * 60            # intraday (sessão noturna): 1/5min
SC_MAX_AGE       = 4 * 86400         # cache vence (4 dias; cobre fds)
SC_CNY_LO        = 50.0              # sanidade do valor CNY/bbl
SC_CNY_HI        = 2000.0            # (hist 2025-26: ~400..900)
SC_PCT_LIMIT     = 25.0              # |pct| além do limite do preço = dado ruim

# ------------------- CONFIG · UREIA (fertilizante, v6.6) ---------------------
# Uréia = fertilizante nitrogenado. 2 linhas em US$/t:
#   - "Uréia (spot intl.)": diário. O TE espelha o granular FOB GOLFO EUA
#     (conferido no dia do teste: TE 460.00 == contínuo CBOT UFV1! 460.0 —
#     por isso o rótulo NÃO fala "Oriente Médio").
#   - "Uréia CFR Brasil"  : futuro CBOT/CME "Urea (Granular) CFR Brazil"
#     (UFB=F) — o preço chegando no porto brasileiro.
# Cadeias (cada fonte com cooldown próprio, padrão v6.4):
#   spot : TE (scrape market_last, mesmo scraper do HO=F) -> TradingView
#          scanner (POST JSON público, contínuo CBOT:UFV1!, MESMA base do
#          TE) -> World Bank Pink Sheet (xlsx MENSAL, zip+XML stdlib; série
#          "Urea" f.o.b. Oriente Médio US$/mt — BASE DIFERENTE, rodapé
#          mostra "mensal") -> cache.
#   CFR  : Yahoo UFB=F (chart API, q1 -> q2 em 429) -> TV (CBOT:UFB1!) ->
#          cache.
# Refetch no máx. 1/h (dado diário); cache vence em 14 dias (padrão do
# combustível). Mortas no teste e portanto FORA da cadeia: CEPEA (sem
# indicador), FMI/PCPS (sem ureia), FRED (só índice PPI), Investing/
# Barchart/CME (403/challenge). A URL do xlsx do Pink Sheet muda de "safra"
# p/ safra (hash no caminho) -> descobre na página oficial, com a URL
# conhecida como reserva.
TE_UREA_URL   = "https://tradingeconomics.com/commodity/urea"
UREA_REFETCH  = 3600                  # diário: refetch no máx. 1/h
UREA_MAX_AGE  = 14 * 86400            # cache vence (14 dias sem fonte)
YAHOO_UREA_BR_URL    = ("https://query1.finance.yahoo.com/v8/finance/chart/UFB=F"
                        "?interval=1d&range=5d")
YAHOO_UREA_BR_URL_Q2 = ("https://query2.finance.yahoo.com/v8/finance/chart/UFB=F"
                        "?interval=1d&range=5d")
TV_SCAN_URL   = "https://scanner.tradingview.com/global/scan"
WB_CM_PAGE    = "https://www.worldbank.org/en/research/commodity-markets"
WB_CM_XLSX    = ("https://thedocs.worldbank.org/en/doc/"
                 "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
                 "CMO-Historical-Data-Monthly.xlsx")   # reserva (set/2026)
UREA_PINK_TTL = 12 * 3600             # xlsx ~600 KB, atual 1x/mês: cache 12h

# ------------------- CONFIG · ENXOFRE (spot CN, v6.7) ------------------------
# Enxofre elemental (granular, spot da China). NÃO existe público em US$/t:
# Pink Sheet sem série sulfur (conferido no xlsx: bloco fertilizante =
# Phosphate rock/DAP/TSP/Urea/KCl), IMF/FRED/Yahoo/OilPrice/Investing não
# têm, futuro não existe em bolsa. As duas fontes vivas publicam CNY/t e
# espelham o MESMO mercado (conferido: SunSirs 2026-09-16 = 7704.00 ==
# fechamento anterior do TE; 09-17: TE 7.687,33 vs SunSirs 7.685,67):
#   - TradingEconomics /commodity/sulfur — scrape market_last (mesmo
#     scraper da ureia/HO); histórico: máx 11.084 / mín 470 (CNY/t)
#   - SunSirs EN prodetail-427 — tabela diária (Sulfur|Chemical|preço|data)
#     com os últimos 6 dias; anti-bot JS seta HW_CHECK=<hash> e recarrega:
#     replicado com urllib em 2 GETs (hash extraído da 1ª resposta)
# Exibição em US$/t: ÷ USDCNY (USDCNY = USDBRL ÷ CNYBRL, 3 fontes
# fetch_fx). Sem câmbio fresco: CNY/t cru (flag 'cny').
TE_SULFUR_URL       = "https://tradingeconomics.com/commodity/sulfur"
SUNSIRS_SULFUR_URL  = "https://www.sunsirs.com/uk/prodetail-427.html"
SULFUR_REFETCH      = 3600            # diário: refetch no máx. 1/h
SULFUR_MAX_AGE      = 14 * 86400      # cache vence (14 dias sem fonte)
SULFUR_CNY_LO       = 100.0           # sãidade do valor CNY/t (hist 470..)
SULFUR_CNY_HI       = 20000.0         # ...11.084; teto folgado

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
#   CDS 5Y       : Investing (API financialdata/historical, 1 ano; fallback
#                  SSR da pagina historical-data, ~1 mes)
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
# v7.1 — API REST do Investing p/ a serie completa do CDS (o SSR da pagina
# historical-data so traz ~1 mes). pair_id do instrumento, extraido do HTML.
INV_CDS_PAIR_ID  = "1116031"
INV_CDS_API_FMT  = ("https://api.investing.com/api/financialdata/"
                    "historical/{pair}?start-date={beg}&end-date={end}"
                    "&time-frame=Daily&add-missing-rows=false")
FRED_CSV_FMT    = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
# v8.1 — o FRED PENDURA (timeout, nem 403) em UA de navegador e no nosso
# 'gold-widget/5.0'; só responde a UA de cliente HTTP "de verdade"
# (curl/Wget/python-urllib/okhttp — validado 23/09/2026). Por isso os
# fetches do FRED usam este UA e NÃO o BROWSER_UA (quebrava o fallback
# de combustível GASREGW/DIESEL desde sempre: timeout em todo hit).
FRED_UA         = "python-urllib/3.12"
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
                            {"User-Agent": FRED_UA},
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


def _hist_cds_api(days):
    """Serie diaria do CDS via API REST do Investing (mesma do site, sem
    chave): 1 ano completo (o SSR da pagina historical-data so traz ~1 mes).
    Cabeçalho 'domain-id' obrigatorio; rows em ordem desc. (mais novo 1o)."""
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    beg = (datetime.now(timezone.utc) - timedelta(days=int(days) + 5)
           ).strftime("%Y-%m-%d")
    url = INV_CDS_API_FMT.format(pair=INV_CDS_PAIR_ID, beg=beg, end=end)
    d = _get_json(url, {"User-Agent": BROWSER_UA,
                        "Accept": "application/json",
                        "domain-id": "www"}, timeout=20)
    rows = d.get("data") or []
    pts = []
    for r in rows:
        try:
            dt = str(r.get("rowDateTimestamp") or "")[:10]
            raw = (r.get("last_closeRaw")
                   if r.get("last_closeRaw") is not None
                   else r.get("last_close"))
            v = float(raw)
            if v > 0 and len(dt) == 10:
                pts.append((dt, v))
        except Exception:
            continue
    pts.sort()
    if len(pts) < 2:
        raise ValueError("API sem serie")
    days = int(days)
    return pts[-days:] if len(pts) > days else pts, "Investing.com (API)"


def _hist_cds(days):
    try:
        return _hist_cds_api(days)
    except Exception as e:
        log(f"hist cds: API Investing falhou ({e}); fallback SSR")
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


def _hist_yield_api(mat, days):
    """Série diária do yield nominal do vencimento `mat` via API historical
    do Investing (a MESMA do CDS v7.1; cabeçalho 'domain-id' obrigatório;
    rows em ordem DESC — sort asc). Serve o gráfico do clique (7D-1A) e o
    último degrau do quote (linha de HOJE entra intraday — conferido ao
    vivo 23/09/2026: 1ª row = valor vivo 14.17)."""
    meta = YIELD_MATS.get(mat)
    if not meta:
        raise ValueError(f"vencimento desconhecido: {mat}")
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    beg = (datetime.now(timezone.utc) - timedelta(days=int(days) + 5)
           ).strftime("%Y-%m-%d")
    url = INV_CDS_API_FMT.format(pair=meta["pair"], beg=beg, end=end)
    d = _get_json(url, {"User-Agent": BROWSER_UA,
                        "Accept": "application/json",
                        "domain-id": "www"}, timeout=20)
    rows = d.get("data") or []
    pts = []
    for r in rows:
        dt = str(r.get("rowDateTimestamp") or "")[:10]
        raw = (r.get("last_closeRaw")
               if r.get("last_closeRaw") is not None else r.get("last_close"))
        v = _to_float(raw)
        if v and YIELD_LO < v < YIELD_HI and len(dt) == 10:
            pts.append((dt, v))
    pts.sort()
    if len(pts) < 2:
        raise ValueError(f"API sem série do {mat}")
    days = int(days)
    return pts[-days:] if len(pts) > days else pts, "Investing.com (API)"


def _hist_us_yield_api(mat, days):
    """Série diária do yield nominal do vencimento `mat` (UST) via API
    historical do Investing (a MESMA do CDS v7.1; cabeçalho 'domain-id'
    obrigatório; rows em ordem DESC — sort asc). Serve o gráfico do clique
    (7D-1A) e o degrau do quote (linha de HOJE entra intraday)."""
    meta = US_YIELD_MATS.get(mat)
    if not meta:
        raise ValueError(f"vencimento desconhecido: {mat}")
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    beg = (datetime.now(timezone.utc) - timedelta(days=int(days) + 5)
           ).strftime("%Y-%m-%d")
    url = INV_CDS_API_FMT.format(pair=meta["pair"], beg=beg, end=end)
    d = _get_json(url, {"User-Agent": BROWSER_UA,
                        "Accept": "application/json",
                        "domain-id": "www"}, timeout=20)
    rows = d.get("data") or []
    pts = []
    for r in rows:
        dt = str(r.get("rowDateTimestamp") or "")[:10]
        raw = (r.get("last_closeRaw")
               if r.get("last_closeRaw") is not None else r.get("last_close"))
        v = _to_float(raw)
        if v and US_YIELD_LO < v < US_YIELD_HI and len(dt) == 10:
            pts.append((dt, v))
    pts.sort()
    if len(pts) < 2:
        raise ValueError(f"API sem série do {mat}")
    days = int(days)
    return pts[-days:] if len(pts) > days else pts, "Investing.com (API)"


def _hist_us_yield_fred(mat, days):
    """Série diária do yield CMT oficial do Tesouro (FRED DGS*) — fallback
    do gráfico quando a API do Investing cai. EOD (fecha ~1 dia atrás)."""
    meta = US_YIELD_MATS.get(mat) or {}
    sid = meta.get("fred")
    if not sid:
        raise ValueError(f"FRED sem série do {mat}")
    pts, src = _hist_fred([sid], days + 5)
    pts = [(d, v) for d, v in pts if US_YIELD_LO < v < US_YIELD_HI]
    if len(pts) < 2:
        raise ValueError(f"FRED sem série do {mat}")
    return pts, src


def _hist_oilprice_blend(blend_id, days, label):
    """Série histórica de um blend no endpoint JSON do OilPrice.com.
    Períodos do blend: 4=1M (~20 pts), 6=3M (~61), 5=1A (~251).
    Pontos vêm em epoch; normaliza p/ data UTC deduplicada."""
    days = int(days)
    if days <= 40:
        period = 4
    elif days <= 120:
        period = 6
    else:
        period = 5
    pts, _lc, _u = _oilprice_json_period(blend_id, period)
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
        raise ValueError(f"OilPrice {label} sem serie")
    return ser[-days:] if len(ser) > days else ser, f"OilPrice.com"


def _hist_urals(days):
    return _hist_oilprice_blend(URALS_BLEND_ID, days, "Urals")


def _hist_murban(days):
    return _hist_oilprice_blend(MURBAN_BLEND_ID, days, "Murban")


def _hist_sc_sina_kline():
    """Série diária do contínuo SC0 no endpoint de kline de futuros da
    própria Sina (infra independente do Eastmoney; desde 2018-03-26, o
    listing do SC). JSONP 'var _s=([{d,o,h,l,c,v,...},...])' — exige
    Referer; c>0 e dentro da faixa de sanidade."""
    raw = _http_get(SINA_SC_KLINE_URL,
                    {"Referer": SINA_REFERER}).decode("utf-8", "replace")
    s, e = raw.find("["), raw.rfind("]")
    if s < 0 or e <= s:
        raise ValueError("Sina kline sem JSONP")
    rows = json.loads(raw[s:e + 1])
    pts = []
    for r in rows:
        try:
            c = float(r.get("c"))
        except (TypeError, ValueError):
            continue
        if not _sc_ok(c):
            continue
        d = str(r.get("d") or "")
        if len(d) == 10:
            pts.append((d, c))
    if len(pts) < 2:
        raise ValueError("Sina kline SC0 sem série")
    return pts


def _hist_sc(days):
    """Série p/ o gráfico do SC: kline diário do contínuo (CNY/bbl) —
    Eastmoney 142.scm -> Sina SC0 (fontes independentes) — convertida
    ÷ USDCNY de AGORA (nota no rodapé do popup, como no enxofre). Sem
    câmbio fresco ou com as duas séries mortas: levanta (o fetch_history
    cai pro log local, que acumula US$/bbl desde a v6.8)."""
    days = int(days)
    fx = fetch_fx()
    if not (fx.get("usdcny") and _fx_fresh(fx)):
        raise ValueError("sem câmbio fresco p/ converter a série SC")
    rate = float(fx["usdcny"])
    try:
        cny_pts, _s0 = _hist_em(EM_SC_SECID, days)
    except Exception as e:
        log(f"hist SC: push2his falhou ({e}); Sina kline")
        cny_pts = _hist_sc_sina_kline()
    pts = [(d, round(v / rate, 4))
           for d, v in (cny_pts[-days:] if len(cny_pts) > days else cny_pts)]
    if len(pts) < 2:
        raise ValueError(f"SC sem série ({len(pts)} ponto(s))")
    return pts, f"SC diário (CNY÷{rate:.4f})"


def _hist_cu_sina_kline():
    """Série diária do contínuo CU0 no endpoint de kline de futuros da
    própria Sina (infra independente do Eastmoney; desde 2005). JSONP
    'var _s=([{d,o,h,l,c,v,...},...])' — exige Referer; c>0 e dentro da
    faixa de sanidade. MESMA série emendada do kline EM 113.cum
    (conferido 22/09/2026: fech. 22/09 = 111.320 nas duas)."""
    raw = _http_get(SINA_CU_KLINE_URL,
                    {"Referer": SINA_REFERER}).decode("utf-8", "replace")
    s, e = raw.find("["), raw.rfind("]")
    if s < 0 or e <= s:
        raise ValueError("Sina kline CU0 sem JSONP")
    rows = json.loads(raw[s:e + 1])
    pts = []
    for r in rows:
        try:
            c = float(r.get("c"))
        except (TypeError, ValueError):
            continue
        if not _cu_ok(c):
            continue
        d = str(r.get("d") or "")
        if len(d) == 10:
            pts.append((d, c))
    if len(pts) < 2:
        raise ValueError("Sina kline CU0 sem série")
    return pts


def _hist_cu(days):
    """Série p/ o gráfico do CU0: kline diário do contínuo (CNY/t) —
    Eastmoney 113.cum -> Sina CU0 (fontes independentes) — convertida
    ÷ USDCNY de AGORA ÷ 2204.62262 (lb/t; nota no rodapé do popup). Sem
    câmbio fresco ou com as duas séries mortas: levanta (o fetch_history
    cai pro log local, que acumula US$/lb desde a v7.3)."""
    days = int(days)
    fx = fetch_fx()
    if not (fx.get("usdcny") and _fx_fresh(fx)):
        raise ValueError("sem câmbio fresco p/ converter a série CU")
    rate = float(fx["usdcny"])
    try:
        cny_pts, _s0 = _hist_em(EM_CU_SECID, days)
    except Exception as e:
        log(f"hist CU: push2his falhou ({e}); Sina kline")
        cny_pts = _hist_cu_sina_kline()
    pts = [(d, round(v / rate / LB_PER_TON, 4))
           for d, v in (cny_pts[-days:] if len(cny_pts) > days else cny_pts)]
    if len(pts) < 2:
        raise ValueError(f"CU sem série ({len(pts)} ponto(s))")
    return pts, f"SHFE CU0 diário (CNY÷{rate:.4f}÷lb)"


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
    "copper":     {"title": "Cobre · COMEX HG=F (US$/lb)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}",
                   "yfmt": lambda v: f"{v:.2f}",
                   "ranges": (7, 30, 90, 180, 365)},
    "cu_shfe":    {"title": "Cobre · SHFE CU0 (US$/lb)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}",
                   "yfmt": lambda v: f"{v:.2f}",
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
    "sc_f":       {"title": "China · Crude SC (USD/bbl)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}",
                   "yfmt": lambda v: f"{v:,.0f}",
                   "ranges": (7, 30, 90, 180, 365)},
    "murban":     {"title": "Emirados · Murban (USD/bbl)",
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
                   "ranges": (7, 30, 90, 180, 365)},
    "urea_me":    {"title": "Uréia · Spot intl. (US$/t)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}/t",
                   "yfmt": lambda v: f"{v:,.0f}",
                   "ranges": (7, 30, 90, 180, 365)},
    "urea_br":    {"title": "Uréia · CFR Brasil UFB=F (US$/t)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}/t",
                   "yfmt": lambda v: f"{v:,.0f}",
                   "ranges": (7, 30)},
    "sulfur":     {"title": "Enxofre · Spot CN (US$/t)",
                   "fmt": lambda v: f"US$ {fmt_usd(v)}/t",
                   "yfmt": lambda v: f"{v:,.0f}",
                   "ranges": (7, 30, 90, 180, 365)},
}


def fetch_history(key, days=30, hist_log=None):
    days = int(days)
    base = key
    bank_name = None
    if key.startswith("bank:"):
        bank_name = key.split(":", 1)[1]
        base = "sge_au9999"
    elif key.startswith("br_yield:"):
        base = "br_yield"
    elif key.startswith("us_yield:"):
        base = "us_yield"
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
        elif base == "copper":
            pts, src = _hist_yahoo("HG=F", days)
        elif base == "cu_shfe":
            pts, src = _hist_cu(days)
        elif base == "gc_f":
            pts, src = _hist_yahoo("GC=F", days)
        elif base == "ho_f":
            pts, src = _hist_yahoo("HO=F", days)
        elif base == "brent":
            pts, src = _hist_yahoo("BZ=F", days)
        elif base == "urals":
            pts, src = _hist_urals(days)
        elif base == "sc_f":
            pts, src = _hist_sc(days)
        elif base == "murban":
            pts, src = _hist_murban(days)
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
        elif base == "br_yield":
            pts, src = _hist_yield_api(key.split(":", 1)[1], days)
        elif base == "us_yield":
            _umat = key.split(":", 1)[1]
            try:
                pts, src = _hist_us_yield_api(_umat, days)
            except Exception:
                pts, src = _hist_us_yield_fred(_umat, days)
        elif base == "urea_me":
            pts, src = _hist_urea_me(days)
        elif base == "urea_br":
            raise ValueError("UFB=F sem série pública (histórico no log local)")
        elif base == "sulfur":
            pts, src = _hist_sulfur(days)
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

# ------------------- INSTÂNCIA ÚNICA (v8.4.1) -------------------
# Trava a GUI em UMA instância via flock(LOCK_EX|LOCK_NB) em LOCK_FILE.
# Por que flock e não pidfile: o kernel libera o lock sozinho quando o
# processo morre (até em SIGKILL/poweroff) — pidfile fica stale e exige
# heurística de kill -0 + risco de PID reciclado.
# O fd fica guardado em _INSTANCE_LOCK_FD (global) a app inteira: se o fd
# fosse fechado/GC'd, o lock seria liberado e a proteção sumiria.
# Retorna True (lock nosso, pode rodar) ou False (outra instância dona).
_INSTANCE_LOCK_FD = None

def acquire_instance_lock():
    """Tenta segurar a trava de instância única. Nunca levanta."""
    global _INSTANCE_LOCK_FD
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        # O_RDWR|O_CREAT cria se não existir e NUNCA trunca (só o dono
        # do lock reescreve o carimbo, via ftruncate+write abaixo).
        fd = os.open(LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            # EACCES/EAGAIN = outro processo segura o lock. Outro errno
            # (ex.: NFS sem suporte) = fail-open: roda sem trava, como antes.
            os.close(fd)
            if e.errno in (errno.EACCES, errno.EAGAIN):
                return False
            log(f"instância única indisponível ({e}); rodando sem trava")
            return True
        _INSTANCE_LOCK_FD = fd  # fd ABERTO até o exit: lock vivo
        try:
            # Carimbo informativo (best-effort; falha aqui não solta o lock).
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        except Exception:
            pass
        return True
    except Exception as e:
        log(f"instância única indisponível ({e}); rodando sem trava")
        return True  # fail-open: trava NUNCA impede o uso

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

def fmt_yield(v):
    """14,170 (pt-BR, 3 decimais) — yield em % a.a."""
    s = f"{v:,.3f}"
    return s.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")

def fmt_pp(v):
    """+0,04pp — Δ do yield em pontos percentuais (não % relativo)."""
    s = f"{v:+,.2f}"
    s = s.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")
    return f"{s}pp"

def fmt_fx4(v):
    """5,1526 (pt-BR, 4 decimais) — par cambial USD/BRL."""
    s = f"{v:,.4f}"
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

def _http_post_raw(url, body, headers=None, timeout=NET_TIMEOUT):
    """POST com corpo cru (XML/texto) — o _http_post_json faz json.dumps
    e estraga SOAP."""
    if isinstance(body, str):
        body = body.encode("utf-8")
    hdrs = {"User-Agent": "gold-widget/5.0", "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

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

# ------------------- FETCH · USD/BRL (campo visível, v8.2) -----------------
# Só o campo "CÂMBIO · USD/BRL". NÃO mexe no fetch_fx (derivações). Mid =
# (compra+venda)/2 ou (bid+ask)/2; fonte de 1 número usa o número direto.
# Cada degrau tem nome/cooldown próprio (padrão v6.4): falha cai no próximo
# automaticamente, e se o próximo falhar cai em outro, até acabar.

def _mid(a, b):
    """Mid de um par compra/venda ou bid/ask; 1 número só vira o mid."""
    if a is None and b is None:
        raise ValueError("sem cotação")
    if a is None:
        return float(b)
    if b is None:
        return float(a)
    return (float(a) + float(b)) / 2.0

def _ok_usdbrl(r):
    """Valida o mid: tem que ser um USD/BRL plausível."""
    r = float(r)
    if not (1.0 <= r <= 20.0):
        raise ValueError(f"USD/BRL fora de faixa: {r}")
    return r

def _usdbrl_awesomeapi():
    """1. awesomeapi: bid/ask do par USDBRL (intraday BR). Reserva /all."""
    errs = []
    for url in (AAPI_USDBRL, AAPI_ALL):
        try:
            d = _get_json(url, {"User-Agent": BROWSER_UA}, timeout=10)
            u = d.get("USDBRL") or d.get("USD") or {}
            return _ok_usdbrl(_mid(_to_float(u.get("bid")),
                                   _to_float(u.get("ask"))))
        except Exception as e:
            errs.append(f"{url.split('/')[-1]}: {e}")
    raise ValueError("awesomeapi (" + "; ".join(errs) + ")")

def _usdbrl_yahoo():
    """2. Yahoo USDBRL=X (chart). q2 -> q1 em erro/429. Usa bid/ask se
    vierem; senão regularMarketPrice."""
    errs = []
    for url in (YAHOO_UBRL_Q2, YAHOO_UBRL_Q1):
        try:
            _yahoo_throttle()
            d = _get_json(url, {"User-Agent": BROWSER_UA}, timeout=10)
            res = (d.get("chart") or {}).get("result") or []
            if not res:
                raise ValueError("sem result")
            meta = res[0].get("meta") or {}
            b = _to_float(meta.get("regularMarketBid"))
            a = _to_float(meta.get("regularMarketAsk"))
            if b is not None or a is not None:
                return _ok_usdbrl(_mid(b, a))
            p = _to_float(meta.get("regularMarketPrice"))
            if p is None:
                raise ValueError("sem preço")
            return _ok_usdbrl(p)
        except Exception as e:
            errs.append(str(e))
    raise ValueError("Yahoo (" + "; ".join(errs) + ")")

def _usdbrl_te():
    """3. TradingEconomics /brazil/currency — scrape market_last (mesmo
    scraper do HO=F/ureia/enxofre)."""
    d = _fetch_te_commodity(TE_USDBRL_URL, 20)
    return _ok_usdbrl(d["price"])

def _usdbrl_floatrates():
    """4. floatrates: usd.json -> brl.rate (intraday)."""
    d = _get_json(FLOATRATES_URL, {"User-Agent": BROWSER_UA}, timeout=10)
    return _ok_usdbrl(_to_float((d.get("brl") or {}).get("rate")))

def _usdbrl_currency_api():
    """5. currency-api: usd.brl nos 2 espelhos (pages.dev FRESCO 1º — o
    jsDelivr @latest fica preso na versão do pacote e serve cotação velha;
    validado 24/09/2026: jsDelivr 5,1015 vs pages.dev 5,1672). Reserva o
    inverso 1/brl.usd."""
    errs = []
    for url in (FX_JSD_PAGES, FX_JSD):
        try:
            d = _get_json(url, timeout=12)
            r = _to_float((d.get("usd") or {}).get("brl"))
            if r:
                return _ok_usdbrl(r)
            raise ValueError("sem usd.brl")
        except Exception as e:
            errs.append(str(e))
    for url in (FX_JSD_BRL_PG,):
        try:
            d = _get_json(url, timeout=12)
            inv = _to_float((d.get("brl") or {}).get("usd"))
            if inv and inv > 0:
                return _ok_usdbrl(1.0 / inv)
            raise ValueError("sem brl.usd")
        except Exception as e:
            errs.append(f"inv: {e}")
    raise ValueError("currency-api (" + "; ".join(errs) + ")")

def _usdbrl_erapi():
    """6. open.er-api.com: rates.BRL (diário)."""
    d = _get_json(FX_ERAPI, timeout=10)
    return _ok_usdbrl(_to_float((d.get("rates") or {}).get("BRL")))

def _usdbrl_frankfurter():
    """7. frankfurter.dev: rates.BRL (ECB, diário). O .app redireciona
    p/ .dev — só .dev responde JSON."""
    d = _get_json(FX_FRA, timeout=10)
    return _ok_usdbrl(_to_float((d.get("rates") or {}).get("BRL")))

def _bcb_sgs_valor(serie):
    """Último valor do SGS (texto '5.1414') ou None se a série não
    publicou (fds/feriado não pode matar o degrau inteiro)."""
    try:
        d = _get_json(BCB_SGS_ULT.format(serie=serie), timeout=10)
    except Exception:
        return None
    if isinstance(d, list) and d:
        return _to_float(d[-1].get("valor"))
    return None

def _usdbrl_bcb_sgs():
    """8. BCB SGS: compra (10813) + venda (1) -> mid. Uma série morta
    (fds) não derruba o degrau: usa a outra."""
    c = _bcb_sgs_valor(SGS_COMPRA)
    v = _bcb_sgs_valor(SGS_VENDA)
    return _ok_usdbrl(_mid(c, v))

def _olinda_mid(values):
    """Mid da entrada PTAX mais recente de uma lista Olinda."""
    best = None
    for it in values or []:
        ts = str(it.get("dataHoraCotacao") or "")
        if best is None or ts > str(best.get("dataHoraCotacao") or ""):
            best = it
    if not best:
        raise ValueError("Olinda sem cotação")
    return _mid(_to_float(best.get("cotacaoCompra")),
                _to_float(best.get("cotacaoVenda")))

def _usdbrl_olinda():
    """9. Olinda PTAX: CotacaoDolarDia (hoje; 13h BRT e pode sair vazio)
    -> CotacaoDolarPeriodo (últimos dias) -> mid compra/venda."""
    errs = []
    for back in (0, 1, 2, 3):
        day = (datetime.now(timezone.utc) - timedelta(days=back))
        date = day.strftime("%m-%d-%Y")
        try:
            d = _get_json(OLINDA_DIA.format(date=date), timeout=12)
            vals = d.get("value") or []
            if vals:
                return _ok_usdbrl(_olinda_mid(vals))
            errs.append(f"dia {date} vazio")
        except Exception as e:
            errs.append(f"dia {date}: {e}")
    try:
        d0 = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%m-%d-%Y")
        d1 = datetime.now(timezone.utc).strftime("%m-%d-%Y")
        d = _get_json(OLINDA_PER.format(d0=d0, d1=d1), timeout=12)
        return _ok_usdbrl(_olinda_mid(d.get("value") or []))
    except Exception as e:
        errs.append(f"periodo: {e}")
    raise ValueError("Olinda (" + "; ".join(errs) + ")")

_SOAP_ENV = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
    ' xmlns:pub="http://publico.servicos.wssgs.bcb.gov.br">'
    '<soapenv:Header/><soapenv:Body><pub:getUltimoValorVO>'
    '<pub:codigoSérie>{serie}</pub:codigoSérie>'
    '</pub:getUltimoValorVO></soapenv:Body></soapenv:Envelope>'
)

def _bcb_soap_valor(serie):
    """Espelho SOAP do SGS (host www3): último valor da série ou None."""
    try:
        xml = _http_post_raw(BCB_SOAP_URL, _SOAP_ENV.format(serie=serie),
                             {"Content-Type": "text/xml; charset=utf-8",
                              "SOAPAction": ""}, timeout=12)
    except Exception:
        return None
    m = re.search(r"<svalor[^>]*>([0-9.]+)", xml)
    return _to_float(m.group(1)) if m else None

def _usdbrl_bcb_soap():
    """10. BCB SOAP www3 (host espelho do SGS): compra+venda -> mid."""
    c = _bcb_soap_valor(SGS_COMPRA)
    v = _bcb_soap_valor(SGS_VENDA)
    return _ok_usdbrl(_mid(c, v))

def fetch_usdbrl():
    """USD/BRL mid p/ o campo visível. Cadeia (v8.2, cooldown por fonte):
    awesomeapi -> Yahoo -> TE -> floatrates -> currency-api -> er-api ->
    frankfurter -> BCB SGS -> Olinda PTAX -> BCB SOAP. Cada falha cai no
    próximo degrau automaticamente; se o próximo falhar cai em outro, até
    acabar. O chamador segura o cache 24h quando levanta."""
    errs = []
    chain = (
        ("usdbrl-awesomeapi",    _usdbrl_awesomeapi),
        ("usdbrl-yahoo",         _usdbrl_yahoo),
        ("usdbrl-te",            _usdbrl_te),
        ("usdbrl-floatrates",    _usdbrl_floatrates),
        ("usdbrl-currency-api",  _usdbrl_currency_api),
        ("usdbrl-er-api",        _usdbrl_erapi),
        ("usdbrl-frankfurter",   _usdbrl_frankfurter),
        ("usdbrl-bcb-sgs",       _usdbrl_bcb_sgs),
        ("usdbrl-olinda",        _usdbrl_olinda),
        ("usdbrl-bcb-soap",      _usdbrl_bcb_soap),
    )
    for name, fn in chain:
        if not _src_due(name):
            continue                       # fonte em cooldown: pula p/ a próxima
        try:
            rate = _ok_usdbrl(fn())        # validação extra (defesa em profundidade)
            _src_clear(name)
            return {"rate": rate, "src": name.replace("usdbrl-", ""),
                    "ts": time.time()}
        except Exception as e:
            errs.append(f"{name.replace('usdbrl-', '')}: {e}")
            _src_cooldown(name, USDBRL_REFETCH, str(e))
    raise RuntimeError("USD/BRL sem fonte viva (" + "; ".join(errs) + ")")

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
    com o Δ absoluto e market_daily_Pchg com o Δ% do dia. Quando a página
    traz o resumo ('... rose to 121.61 USD/Bbl on September 16, 2026'),
    a data real do dado vai no campo 'day' (strptime %B %d, %Y — locale
    C = meses em inglês)."""
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
    day = None
    mday = re.search(r"rose to [0-9.,]+ [^<>]{0,80}?on "
                     r"([A-Z][a-z]+ \d{1,2}, \d{4})", html)
    if mday:
        try:
            day = (datetime.strptime(mday.group(1), "%B %d, %Y")
                   .date().isoformat())
        except ValueError:
            pass
    return {"price": price,
            "pct": _to_float(mp.group(1)) if mp else None,
            "day_chg": chg,
            "prev_close": (round(price - chg, 4) if chg else None),
            "day": day,
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

# ------------------- FETCH · COBRE COMEX HG=F (v7.2) -------------------------
def fetch_hg_yahoo():
    """Futuro COMEX cobre contínuo (HG=F) pelo chart do Yahoo — fonte
    principal, mesmo pipeline do GC=F/HO=F/BZ=F."""
    return _fetch_yahoo_future("HG=F", YAHOO_HG_URL)

def fetch_hg_yahoo_q2():
    """HG=F host reserva."""
    return _fetch_yahoo_future("HG=F", YAHOO_HG_URL_Q2)

def fetch_hg_fxempire():
    """Fallback do cobre: SSR da página /commodities/copper do FXEmpire.
    Blob react-query (mesmo mecanismo do HO/Brent) com o marker único
    '"vendorSymbol":"HG"'; o quote vem DIRETO no data (last/change/
    percentChange/previousClose/high/low/lastUpdate/futuresMonth/
    openInterest). Diferente do HO: AQUI usa-se o top-level — ele espelha
    o contrato mais líquido (dez/26, OI 171.866 vs 1.363 do front set/26,
    conferido ao vivo), que é o benchmark que o TE também segue."""
    html = _http_get(FXE_COPPER_URL, {"User-Agent": BROWSER_UA},
                     timeout=25).decode("utf-8", "replace")
    q = _fxe_segment(html, '"vendorSymbol":"HG"')
    price = _to_float(q.get("last"))
    if not price or price < HG_USD_LO or price > HG_USD_HI:
        raise ValueError("FXEmpire sem preço válido")
    pct = _to_float(q.get("percentChange"))
    prev = _to_float(q.get("previousClose"))
    if pct is None and prev and prev > 0:
        pct = (price / prev - 1.0) * 100.0
    return {"price": price,
            "pct": pct,
            "day_chg": _to_float(q.get("change")),
            "prev_close": prev,
            "high": _to_float(q.get("high")),
            "low": _to_float(q.get("low")),
            "oi": _to_float(q.get("openInterest")),
            "month": q.get("futuresMonth") or "",
            "vendor_ts": q.get("lastUpdate") or "",
            "name": q.get("name") or "",
            "src": "FXEmpire/Oanda", "ts": time.time()}

def fetch_hg_te():
    """Fallback 2 do cobre: scrape do SSR do Trading Economics (referência
    CFD do contrato principal; mesmo scraper do HO=F/ureia/sulfur)."""
    return {**_fetch_te_commodity(TE_COPPER_URL, HG_USD_HI), "ts": time.time()}

def fetch_copper():
    """Futuro COMEX cobre (HG=F), US$/lb. Cadeia (v7.2): Yahoo-q1 ->
    Yahoo-q2 -> FXEmpire -> TradingEconomics -> cache (a camada de cima
    mantém). Todas sem chave; cada fonte com cooldown próprio: fallback
    que salva NÃO anistia a primária morta; 429 conta como falha dupla.
    Falha isolada das demais seções."""
    cands = (
        ("Yahoo-HG-q1", fetch_hg_yahoo, HG_REFETCH),
        ("Yahoo-HG-q2", fetch_hg_yahoo_q2, HG_REFETCH),
        ("FXEmpire-HG", fetch_hg_fxempire, HG_REFETCH),
        ("TE-HG", fetch_hg_te, HG_REFETCH),
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
    raise RuntimeError("cobre COMEX sem fonte viva (" + "; ".join(errs) + ")")

# ------------------- FETCH · COBRE SHFE CU0 (China, v7.3) --------------------
# Cobre 沪铜 (SHFE, CNY/t). Cadeia espelhada no SC (v6.8): Sina ->
# futsseapi -> push2delay -> cache; a conversão US$/lb acontece no
# fetch_cu_shfe com o câmbio do ciclo (regra do enxofre/SC: nada de
# USDCNY velho). Cada fonte com cooldown próprio.
def _cu_ok(v):
    return bool(v and CU_CNY_LO < float(v) < CU_CNY_HI)

def fetch_cu_sina():
    """Contínuo CU0 da SHFE pela Sina (nf_CU0, mesmo pipeline do nf_SC0).
    f[8]=último, f[27]=昨结算 (settlement anterior). pct vs settlement =
    convenção chinesa; sem settlement parseável (ou pct fora do limite
    diário) o registro volta SEM pct — nunca pct errado."""
    txt = _http_get(SINA_URL_FMT.format(codes=SINA_CU_CODE),
                    {"Referer": SINA_REFERER}).decode("gbk", "replace")
    m = re.search(r'hq_str_' + SINA_CU_CODE + r'="([^"]*)"', txt)
    if not m:
        raise ValueError("resposta Sina nf_CU0 sem payload")
    f = m.group(1).split(",")
    last = _to_float(f[8] if len(f) > 8 else None)
    if not _cu_ok(last):
        raise ValueError("Sina nf_CU0 sem preço válido")
    prev = _to_float(f[27] if len(f) > 27 else None)
    pct = None
    if _cu_ok(prev) and abs(last / prev - 1.0) * 100.0 <= CU_PCT_LIMIT:
        pct = (last / prev - 1.0) * 100.0
    return {"price": last, "pct": pct,
            "prev_close": (prev if _cu_ok(prev) else None),
            "src": "Sina nf_CU0", "ts": time.time()}

def fetch_cu_futsse():
    """沪铜主连 (cum) na API interna do Eastmoney (futsseapi). p=último,
    j=昨结算 (settlement) — mesma convenção da Sina. Série EMENDADA: o
    nível pode divergir ~0,4% do contrato cru (pct interno consistente)."""
    d = _get_json(EM_CU_FUTSSE_URL).get("qt") or {}
    last, prev = _to_float(d.get("p")), _to_float(d.get("j"))
    if not _cu_ok(last):
        raise ValueError("futsseapi cum sem preço válido")
    pct = None
    if _cu_ok(prev) and abs(last / prev - 1.0) * 100.0 <= CU_PCT_LIMIT:
        pct = (last / prev - 1.0) * 100.0
    return {"price": last, "pct": pct, "prev_close": (prev if _cu_ok(prev) else None),
            "name": d.get("name") or "", "src": "Eastmoney (futsseapi)",
            "ts": time.time()}

def fetch_cu_push2():
    """Último degrau Eastmoney: push2delay 113.cum. O f43 vem na escala
    f152 (casas decimais do instrumento — RELATORIO: preço = f43/10^f152;
    SHFE cum tem 2 casas -> f43/100). O host é instável (502 intermitente)
    e o f170 calcula vs limite -> degrau de preço puro: pct sempre None.
    A escala é resolvida por f152 com varredura de faixa como reserva
    (divisor único que caiba em CU_CNY_LO..HI)."""
    url = EM_CU_PUSH2_URL.format(secid=EM_CU_SECID)
    data = _get_json(url).get("data") or {}
    f43 = _to_float(data.get("f43"))
    if f43 is None:
        raise ValueError("push2delay cum sem f43")
    f152 = _to_float(data.get("f152"))
    divs = ([10 ** int(f152)] if (f152 is not None and f152 >= 0)
            else []) + [100, 10, 1000, 1, 10000]
    for div in divs:
        price = f43 / div
        if _cu_ok(price):
            return {"price": price, "pct": None, "prev_close": None,
                    "src": "Eastmoney (push2delay)", "ts": time.time()}
    raise ValueError("push2delay cum com preço fora de faixa")

def _cu_usd(price_cny, fx):
    """CNY/t -> US$/lb com o câmbio do ciclo. Exige câmbio PRESENTE e com
    até FX_MAX_AGE (mesma regra da derivação do BRL/SC/enxofre). Sem
    câmbio fresco devolve (None, None) — a UI mostra o CNY/t cru."""
    if not (fx and fx.get("usdcny") and _fx_fresh(fx)):
        return None, None
    rate = float(fx["usdcny"])
    if rate <= 0:
        return None, None
    usd_t = float(price_cny) / rate
    if not (CU_CNY_LO / rate < usd_t < CU_CNY_HI / rate):
        return None, None
    return usd_t / LB_PER_TON, rate

def fetch_cu_shfe(fx):
    """Cobre SHFE CU0 (China), exibição US$/lb. Cadeia (v7.3): Sina ->
    Eastmoney futsseapi -> Eastmoney push2delay -> cache (a camada de
    cima mantém). Cada fonte com cooldown próprio; o primeiro degrau vivo
    converte com o câmbio do ciclo (fx) e preserva o CNY original
    ('cny_price', 'usdcny_used'). Sem câmbio fresco o registro volta em
    CNY cru (flag 'cny') — nunca com taxa velha. Falha isolada."""
    errs = []
    for name, fn, iv in (("Sina-CU", fetch_cu_sina, CU_REFETCH),
                         ("Futsse-CU", fetch_cu_futsse, CU_REFETCH),
                         ("EM-Push-CU", fetch_cu_push2, CU_REFETCH)):
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            continue
        try:
            r = fn()
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, iv, str(e))
            continue
        p_cny = r.get("price")
        if not _cu_ok(p_cny):
            errs.append(f"{name}: valor CNY fora de faixa ({p_cny})")
            _src_cooldown(name, iv, "valor fora de faixa")
            continue
        _src_clear(name)
        usd, rate = _cu_usd(p_cny, fx)
        if usd is None:
            r["cny"] = True                  # câmbio velho/ausente: cru
        else:
            r["cny_price"] = p_cny
            r["price"] = round(usd, 4)
            r["usdcny_used"] = rate
        return r
    raise RuntimeError("cobre SHFE sem fonte viva (" + "; ".join(errs) + ")")

# ------------------- FETCH · CRUDE URALS (Rússia, v7.0) ----------------------
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
    delay = _urals_delay(mdelay.group(1) if mdelay else "")
    if delay.endswith("d"):      # texto em dias: data real (stamp) é a verdade
        delay = _day_delay(day) or delay
    return {"price": price, "pct": pct, "day_chg": chg, "prev_close": prev,
            "delay": delay,
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
    delay = _urals_delay(update)
    if delay.endswith("d"):      # texto em dias: data real do ponto é a verdade
        delay = _day_delay(day) or delay
    return {"price": price, "pct": pct,
            "day_chg": (round(price - prev, 2) if prev else None),
            "prev_close": prev, "delay": delay, "day": day}

def fetch_urals_json():
    """Fallback do Urals: quote JSON do freewidgets (blend 4466)."""
    return {**_oilprice_json_quote(URALS_BLEND_ID),
            "src": "OilPrice.com (freewidgets)", "ts": time.time()}

def _day_delay(day):
    """Data ISO do dado ('2026-09-16') -> delay '1d' (diff p/ hoje UTC).
    O atraso vem da data real da avaliação, não de texto fixo da fonte."""
    if not day:
        return None
    try:
        dd = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        return None
    n = (datetime.now(timezone.utc).date() - dd).days
    return f"{n}d" if n >= 0 else None

def fetch_urals_te():
    """Degrau 1 do Urals (v7.0): spot OTC/CFD espelhado no TradingEconomics
    (scrape market_last, mesmo scraper do HO=F/ureia/sulfur). É a MESMA
    avaliação que o OilPrice repassa com 2 dias; o TE publica T+1
    (conferido ao vivo 17/09/2026: TE 121.61 de 16/09 vs OilPrice 111.77
    de 15/09 no mesmo instante)."""
    d = _fetch_te_commodity(TE_URALS_URL, 500)
    return {**d, "delay": _day_delay(d.get("day"))}

def fetch_urals_minfin():
    """Degrau 2 do Urals (v7.0): tabela diária do minfin.com.ua (espelho
    da mesma avaliação; GET puro sem chave, decimal com vírgula). A
    linha 'atual' vem logo após 'составляют:' — 1ª célula = data
    dd.mm.yyyy, depois <big>121,61</big>&nbsp;USD/bbl, Δ$ e Δ%."""
    html = _http_get(MINFIN_URALS_URL, {"User-Agent": BROWSER_UA},
                     timeout=30).decode("utf-8", "replace")
    m = re.search(r"составляют.*?<tr><td>(\d{2})\.(\d{2})\.(\d{4}).*?</td>\s*"
                  r"<td><big>([0-9.,]+)</big>&nbsp;USD/bbl</td>\s*"
                  r"<td[^>]*><small class='d-[a-z]+'>([-+]?[0-9.,]+)</small>"
                  r"</td>\s*<td[^>]*><small class='d-[a-z]+'>([-+]?[0-9.]+)%"
                  r"</small></td>", html, re.S)
    if not m:
        raise ValueError("minfin sem linha atual do Urals")
    price = _to_float(m.group(4).replace(",", "."))
    chg = _to_float(m.group(5).replace(",", "."))
    pct = _to_float(m.group(6))
    if not price or price < 1 or price > 500:
        raise ValueError("minfin com preço inválido")
    day = (datetime.strptime(f"{m.group(1)}.{m.group(2)}.{m.group(3)}",
                             "%d.%m.%Y").date().isoformat())
    prev = round(price - chg, 2) if chg else None
    if pct is None and prev and prev > 0:
        pct = (price / prev - 1.0) * 100.0
    return {"price": price, "pct": pct, "day_chg": chg, "prev_close": prev,
            "day": day, "delay": _day_delay(day),
            "src": "minfin.com.ua", "ts": time.time()}

def fetch_urals():
    """Crude Urals (blend de exportação russo), US$/barril. Cadeia (v7.0):
    TradingEconomics urals-oil (T+1) -> minfin.com.ua (T+1) -> OilPrice.com
    tabela (T+2) -> OilPrice.com freewidgets (T+2). Cada fonte com
    cooldown próprio: fallback que salva NÃO anistia a primária morta.
    Avaliação spot com atraso; falha isolada das demais seções."""
    errs = []
    for name, fn, iv in (("TE-Urals", fetch_urals_te, URALS_REFETCH),
                         ("minfin-Urals", fetch_urals_minfin, URALS_REFETCH),
                         ("OilPrice-table", fetch_urals_table, URALS_REFETCH),
                         ("OilPrice-json", fetch_urals_json, URALS_REFETCH)):
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            continue
        try:
            r = fn()
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, iv, str(e))
            continue
        _src_clear(name)
        return r
    raise RuntimeError("crude Urals sem fonte (" + "; ".join(errs) + ")")

# --------------------- FETCH · CRUDE MURBAN (v6.9) ---------------------------
def fetch_murban_table():
    """Preço do Murban na tabela principal do OilPrice.com — linha
    data-name='Murban-Crude' (blend_id 4464; avaliação ADNOC com delay de
    minutos; conferido ao vivo: 118.80, Δ -5.01, 16-Minute Delay)."""
    return _oilprice_row("Murban")

def fetch_murban_json():
    """Fallback do Murban: quote JSON do freewidgets (blend 4464) — a
    mesma mecânica (CSRF + X-Requested-With) do fallback do Urals/Brent."""
    return {**_oilprice_json_quote(MURBAN_BLEND_ID),
            "src": "OilPrice.com (freewidgets)", "ts": time.time()}

def fetch_murban():
    """Crude Murban (Abu Dhabi/ADNOC), US$/barril. Cadeia (v6.9):
    OilPrice.com tabela (GET) -> OilPrice.com freewidgets (POST JSON com
    CSRF). Avaliação com delay de minutos; falha isolada das demais."""
    errs = []
    for fetcher in (fetch_murban_table, fetch_murban_json):
        try:
            return fetcher()
        except Exception as e:
            errs.append(f"{fetcher.__name__}: {e}")
    raise RuntimeError("crude Murban sem fonte (" + "; ".join(errs) + ")")

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

# -------------------- FETCH · CRUDE SC (Xangai INE, v6.8) --------------------
# Fontes testadas ao vivo (2026-09-17): Yahoo sem SC=F, TV sem futuros da
# INE e SunSirs "Crude oil" = fechamento do Brent (base errada). Cadeia
# inteira em CNY/bbl; a conversão US$/bbl acontece no fetch_sc com o câmbio
# do ciclo (regra do enxofre: nada de USDCNY velho).
def _sc_ok(v):
    return bool(v and SC_CNY_LO < float(v) < SC_CNY_HI)

def fetch_sc_sina():
    """Contínuo SC0 da INE pela Sina (nf_SC0, mesmo pipeline do nf_AU0).
    f[8]=último, f[10]=limite-up (PEGADINHA — nunca prev), f[27]=昨结算
    (settlement anterior). pct vs settlement = convenção chinesa; sem
    settlement parseável o registro volta sem pct (nunca pct errado)."""
    txt = _http_get(SINA_URL_FMT.format(codes=SINA_SC_CODE),
                    {"Referer": SINA_REFERER}).decode("gbk", "replace")
    m = re.search(r'hq_str_' + SINA_SC_CODE + r'="([^"]*)"', txt)
    if not m:
        raise ValueError("resposta Sina nf_SC0 sem payload")
    f = m.group(1).split(",")
    last = _to_float(f[8] if len(f) > 8 else None)
    if not _sc_ok(last):
        raise ValueError("Sina nf_SC0 sem preço válido")
    prev = _to_float(f[27] if len(f) > 27 else None)
    pct = None
    if _sc_ok(prev) and abs(last / prev - 1.0) * 100.0 <= SC_PCT_LIMIT:
        pct = (last / prev - 1.0) * 100.0
    return {"price": last, "pct": pct,
            "prev_close": (prev if _sc_ok(prev) else None),
            "settle_ref": (_to_float(f[27]) if len(f) > 27 else None),
            "src": "Sina nf_SC0", "ts": time.time()}

def fetch_sc_futsse():
    """原油主连 (scm) na API interna do Eastmoney (futsseapi). p=último,
    j=昨结算 (settlement) — mesma convenção da Sina (valores batem)."""
    d = _get_json(EM_SC_FUTSSE_URL).get("qt") or {}
    last, prev = _to_float(d.get("p")), _to_float(d.get("j"))
    if not _sc_ok(last):
        raise ValueError("futsseapi scm sem preço válido")
    pct = None
    if _sc_ok(prev) and abs(last / prev - 1.0) * 100.0 <= SC_PCT_LIMIT:
        pct = (last / prev - 1.0) * 100.0
    return {"price": last, "pct": pct, "prev_close": (prev if _sc_ok(prev) else None),
            "name": d.get("name") or "", "src": "Eastmoney (futsseapi)",
            "ts": time.time()}

def fetch_sc_push2():
    """Último degrau Eastmoney: push2delay 142.scm (f43 x10, tick 0,1 CNY).
    O f170 da INE calcula vs LIMITE-UP (conferido: -5,79% contra 805,0) ->
    NÃO vira pct. Degrau de preço puro: pct sempre None."""
    d = _get_json(EASTMONEY_FMT.format(secid=EM_SC_SECID))
    data = d.get("data") or {}
    f43 = _to_float(data.get("f43"))
    if f43 is None:
        raise ValueError("push2delay scm sem f43")
    price = f43 / 10.0
    if not _sc_ok(price):
        raise ValueError("push2delay scm com preço inválido")
    return {"price": price, "pct": None, "prev_close": None,
            "src": "Eastmoney (push2delay)", "ts": time.time()}

def _sc_usd(price_cny, fx):
    """CNY/bbl -> US$/bbl com o câmbio do ciclo. Exige câmbio PRESENTE e
    com até FX_MAX_AGE (mesma regra da derivação do BRL/enxofre). Sem
    câmbio fresco devolve (None, None) — a UI mostra o CNY/bbl cru."""
    if not (fx and fx.get("usdcny") and _fx_fresh(fx)):
        return None, None
    rate = float(fx["usdcny"])
    if rate <= 0:
        return None, None
    usd = float(price_cny) / rate
    return (usd if SC_CNY_LO / rate < usd < SC_CNY_HI / rate else None), rate

def fetch_sc(fx):
    """Crude SC (Xangai INE), exibição US$/bbl. Cadeia (v6.8): Sina ->
    Eastmoney futsseapi -> Eastmoney push2delay -> cache (camada de cima
    mantém). Cada fonte com cooldown próprio; o primeiro degrau vivo
    converte com o câmbio do ciclo (fx) e preserva o CNY original
    ('cny_price', 'usdcny_used'). Sem câmbio fresco o registro volta em
    CNY cru (flag 'cny') — nunca com taxa velha."""
    errs = []
    for name, fn, iv in (("Sina-SC", fetch_sc_sina, SC_REFETCH),
                         ("Futsse-SC", fetch_sc_futsse, SC_REFETCH),
                         ("EM-Push-SC", fetch_sc_push2, SC_REFETCH)):
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            continue
        try:
            r = fn()
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, iv, str(e))
            continue
        p_cny = r.get("price")
        if not _sc_ok(p_cny):
            errs.append(f"{name}: valor CNY fora de faixa ({p_cny})")
            _src_cooldown(name, iv, "valor fora de faixa")
            continue
        _src_clear(name)
        usd, rate = _sc_usd(p_cny, fx)
        if usd is None:
            r["cny"] = True                  # câmbio velho/ausente: cru
        else:
            r["cny_price"] = p_cny
            r["price"] = round(usd, 4)
            r["usdcny_used"] = rate
        return r
    raise RuntimeError("crude SC sem fonte viva (" + "; ".join(errs) + ")")

# ---------------------- FETCH · UREIA (fertilizante, v6.6) -------------------
def fetch_urea_te():
    """Spot diário da ureia no Trading Economics (scrape market_last — o
    mesmo scraper do HO=F/Brent-TE). O TE espelha o granular FOB Golfo
    EUA (conferido: 460.00 == contínuo CBOT UFV1! 460.0 no mesmo dia)."""
    return {**_fetch_te_commodity(TE_UREA_URL, 2000), "ts": time.time()}

def _tv_quote(ticker):
    """Quote de um símbolo no scanner PÚBLICO do TradingView — POST JSON
    em /global/scan, sem chave (funciona até com o UA default do widget;
    testado com e sem Origin). Resposta: {"data":[{"s":..., "d":[...]}]}
    em que "d" segue a ORDEM das colunas pedidas (close, change,
    prev_close_price); valor que o TV não tem vem null."""
    body = json.dumps({"symbols": {"tickers": [ticker],
                                   "query": {"types": []}},
                       "columns": ["close", "change", "prev_close_price"]}
                      ).encode("utf-8")
    req = urllib.request.Request(
        TV_SCAN_URL, data=body,
        headers={"User-Agent": BROWSER_UA, "Accept": "application/json",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=NET_TIMEOUT + 7) as r:
        d = json.loads(r.read().decode("utf-8"))
    rows = d.get("data") or []
    if not rows or not isinstance((rows[0] or {}).get("d"), list):
        raise ValueError(f"TV {ticker} sem linha")
    arr = rows[0]["d"]
    price = _to_float(arr[0]) if len(arr) >= 1 else None
    if not price or price < 10 or price > 2000:      # ureia: 100-1100 hist.
        raise ValueError(f"TV {ticker} sem preço válido")
    chg = _to_float(arr[1]) if len(arr) >= 2 else None
    prev = _to_float(arr[2]) if len(arr) >= 3 else None
    if prev is None and chg:
        prev = round(price - chg, 4)
    pct = (price / prev - 1.0) * 100.0 if (prev and prev > 0) else None
    return {"price": price, "pct": pct, "day_chg": chg, "prev_close": prev,
            "src": "TradingView", "ts": time.time()}

def fetch_urea_tv_usgulf():
    """Fallback 1 do spot: contínuo CBOT UFV1! no TV — a MESMA base do TE."""
    return _tv_quote("CBOT:UFV1!")

def fetch_urea_tv_cfr():
    """Fallback do CFR Brasil: contínuo CBOT UFB1! no TV (o mesmo ativo
    do futuro UFB=F do Yahoo; scanner independente)."""
    return _tv_quote("CBOT:UFB1!")

_PINK = {"series": None, "ts": 0.0}      # série mensal parseada (cache proc.)
_PINK_LOCK = threading.Lock()

def _pinksheet_xlsx_url():
    """URL atual do xlsx mensal do Pink Sheet. O caminho tem um hash de
    documento que o World Bank troca de tempos em tempos — descobre na
    página oficial; se ela falhar, usa a URL conhecida (reserva)."""
    try:
        html = _http_get(WB_CM_PAGE, {"User-Agent": BROWSER_UA},
                         timeout=20).decode("utf-8", "replace")
        m = re.search(r"https://thedocs\.worldbank\.org/"
                      r"[^\"'\s]+CMO-Historical-Data-Monthly\.xlsx", html)
        if m:
            return m.group(0)
        log("pink sheet: página oficial sem link do xlsx")
    except Exception as e:
        log(f"pink sheet: página oficial falhou ({e})")
    return WB_CM_XLSX

_PINK_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

def _pinksheet_parse(raw):
    """XLSX do Pink Sheet -> série mensal da ureia [(('YYYY-MM', valor))].
    Só stdlib: zip + XML. Planilha "Monthly Prices" (nomes, r:id no
    workbook.xml); cabeçalho = linha que tem a célula 'Urea' (com espaço
    no fim); valor = última célula numérica da coluna (células '…'/vazias
    pulam). US$/mt f.o.b. Oriente Médio (antes: Black Sea até 2022)."""
    z = zipfile.ZipFile(io.BytesIO(raw))
    # workbook.xml: nome da planilha -> rId; rels: rId -> arquivo
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {}
    for rel in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")):
        rels[rel.get("Id")] = rel.get("Target")
    sheet = None
    for sh in wb.iter(f"{_PINK_NS}sheet"):
        if sh.get("name") == "Monthly Prices":
            target = rels.get(sh.get(f"{{http://schemas.openxmlformats.org/"
                                     f"officeDocument/2006/relationships}}id"))
            break
    else:
        raise ValueError("pink sheet: sem planilha 'Monthly Prices'")
    if not target:
        raise ValueError("pink sheet: rel da planilha ausente")
    strings = []
    try:
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")
                                ).iter(f"{_PINK_NS}si"):
            strings.append("".join(t.text or "" for t in si.iter(f"{_PINK_NS}t")))
    except KeyError:
        pass
    sh = ET.fromstring(z.read("xl/" + target.lstrip("/")))
    urea_col, data_rows = None, []
    for row in sh.iter(f"{_PINK_NS}row"):
        cells = {}
        for c in row.iter(f"{_PINK_NS}c"):
            ref = c.get("r") or ""
            col = re.match(r"([A-Z]+)", ref)
            if not col:
                continue
            v = c.find(f"{_PINK_NS}v")
            if c.get("t") == "s" and v is not None:
                val = strings[int(v.text)] if int(v.text) < len(strings) else ""
            elif v is not None:
                val = v.text
            else:
                val = None
            cells[col.group(1)] = val
        if urea_col is None:
            for col, val in cells.items():
                if val and val.strip().lower() == "urea":
                    urea_col = col
                    break
        elif cells.get("A"):
            data_rows.append((cells.get("A"), cells.get(urea_col)))
    if not urea_col:
        raise ValueError("pink sheet: linha 'Urea' não encontrada")
    pts = []
    for period, val in data_rows:
        m = re.match(r"^(\d{4})M(\d{2})$", str(period or ""))
        if not m:
            continue
        try:
            price = float(val)
        except (TypeError, ValueError):
            continue                       # '…', vazio
        if not price > 0:
            continue
        pts.append((f"{m.group(1)}-{m.group(2)}", price))
    pts.sort()
    if not pts:
        raise ValueError("pink sheet: sem pontos válidos de ureia")
    return pts

def _pinksheet_series():
    """Série mensal cacheada no processo (xlsx ~600 KB, atual 1x/mês).
    Thread-safe (poller x popup de gráfico disputam o mesmo cache)."""
    with _PINK_LOCK:
        if _PINK["series"] and time.time() - _PINK["ts"] < UREA_PINK_TTL:
            return _PINK["series"]
        raw = _http_get(_pinksheet_xlsx_url(), {"User-Agent": BROWSER_UA},
                        timeout=45)
        ser = _pinksheet_parse(raw)
        _PINK["series"] = ser
        _PINK["ts"] = time.time()
        return ser

def fetch_urea_pink():
    """Fallback 2 do spot: último valor mensal do Pink Sheet (f.o.b.
    Oriente Médio, US$/mt). BASE DIFERENTE do spot diário (Golfo EUA) —
    o rodapé mostra 'mensal' e a data da série."""
    ser = _pinksheet_series()
    day, price = ser[-1]
    prev = ser[-2][1] if len(ser) >= 2 else None
    return {"price": price, "pct": None, "day_chg": None, "prev_close": prev,
            "day": day, "mensal": True,
            "src": "WB Pink Sheet (mensal)", "ts": time.time()}

def _urea_chain(key, cands):
    """Cadeia genérica da ureia (padrão v6.4): cada fonte com cooldown
    próprio; degrau vivo salva; cadeia morta levanta com os erros."""
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
    raise RuntimeError(key + " sem fonte viva (" + "; ".join(errs) + ")")

def fetch_urea_me():
    """Uréia (spot intl.), US$/t. Cadeia (v6.6): TE -> TV UFV1! -> Pink
    Sheet mensal -> cache (camada de cima mantém)."""
    return _urea_chain("uréia (spot)", (
        ("TE-UREA", fetch_urea_te, UREA_REFETCH),
        ("TV-UF", fetch_urea_tv_usgulf, UREA_REFETCH),
        ("Pink-UREA", fetch_urea_pink, UREA_REFETCH),
    ))

def fetch_urea_br_yahoo():
    """Futuro CBOT/CME ureia CFR Brasil (UFB=F) pelo chart do Yahoo —
    fonte principal, mesmo pipeline do GC=F/HO=F/BZ=F."""
    return _fetch_yahoo_future("UFB=F", YAHOO_UREA_BR_URL)

def fetch_urea_br_yahoo_q2():
    """UFB=F host reserva."""
    return _fetch_yahoo_future("UFB=F", YAHOO_UREA_BR_URL_Q2)

def fetch_urea_br():
    """Uréia CFR Brasil (futuro UFB=F), US$/t. Cadeia (v6.6): Yahoo-q1 ->
    Yahoo-q2 -> TradingView UFB1! -> cache."""
    return _urea_chain("uréia CFR Brasil", (
        ("Yahoo-UFB-q1", fetch_urea_br_yahoo, UREA_REFETCH),
        ("Yahoo-UFB-q2", fetch_urea_br_yahoo_q2, UREA_REFETCH),
        ("TV-UFB", fetch_urea_tv_cfr, UREA_REFETCH),
    ))

def _hist_urea_me(days):
    """Série MENSAL do Pink Sheet p/ o gráfico do spot. Janela < ~2 meses
    não tem 2 pontos mensais -> levanta (o fetch_history cai pro log
    local). Datas '2026M08' -> '2026-08'."""
    days = int(days)
    ser = _pinksheet_series()
    cut = (datetime.now(timezone.utc) - timedelta(days=days)
           ).strftime("%Y-%m")
    pts = [(d, v) for d, v in ser if d >= cut]
    if len(pts) < 2:
        raise ValueError(f"Pink Sheet: {len(pts)} ponto(s) em {days}d")
    return pts, "WB Pink Sheet (mensal)"

# ----------------------- FETCH · ENXOFRE (v6.7) ------------------------------
# Enxofre elemental spot da China. Só existe público em CNY/t (o USD spot
# internacional não é publicado em nenhuma fonte grátis — ver comentário do
# CONFIG). Cadeia: TE -> SunSirs -> cache; conversão US$/t SÓ com câmbio
# fresco (nada de USDCNY velho: usa o fx do ciclo, mesmas regras da
# derivação do BRL).
def fetch_sulfur_te():
    """Enxofre spot CN no TradingEconomics (scrape market_last, o mesmo
    scraper da ureia/HO=F). Unit do TE: CNY/T — preço fica CRUO em CNY;
    a conversão US$/t acontece no fetch_sulfur com o câmbio do ciclo."""
    return {**_fetch_te_commodity(TE_SULFUR_URL, SULFUR_CNY_HI), "ts": time.time()}

def _sunsirs_page(url):
    """HTML da página de produto do SunSirs com o anti-bot HW_CHECK
    replicado. O 1º GET volta 200 com um script que define o cookie
    HW_CHECK=<hash de 32 hex> e recarrega (nenhum dado); extraímos o hash
    da própria resposta e repetimos o GET com o cookie -> página real.
    urllib puro (header Cookie); sem o cookie a página nunca abre."""
    html = _http_get(url, {"User-Agent": BROWSER_UA},
                     timeout=20).decode("utf-8", "replace")
    if '"HW_CHECK"' in html:
        m = re.search(r'"([a-f0-9]{32})"', html)
        if not m:
            raise ValueError("SunSirs: check sem hash")
        html = _http_get(url, {"User-Agent": BROWSER_UA,
                               "Cookie": f"HW_CHECK={m.group(1)}"},
                         timeout=20).decode("utf-8", "replace")
    if '"HW_CHECK"' in html:
        raise ValueError("SunSirs: check de 2ª rodada")
    return html

def _sunsirs_table(html, name="Sulfur"):
    """Linhas da tabela de preço diário do SunSirs p/ o produto `name`
    -> [(data 'YYYY-MM-DD', preço CNY/t)] em ordem de aparição. A tabela
    traz ['Produto','Setor','Preço','Data']; células com '…'/vazio pulam;
    valor fora de SULFUR_CNY_LO..HI é rejeitado."""
    pts = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(cells) < 4 or cells[0] != name:
            continue
        try:
            v = float(cells[2].replace(",", ""))
        except (TypeError, ValueError):
            continue
        if not (SULFUR_CNY_LO < v < SULFUR_CNY_HI):
            continue
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", cells[3]):
            continue
        pts.append((cells[3], v))
    return pts

def fetch_sulfur_sunsirs():
    """Enxofre spot CN no SunSirs (tabela própria com 6 dias de histórico).
    É o mercado raiz do que o TE espelha (valores batem no mesmo dia)."""
    html = _sunsirs_page(SUNSIRS_SULFUR_URL)
    pts = _sunsirs_table(html)
    if not pts:
        raise ValueError("SunSirs sem linha de Sulfur")
    by = {}
    for d, v in pts:                       # dedupe por data (último ganha)
        by[d] = v
    ser = sorted(by.items())
    day, price = ser[-1]
    prev = ser[-2][1] if len(ser) >= 2 else None
    pct = (price / prev - 1.0) * 100.0 if prev and prev > 0 else None
    return {"price": price, "pct": pct,
            "day_chg": (round(price - prev, 2) if prev else None),
            "prev_close": prev, "day": day, "series6": ser,
            "src": "SunSirs", "ts": time.time()}

def _sulfur_usd(price_cny, fx):
    """Converte CNY/t -> US$/t com o câmbio do ciclo. Exige câmbio PRESENTE
    e com até FX_MAX_AGE (mesma regra da derivação do BRL). Sem câmbio
    fresco devolve (None, None) — a UI mostra o CNY/t cru."""
    if not (fx and fx.get("usdcny") and _fx_fresh(fx)):
        return None, None
    rate = float(fx["usdcny"])
    if rate <= 0:
        return None, None
    usd = float(price_cny) / rate
    return (usd if SULFUR_CNY_LO / rate < usd < SULFUR_CNY_HI / rate
            else None), rate

def fetch_sulfur(fx):
    """Enxofre (spot CN), exibição US$/t. Cadeia (v6.7): TE -> SunSirs ->
    cache (camada de cima mantém). Cada fonte com cooldown próprio; o
    primeiro degrau vivo converte com o câmbio do ciclo (fx) e preserva
    o CNY original ('cny_price', 'usdcny_used'). Sem câmbio fresco o
    registro volta em CNY cru (flag 'cny') — nunca com taxa velha."""
    errs = []
    for name, fn, iv in (
            ("TE-SULFUR", fetch_sulfur_te, SULFUR_REFETCH),
            ("SunSirs-SULFUR", fetch_sulfur_sunsirs, SULFUR_REFETCH)):
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            continue
        try:
            r = fn()
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, iv, str(e))
            continue
        p_cny = r.get("price")
        if not p_cny or not (SULFUR_CNY_LO < p_cny < SULFUR_CNY_HI):
            errs.append(f"{name}: valor CNY fora de faixa ({p_cny})")
            _src_cooldown(name, iv, "valor fora de faixa")
            continue
        _src_clear(name)
        usd, rate = _sulfur_usd(p_cny, fx)
        if usd is None:
            r["cny"] = True                  # câmbio velho/ausente: cru
        else:
            r["cny_price"] = p_cny
            r["price"] = round(usd, 4)
            r["usdcny_used"] = rate
        return r
    raise RuntimeError("enxofre sem fonte viva (" + "; ".join(errs) + ")")

def _hist_sulfur(days):
    """Série p/ o gráfico do enxofre. 7D: tabela do SunSirs (6 pontos
    reais), convertida CNY->US$ com o câmbio de AGORA (nota no rodapé do
    popup). Janela maior: o SunSirs só dá 6 dias -> levanta (o
    fetch_history cai pro log local, que acumula US$/t desde a v6.7)."""
    days = int(days)
    if days > 7:
        raise ValueError(f"SunSirs só dá 6 dias (pedido {days}d)")
    html = _sunsirs_page(SUNSIRS_SULFUR_URL)
    pts_raw = _sunsirs_table(html)
    if len(pts_raw) < 2:
        raise ValueError(f"SunSirs: {len(pts_raw)} ponto(s) na tabela")
    by = {}
    for d, v in pts_raw:
        by[d] = v
    ser = sorted(by.items())
    _, rate = _sulfur_usd(ser[-1][1], fetch_fx())
    if not rate:
        raise ValueError("sem câmbio p/ converter a série SunSirs")
    pts = [(d, round(v / rate, 4)) for d, v in ser]
    if len(pts) < 2:
        raise ValueError("SunSirs: série curta")
    return pts, "SunSirs (CNY÷USDCNY de hoje)"

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

# ------------------- FETCH · YIELD BRASIL NOMINAL (v8.0) ---------------------
def _yield_mat_of_title(title):
    """'Brazil 10-Year' -> '10a' · 'Brazil 3-Month' -> '3m'. O slug da
    linha DISCORDA do título no 8y ('brazil-6-year-bond-yield' com title
    'Brazil 8-Year'), por isso o vencimento vem do título, não do slug."""
    m = re.search(r"Brazil\s+(\d+)\s*-?\s*(Month|Year)", title or "")
    if not m:
        return None
    return (f"{m.group(1)}m" if m.group(2) == "Month" else f"{m.group(1)}a")


def fetch_yield_inv_table(url=INV_BR_BONDS_URL):
    """Curva nominal INTEIRA na tabela SSR do Investing (GET puro, sem
    chave): cada <tr id="pair_N"> traz pid-N-last (yield %), pid-N-
    last_close, pid-N-pc (Δ absoluto — em YIELDS é Δ em pp) e pid-N-time
    (data epoch do dado). Só linhas 'Brazil X-Month/Year' entram; yield
    fora de YIELD_LO..HI é rejeitado."""
    html = _http_get(url, {"User-Agent": BROWSER_UA,
                           "Accept-Language": "en-US,en;q=0.9"},
                     timeout=25).decode("utf-8", "replace")
    out = {}
    for mid in re.findall(r'<tr id="pair_(\d+)">', html):
        s = html.find(f'id="pair_{mid}"')
        if s < 0:
            continue
        e = html.find("</tr>", s)
        row = html[s:e if e > 0 else s + 4000]
        mt = re.search(r'title="(Brazil [\d\w-]+)"', row)
        mat = _yield_mat_of_title(mt.group(1) if mt else "")
        if not mat:
            continue
        mlast = re.search(rf'pid-{mid}-last">([0-9.]+)<', row)
        if not mlast:
            continue
        y = _to_float(mlast.group(1))
        if not y or not (YIELD_LO < y < YIELD_HI):
            continue
        mc = re.search(rf'pid-{mid}-pc">([+-]?[0-9.]+)<', row)
        chg = _to_float(mc.group(1)) if mc else None
        if chg is not None and abs(chg) > 5.0:
            chg = None
        mt2 = re.search(rf'pid-{mid}-time" data-value="(\d+)"', row)
        dt_lbl = (datetime.fromtimestamp(int(mt2.group(1)), timezone.utc)
                  .strftime("%H:%M") if mt2 else None)
        out[mat] = {"yield": y, "chg_pp": chg, "dt": dt_lbl,
                    "src": "Investing.com", "ts": time.time()}
    if not out:
        raise ValueError("Investing: tabela sem yields do Brasil")
    return out


def fetch_yield_te():
    """Degrau do TE — SÓ o 10y (os slugs 1y/2y/3y do TE são 404 genérico,
    validado). market_last + market_daily_Pchg; em títulos o Pchg do TE
    É Δ em PONTOS percentuais (conferido: -0.02 == '0.02 percentage
    points decrease' na descrição deles). Data real do resumo ('...
    eased to 14.17% on September 22, 2026') — regex cobre rose/eased/
    fell/... e não só 'rose to'."""
    html = _http_get(TE_BR_YIELD_URL, {"User-Agent": BROWSER_UA,
                                       "Accept-Language": "en-US,en;q=0.9"},
                     timeout=30).decode("utf-8", "replace")
    m = re.search(r'id="market_last">\s*([0-9.,]+)\s*<', html)
    if not m:
        raise ValueError("TE sem market_last")
    y = float(m.group(1).replace(",", ""))
    if not (YIELD_LO < y < YIELD_HI):
        raise ValueError("TE sem preço válido")
    mp = re.search(r'id="market_daily_Pchg"[^>]*>\s*(-?[0-9.,]+)\s*%', html)
    chg = _to_float(mp.group(1).replace(",", "")) if mp else None
    if chg is not None and abs(chg) > 5.0:
        chg = None
    day = None
    md = re.search(r"(?:rose|eased|fell|climbed|slid|jumped|gained|dropped|"
                   r"declined|advanced|rebounded|tumbled|rallied)\s+to\s+"
                   r"[0-9.,]+%?\s+on\s+([A-Z][a-z]+ \d{1,2}, \d{4})", html)
    if md:
        try:
            day = datetime.strptime(md.group(1), "%B %d, %Y").date().isoformat()
        except ValueError:
            pass
    return {"10a": {"yield": y, "chg_pp": chg, "day": day,
                    "src": "TradingEconomics", "ts": time.time()}}


def fetch_yield_inv_instr(mat):
    """Degrau por vencimento: SSR da página do instrumento no Investing
    (mesmo padrão do CDS v5.8: __NEXT_DATA__ + busca genérica do bloco com
    last/lastUpdateTime). EOD/delayed: o last pode ser o fechamento do dia
    anterior — por isso fica DEPOIS da tabela intraday. changePcr tratado
    como Δ pp (|Δ| > 5 = dado ruim)."""
    meta = YIELD_MATS.get(mat)
    if not meta:
        raise ValueError(f"vencimento desconhecido: {mat}")
    html = _http_get(
        "https://www.investing.com/rates-bonds/" + meta["slug"],
        {"User-Agent": BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"},
        timeout=20).decode("utf-8", "replace")
    mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not mm:
        raise ValueError("página sem __NEXT_DATA__")
    blk = _inv_price_block(json.loads(mm.group(1)))
    if not blk:
        raise ValueError("SSR sem bloco de cotação")
    y = _to_float(blk.get("last"))
    if not y or not (YIELD_LO < y < YIELD_HI):
        raise ValueError("sem preço válido")
    chg = _to_float(blk.get("changePcr"))
    if chg is None:
        lc = _to_float(blk.get("last_close"))
        chg = (y - lc) if (lc and lc > 0) else None
    if chg is not None and abs(chg) > 5.0:
        chg = None
    return {mat: {"yield": y, "chg_pp": chg,
                  "src": "Investing.com (instrumento)", "ts": time.time()}}


def fetch_yield_inv_hist(mat):
    """Último degrau: API historical do Investing p/ o vencimento —
    linha de HOJE entra intraday (pipeline diferente do SSR)."""
    pts, _src = _hist_yield_api(mat, 6)
    dt, y = pts[-1]
    prev = pts[-2][1] if len(pts) >= 2 else None
    chg = None
    if prev and y > 0 and abs(y - prev) <= 5.0:
        chg = round(y - prev, 4)
    return {mat: {"yield": y, "chg_pp": chg, "day": dt,
                  "src": "Investing.com (API)", "ts": time.time()}}


def fetch_yield_br(sel=None):
    """Yield nominal do Brasil (LTN/NTN), % a.a., por vencimento. Cadeia
    (v8.0, cada fonte com cooldown próprio; 429 = falha dupla):
    Investing-tabela (www) -> Investing-tabela (m.) -> TE 10y (pulado se
    o vencimento selecionado não é 10a) -> instrumento (venc. selecionado)
    -> API historical (venc. selecionado) -> cache (a camada de cima
    mantém). O degrau devolve {venc: rec} só do que tem; a camada de cima
    mescla (rec fresco substitui o mesmo vencimento). Falha isolada."""
    sel = sel if sel in YIELD_MATS else YIELD_DEFAULT
    cands = [
        ("Inv-table-YIELD", lambda: fetch_yield_inv_table(INV_BR_BONDS_URL)),
        ("Inv-tableMob-YIELD", lambda: fetch_yield_inv_table(INV_BR_BONDS_URL_M)),
        ("Inv-instr-YIELD", lambda: fetch_yield_inv_instr(sel)),
        ("Inv-hist-YIELD", lambda: fetch_yield_inv_hist(sel)),
    ]
    if sel == "10a":
        cands.insert(2, ("TE-YIELD", fetch_yield_te))
    errs = []
    for name, fn in cands:
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            continue
        try:
            r = fn()
            _src_clear(name)
            if r:
                return r
            errs.append(f"{name}: resposta sem yield")
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, YIELD_REFETCH, str(e))
    raise RuntimeError("yield Brasil sem fonte viva (" + "; ".join(errs) + ")")


# -------------------- FETCH · YIELD EUA NOMINAL (v8.1) ----------------------
def _us_yield_mat_of_title(title):
    """'United States 10-Year' -> '10a' · 'U.S. 20-Year' -> '20a' ·
    'United States 3-Month' -> '3m'. O vencimento vem do title do <a> da
    tabela (o 20y é 'U.S. 20-Year' e os demais 'United States N-Year' —
    os DOIS formatos existem na mesma tabela; e o slug do 20y é 'us-20-
    year-…' sem os pontos de 'u.s.-…'). Só vale se o vencimento estiver
    em US_YIELD_MATS (a tabela também lista 2m/4m, fora da curva pedida)."""
    m = re.search(r"(?:United States|U\.S\.|US)\s+(\d+)\s*-?\s*(Month|Year)",
                  title or "", re.I)
    if not m:
        return None
    mat = (f"{m.group(1)}m" if m.group(2).lower() == "month"
           else f"{m.group(1)}a")
    return mat if mat in US_YIELD_MATS else None


def _us_yield_mat_of_row(row):
    """Vencimento de uma <tr> da tabela: varre TODOS os title="…" do bloco
    (o 1º costuma ser o da flag 'United States', sem prazo; o do <a> traz
    'United States 10-Year' ou 'U.S. 20-Year') e, se nenhum title servir,
    cai pro slug do href ('u.s.-10-year-bond-yield' / 'us-20-year-…')."""
    for t in re.findall(r'title="([^"]+)"', row or ""):
        mat = _us_yield_mat_of_title(t)
        if mat:
            return mat
    m = re.search(r'href="[^"]*rates-bonds/([^"]+)"', row or "")
    if m:
        return _us_yield_mat_of_title(m.group(1).replace("-", " "))
    return None


def fetch_us_yield_inv_table(url=INV_US_BONDS_URL):
    """Curva nominal INTEIRA dos EUA na tabela SSR do Investing (GET puro,
    sem chave): cada <tr id="pair_N"> traz pid-N-last (yield %), pid-N-
    last_close, pid-N-pc (Δ absoluto — em YIELDS é Δ em pp) e pid-N-time
    (data epoch do dado). Só linhas 'United States X-Month/Year' cujo
    vencimento está em US_YIELD_MATS entram (2m/4m da tabela ficam fora);
    yield fora de US_YIELD_LO..HI é rejeitado."""
    html = _http_get(url, {"User-Agent": BROWSER_UA,
                           "Accept-Language": "en-US,en;q=0.9"},
                     timeout=25).decode("utf-8", "replace")
    out = {}
    for mid in re.findall(r'<tr id="pair_(\d+)">', html):
        s = html.find(f'id="pair_{mid}"')
        if s < 0:
            continue
        e = html.find("</tr>", s)
        row = html[s:e if e > 0 else s + 4000]
        mat = _us_yield_mat_of_row(row)
        if not mat:
            continue
        mlast = re.search(rf'pid-{mid}-last">([0-9.]+)<', row)
        if not mlast:
            continue
        y = _to_float(mlast.group(1))
        if not y or not (US_YIELD_LO < y < US_YIELD_HI):
            continue
        mc = re.search(rf'pid-{mid}-pc">([+-]?[0-9.]+)<', row)
        chg = _to_float(mc.group(1)) if mc else None
        if chg is not None and abs(chg) > 5.0:
            chg = None
        mt2 = re.search(rf'pid-{mid}-time" data-value="(\d+)"', row)
        dt_lbl = (datetime.fromtimestamp(int(mt2.group(1)), timezone.utc)
                  .strftime("%H:%M") if mt2 else None)
        out[mat] = {"yield": y, "chg_pp": chg, "dt": dt_lbl,
                    "src": "Investing.com", "ts": time.time()}
    if not out:
        raise ValueError("Investing: tabela sem yields dos EUA")
    return out


def fetch_us_yield_te(mat):
    """Degrau do TE p/ um vencimento — SÓ os que têm página própria
    validados 23/09/2026 (3m/6m/10a/20a/30a; os demais slugs são 404
    genérico; o 10y vive em 'government-bond-yield', o slug
    '10-year-bond-yield' também é 404). market_last + market_daily_Pchg;
    em títulos o Pchg do TE É Δ em PONTOS percentuais (mesma convenção do
    BR, conferida na descrição deles)."""
    meta = US_YIELD_MATS.get(mat) or {}
    te = meta.get("te")
    if not te:
        raise ValueError(f"TE sem página do {mat}")
    html = _http_get(TE_US_YIELD_FMT.format(slug=te),
                     {"User-Agent": BROWSER_UA,
                      "Accept-Language": "en-US,en;q=0.9"},
                     timeout=30).decode("utf-8", "replace")
    m = re.search(r'id="market_last">\s*([0-9.,]+)\s*<', html)
    if not m:
        raise ValueError("TE sem market_last")
    y = float(m.group(1).replace(",", ""))
    if not y or not (US_YIELD_LO < y < US_YIELD_HI):
        raise ValueError("TE sem preço válido")
    mp = re.search(r'id="market_daily_Pchg"[^>]*>\s*(-?[0-9.,]+)\s*%', html)
    chg = _to_float(mp.group(1).replace(",", "")) if mp else None
    if chg is not None and abs(chg) > 5.0:
        chg = None
    day = None
    md = re.search(r"(?:rose|eased|fell|climbed|slid|jumped|gained|dropped|"
                   r"declined|advanced|rebounded|tumbled|rallied)\s+to\s+"
                   r"[0-9.,]+%?\s+on\s+([A-Z][a-z]+ \d{1,2}, \d{4})", html)
    if md:
        try:
            day = datetime.strptime(md.group(1), "%B %d, %Y").date().isoformat()
        except ValueError:
            pass
    return {mat: {"yield": y, "chg_pp": chg, "day": day,
                  "src": "TradingEconomics", "ts": time.time()}}


def fetch_us_yield_inv_instr(mat):
    """Degrau por vencimento: SSR da página do instrumento no Investing
    (mesmo padrão do CDS v5.8: __NEXT_DATA__ + busca genérica do bloco com
    last/lastUpdateTime). EOD/delayed: o last pode ser o fechamento do dia
    anterior — por isso fica DEPOIS da tabela intraday. changePcr tratado
    como Δ pp (|Δ| > 5 = dado ruim)."""
    meta = US_YIELD_MATS.get(mat)
    if not meta:
        raise ValueError(f"vencimento desconhecido: {mat}")
    html = _http_get(
        "https://www.investing.com/rates-bonds/" + meta["slug"],
        {"User-Agent": BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"},
        timeout=20).decode("utf-8", "replace")
    mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not mm:
        raise ValueError("página sem __NEXT_DATA__")
    blk = _inv_price_block(json.loads(mm.group(1)))
    if not blk:
        raise ValueError("SSR sem bloco de cotação")
    y = _to_float(blk.get("last"))
    if not y or not (US_YIELD_LO < y < US_YIELD_HI):
        raise ValueError("sem preço válido")
    chg = _to_float(blk.get("changePcr"))
    if chg is None:
        lc = _to_float(blk.get("last_close"))
        chg = (y - lc) if (lc and lc > 0) else None
    if chg is not None and abs(chg) > 5.0:
        chg = None
    return {mat: {"yield": y, "chg_pp": chg,
                  "src": "Investing.com (instrumento)", "ts": time.time()}}


def fetch_us_yield_inv_hist(mat):
    """Degrau: API historical do Investing p/ o vencimento — linha de HOJE
    entra intraday (pipeline diferente do SSR). Δ = hoje - ontem (pp)."""
    pts, _src = _hist_us_yield_api(mat, 6)
    dt, y = pts[-1]
    prev = pts[-2][1] if len(pts) >= 2 else None
    chg = None
    if prev and y > 0 and abs(y - prev) <= 5.0:
        chg = round(y - prev, 4)
    return {mat: {"yield": y, "chg_pp": chg, "day": dt,
                  "src": "Investing.com (API)", "ts": time.time()}}


def fetch_us_yield_fred():
    """Curva nominal INTEIRA dos EUA no FRED (Treasury CMT oficial, EOD):
    uma chamada fredgraph.csv com as séries DGS* de todos os vencimentos
    (DGS1MO…DGS30). Δ do dia = último - penúltimo (pp). Completa a curva
    quando os degraus de vencimento único não cobrem tudo — sem
    sobrescrever o que já veio fresco deles (ver fetch_us_yield)."""
    pairs = [(m, US_YIELD_MATS[m]["fred"]) for m in
             sorted(US_YIELD_MATS, key=lambda k: US_YIELD_MATS[k]["ordem"])
             if US_YIELD_MATS[m].get("fred")]
    if not pairs:
        raise ValueError("sem séries FRED mapeadas")
    # cosd limita a janela (o CSV completo vem desde 1962 e estoura timeout)
    url = (FRED_CSV_FMT.format(sid=",".join(s for _m, s in pairs))
           + "&cosd=" + (datetime.now(timezone.utc) - timedelta(days=15)
                         ).strftime("%Y-%m-%d"))
    raw = _http_get(url, {"User-Agent": FRED_UA},
                    timeout=40).decode("utf-8", "replace")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if len(lines) < 3:
        raise ValueError("FRED sem série")
    col = {h.strip(): i for i, h in enumerate(lines[0].split(","))}
    last, prev = {}, {}                 # sid -> (dt, v)
    for ln in lines[1:]:
        parts = ln.split(",")
        dt = parts[0].strip()
        for _mat, sid in pairs:
            i = col.get(sid)
            if i is None or i >= len(parts):
                continue
            val = parts[i].strip()
            if not val or val == ".":
                continue
            v = _to_float(val)
            if not v or not (US_YIELD_LO < v < US_YIELD_HI):
                continue
            if sid in last:
                prev[sid] = last[sid]
            last[sid] = (dt, v)
    out = {}
    for mat, sid in pairs:
        if sid not in last:
            continue
        dt, y = last[sid]
        chg = None
        if sid in prev:
            chg = round(y - prev[sid][1], 4)
            if abs(chg) > 5.0:
                chg = None
        out[mat] = {"yield": y, "chg_pp": chg, "day": dt,
                    "src": "FRED", "ts": time.time()}
    if not out:
        raise ValueError("FRED sem yields dos EUA")
    return out


def fetch_us_yield(sel=None):
    """Yield nominal dos EUA (UST: bills ≤1a, notes 2-10a, bonds 20-30a),
    % a.a., por vencimento. Cadeia (v8.1, cada fonte com cooldown próprio;
    429 = falha dupla; nomes com prefixo US p/ não colidir com o BR):
    Investing-tabela (www) -> Investing-tabela (m.) -> TE (só se o
    vencimento selecionado tiver página) -> instrumento -> API historical
    -> FRED (curva inteira, completa sem sobrescrever) -> cache (a camada
    de cima mantém). Tabela e FRED devolvem a curva inteira; os degraus
    de vencimento único devolvem só o selecionado (a camada de cima
    mescla). Falha isolada das demais seções."""
    sel = sel if sel in US_YIELD_MATS else US_YIELD_DEFAULT
    errs = []

    def _try(name, fn):
        if not _src_due(name):
            errs.append(f"{name}: em cooldown")
            return None
        try:
            r = fn()
            _src_clear(name)
            return r or None
        except Exception as e:
            errs.append(f"{name}: {e}")
            _src_cooldown(name, US_YIELD_REFETCH, str(e))
            return None

    # 1-2: curva inteira intraday
    r = _try("Inv-table-USYIELD",
             lambda: fetch_us_yield_inv_table(INV_US_BONDS_URL))
    if r:
        return r
    r = _try("Inv-tableMob-USYIELD",
             lambda: fetch_us_yield_inv_table(INV_US_BONDS_URL_M))
    if r:
        return r

    # 3-5: vencimento selecionado (intraday-ish)
    got = {}
    if (US_YIELD_MATS.get(sel) or {}).get("te"):
        r = _try("TE-USYIELD", lambda: fetch_us_yield_te(sel))
        if r:
            got.update(r)
    if sel not in got:
        r = _try("Inv-instr-USYIELD", lambda: fetch_us_yield_inv_instr(sel))
        if r:
            got.update(r)
    if sel not in got:
        r = _try("Inv-hist-USYIELD", lambda: fetch_us_yield_inv_hist(sel))
        if r:
            got.update(r)

    # 6: FRED completa a curva (EOD) sem sobrescrever o fresco
    r = _try("FRED-USYIELD", fetch_us_yield_fred)
    if r:
        for m, rec in r.items():
            got.setdefault(m, rec)

    if got:
        return got
    raise RuntimeError("yield EUA sem fonte viva (" + "; ".join(errs) + ")")

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

# -------------------- BANDEJA DO SISTEMA (v8.3) --------------------
# System tray via AyatanaAppIndicator3 (GI, pacote do sistema
# gir1.2-ayatana-appindicator3 — zero dependência pip nova).
#
# Decisões do usuário (nada aqui é chute):
#   * biblioteca: Ayatana GI do sistema (pystray NEM é tentado).
#   * minimizar: SÓ via item de menu "Minimizar p/ bandeja"; o X/Sair
#     continua encerrando o processo.
#   * clique no ícone: o Ayatana no GNOME SEMPRE abre o menu (não há
#     sinal de clique-esquerdo para interceptar — validado no ambiente);
#     mostrar/esconder vive no item "Mostrar/Ocultar" do menu da bandeja.
#   * menu da bandeja: Mostrar/Ocultar + Atualizar agora + Ver gráfico
#     (mesmas entradas da janela) + Sair.
#   * ícone: círculo dourado gerado com Pillow em TRAY_ICON_FILE, com
#     fallback para ícone do tema quando o Pillow/geração falhar.
#   * label ao lado do ícone: spot em BRL (R$/g, igual ao widget);
#     USD temporário SÓ se todos os fallbacks do BRL falharem;
#     título/tooltip: BRL + USD (BRL primeiro).
#   * polling/cache/log: seguem rodando com a janela oculta (nada pausa).
#   * boot: SEMPRE inicia minimizado; --show inicia visível (fuga/debug).
#   * falha do Ayatana: NUNCA quebra o app — loga e segue visível como
#     antes; o item de menu vira no-op seguro.
#
# Thread-safety: callbacks Gtk rodam na thread do GLib — NUNCA tocam o
# tkinter direto; tudo é despachado para a thread do Tk via root.after(0).
_TRAY_ID = "gold-widget"

def _tray_icon_path():
    """Caminho do ícone da bandeja; gera o PNG dourado se preciso.

    Retorna (path_ou_nome, eh_arquivo). Nunca levanta: em qualquer
    falha devolve um nome de ícone do tema.
    """
    fallback = ("dialog-information", False)
    try:
        p = TRAY_ICON_FILE
        try:
            # PNG válido = existe, tem tamanho E abre como imagem (um
            # arquivo corrompido/antigo nunca passa daqui: cai na
            # regeneração abaixo em vez de quebrar o indicador).
            if os.path.isfile(p) and os.path.getsize(p) > 100:
                try:
                    from PIL import Image as _VImg
                    with _VImg.open(p) as _v:
                        _v.verify()
                    return (p, True)
                except Exception:
                    pass  # corrompido ou Pillow ausente: regenera/usa tema
        except Exception:
            pass
        try:
            from PIL import Image, ImageDraw
        except Exception as e:
            log(f"bandeja: Pillow indisponível ({e}); usando ícone do tema")
            return fallback
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            # círculo dourado com borda escura + brilho simples
            d.ellipse([4, 4, size - 5, size - 5], fill=(201, 162, 39, 255),
                      outline=(90, 66, 10, 255), width=3)
            d.ellipse([14, 12, size - 22, size - 28], fill=(240, 210, 110, 255))
            tmp = p + ".tmp"
            img.save(tmp, "PNG")
            os.replace(tmp, p)
            return (p, True)
        except Exception as e:
            log(f"bandeja: falha ao gerar ícone ({e}); usando ícone do tema")
            return fallback
    except Exception as e:
        log(f"bandeja: falha inesperada no ícone ({e})")
        return fallback

def _tray_label_and_title(last):
    """(label, titulo) da bandeja a partir do cache. Nunca levanta.

    v8.4: o LABEL é em BRL (R$/g, "R$ 714,32/g", igual ao widget). O USD
    só aparece no label se LITERALMENTE todos os fallbacks do BRL
    falharem (sem brl_price no cache): aí mostra o USD temporário
    ("US$ 4,266.16") até o BRL voltar. O TÍTULO/tooltip mantém os dois,
    com o BRL primeiro ("R$ 714,32/g · US$ 4,266.16").
    """
    try:
        d = last or {}
        usd = d.get("usd_price")
        brl = d.get("brl_price")
        if brl:
            try:
                label = f"R$ {fmt_brl(brl / TROY_OZ_GRAMS)}/g"
            except Exception:
                label = f"R$ {brl}/g"
        elif usd:
            # Último recurso: BRL sem dado (todos os fallbacks do BRL
            # falharam). Mostra USD temporário até o BRL voltar.
            try:
                label = f"US$ {fmt_usd(usd)}"
            except Exception:
                label = f"US$ {usd}"
        else:
            label = "Ouro —"
        parts = []
        if brl:
            try:
                parts.append(f"R$ {fmt_brl(brl / TROY_OZ_GRAMS)}/g")
            except Exception:
                parts.append(f"R$ {brl}/g")
        if usd:
            try:
                parts.append(f"US$ {fmt_usd(usd)}")
            except Exception:
                parts.append(f"US$ {usd}")
        title = "OuroWidget — " + (" · ".join(parts) if parts else "sem dados ainda")
        return (label, title)
    except Exception:
        return ("Ouro —", "OuroWidget")

def _tray_load_gi():
    """Importa AyatanaAppIndicator3+Gtk+GLib via GI. (mod, erro)."""
    try:
        import gi as _gi
        _gi.require_version("AyatanaAppIndicator3", "0.1")
        _gi.require_version("Gtk", "3.0")
        from gi.repository import (  # noqa: F401
            AyatanaAppIndicator3 as _AI, Gtk as _Gtk, GLib as _GLib)
        return (_AI, _Gtk, _GLib), None
    except Exception as e:
        return None, e

class TrayController:
    """Dono do AppIndicator + menu Gtk. Toda ação chega ao app via
    callbacks seguros (root.after) — este objeto nunca toca tkinter."""

    def __init__(self, app):
        self.app = app
        self.AI = None
        self.Gtk = None
        self.GLib = None
        self.ind = None
        self.item_toggle = None
        self.ok = False

    def start(self):
        """Cria o indicador. Retorna True se a bandeja está viva."""
        try:
            mods, err = _tray_load_gi()
            if mods is None:
                log(f"bandeja indisponível (GI Ayatana: {err}); sem tray")
                return False
            AI, Gtk, GLib = mods
            self.AI, self.Gtk, self.GLib = AI, Gtk, GLib
            icon, is_file = _tray_icon_path()
            try:
                if is_file:
                    self.ind = AI.Indicator.new_with_path(
                        _TRAY_ID, os.path.basename(icon),
                        AI.IndicatorCategory.APPLICATION_STATUS,
                        os.path.dirname(icon) or STATE_DIR)
                else:
                    self.ind = AI.Indicator.new(
                        _TRAY_ID, icon,
                        AI.IndicatorCategory.APPLICATION_STATUS)
            except Exception as e:
                log(f"bandeja: falha ao criar indicador ({e})")
                return False
            try:
                label0, title0 = _tray_label_and_title(
                    getattr(self.app, "last", None))
                try:
                    self.ind.set_title(title0)
                except Exception:
                    pass
                try:
                    self.ind.set_label(label0, label0)
                except Exception:
                    pass
                self.ind.set_status(AI.IndicatorStatus.ACTIVE)
            except Exception as e:
                log(f"bandeja: falha ao configurar indicador ({e})")
                return False
            try:
                self.ind.set_menu(self._build_menu())
            except Exception as e:
                log(f"bandeja: falha ao anexar menu ({e})")
                return False
            self.ok = True
            log("bandeja ativa (AyatanaAppIndicator3)")
            return True
        except Exception as e:
            log(f"bandeja: falha inesperada ao iniciar ({e})")
            self.ok = False
            return False

    def _build_menu(self):
        Gtk = self.Gtk
        menu = Gtk.Menu()

        self.item_toggle = Gtk.MenuItem(label="Mostrar")
        self.item_toggle.connect("activate", self._on_toggle)
        menu.append(self.item_toggle)

        mi_upd = Gtk.MenuItem(label="Atualizar agora")
        mi_upd.connect("activate", self._on_update_now)
        menu.append(mi_upd)

        mi_graph = Gtk.MenuItem(label="Ver gráfico")
        submenu = Gtk.Menu()
        try:
            entries = list(self.app.tray_graph_entries())
        except Exception:
            entries = []
        if not entries:
            _none = Gtk.MenuItem(label="(indisponível)")
            _none.set_sensitive(False)
            submenu.append(_none)
        else:
            for lbl, key in entries:
                mi = Gtk.MenuItem(label=lbl)
                mi.connect("activate", self._on_graph, key)
                submenu.append(mi)
        mi_graph.set_submenu(submenu)
        menu.append(mi_graph)

        sep = Gtk.SeparatorMenuItem()
        menu.append(sep)

        mi_quit = Gtk.MenuItem(label="Sair")
        mi_quit.connect("activate", self._on_quit)
        menu.append(mi_quit)

        menu.show_all()
        self._refresh_toggle_label()
        return menu

    # -- callbacks Gtk (thread GLib) -> despacha p/ thread do Tk ---------
    def _tk(self, fn):
        try:
            root = getattr(self.app, "root", None)
            if root is not None:
                root.after(0, fn)
            else:
                fn()
        except Exception:
            try:
                fn()
            except Exception:
                pass

    def _on_toggle(self, _item):
        self._tk(self.app.toggle_visible)

    def _on_update_now(self, _item):
        self._tk(self.app.update_now)

    def _on_graph(self, _item, key):
        self._tk(lambda: self.app.open_history(key))

    def _on_quit(self, _item):
        self._tk(self.app.quit)

    # -- updates vindos da thread do Tk ----------------------------------
    def _refresh_toggle_label(self):
        try:
            if self.item_toggle is None:
                return
            vis = bool(self.app.is_visible())
            self.item_toggle.set_label("Ocultar" if vis else "Mostrar")
        except Exception:
            pass

    def refresh(self):
        """Atualiza label/título + rótulo Mostrar/Ocultar. Nunca levanta;
        quando chamada fora da thread GLib, reagenda via idle_add."""
        try:
            if not self.ok or self.ind is None:
                return
            GLib = self.GLib

            def _do():
                try:
                    label, title = _tray_label_and_title(
                        getattr(self.app, "last", None))
                    try:
                        self.ind.set_title(title)
                    except Exception:
                        pass
                    try:
                        self.ind.set_label(label, label)
                    except Exception:
                        pass
                    self._refresh_toggle_label()
                except Exception as e:
                    log(f"bandeja: falha no refresh ({e})")
                return False

            try:
                GLib.idle_add(_do)
            except Exception:
                _do()
        except Exception as e:
            log(f"bandeja: falha inesperada no refresh ({e})")

    def stop(self):
        try:
            if self.ind is not None and self.AI is not None:
                try:
                    self.ind.set_status(self.AI.IndicatorStatus.PASSIVE)
                except Exception:
                    pass
        except Exception:
            pass
        self.ok = False

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
                    self.app.root.after(0, lambda r=res: self._done(r, None))
                except Exception as ex:
                    # v6.7: `ex` é deletado ao sair do except (cleanup do
                    # Python) — a lambda morria com NameError quando o
                    # callback rodava e o popup ficava eterno no
                    # "carregando…". Bind antecipado (default arg).
                    msg = str(ex)
                    self.app.root.after(0, lambda e=msg: self._done(None, e))

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

        # v7.1 — rolagem oculta: o conteúdo inteiro vive num frame interno
        # (self.body) dentro de um Canvas. NÃO há scrollbar na UI: quando o
        # conteúdo não couber, a roda do mouse rola (yview/xview direto).
        self.canvas = tk.Canvas(self.frame, bg=BG, highlightthickness=0,
                                bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=BG)
        self._body_win = self.canvas.create_window(
            0, 0, window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_cfg)
        self.body.bind("<Configure>", self._on_body_cfg)

        self.l_title = tk.Label(self.body, text="OURO · SPOT", bg=BG,
                                fg=TITLE, font=("DejaVu Sans", 9, "bold"))
        self.l_title.pack(anchor="w", padx=12, pady=(8, 0))

        row_usd = tk.Frame(self.body, bg=BG)
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

        row_brl = tk.Frame(self.body, bg=BG)
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

        self.l_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                              font=("DejaVu Sans", 8))
        self.l_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # --------------- seção CÂMBIO · USD/BRL (v8.2) --------------------
        # Só o valor (mid), estilo do spot do ouro. Sem rodapé/gráfico.
        self.l_fx_title = tk.Label(self.body, text="CÂMBIO · USD/BRL", bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 9, "bold"))
        self.l_fx_title.pack(anchor="w", padx=12, pady=(8, 0))
        self.l_usdbrl = tk.Label(self.body, text="—", bg=BG, fg=TXT_USD,
                                 font=("DejaVu Sans", 13, "bold"))
        self.l_usdbrl.pack(anchor="w", padx=12, pady=(0, 8))

        # --------------- seção COBRE (COMEX HG=F + SHFE CU0, v7.3) --------
        self.copper_frame = tk.Frame(self.body, bg=BG)
        self.copper_frame.pack(anchor="w", padx=12, fill="x")
        self._copper_sig = None
        self._copper_refs = []
        self.l_copper_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                     font=("DejaVu Sans", 7))
        self.l_copper_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # REMOVIDO a pedido do usuário (2026-09-17): seção COMEX · FUTURO (GC=F)
        # REMOVIDO a pedido do usuário (2026-09-17): seção CHINA
        # (BOLSAS SGE/SHFE + REFERÊNCIA Base China Gold + BARRAS DE BANCO)

        # --------------- seção EUA · COMBUSTÍVEL (média de varejo) ---------
        self.us_frame = tk.Frame(self.body, bg=BG)
        self.us_frame.pack(anchor="w", padx=12, fill="x")
        self._us_sig = None
        self._us_refs = []
        self.l_us_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                 font=("DejaVu Sans", 7))
        self.l_us_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ---------------- seção BRASIL · CDS 5 ANOS (v5.7) ----------------
        self.cds_frame = tk.Frame(self.body, bg=BG)
        self.cds_frame.pack(anchor="w", padx=12, fill="x")
        self._cds_sig = None
        self._cds_refs = []
        self.l_cds_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 7))
        self.l_cds_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ------------- seção BRASIL · YIELD NOMINAL (v8.0) -----------------
        # UMA linha (vencimento escolhido no DROPDOWN ▾) + rodapé com a
        # curva inteira. O vencimento fica no dropdown, não em linhas
        # separadas, p/ não inflar o widget.
        self.yield_frame = tk.Frame(self.body, bg=BG)
        self.yield_frame.pack(anchor="w", padx=12, fill="x")
        self._yield_sig = None
        self._yield_refs = []
        self.l_yield_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                    font=("DejaVu Sans", 7))
        self.l_yield_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ------------- seção EUA · YIELD TREASURY (v8.1) --------------------
        # Espelha o yield BR: UMA linha (vencimento no DROPDOWN ▾) + rodapé
        # com a curva inteira. Bills/notes/bonds misturados como no
        # noticiário, com o tipo no nome. Posição: logo abaixo do BR.
        self.us_yield_frame = tk.Frame(self.body, bg=BG)
        self.us_yield_frame.pack(anchor="w", padx=12, fill="x")
        self._us_yield_sig = None
        self._us_yield_refs = []
        self.l_us_yield_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                       font=("DejaVu Sans", 7))
        self.l_us_yield_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # --------------- seção NYMEX · DIESEL HO=F (v6.1) -----------------
        self.ho_frame = tk.Frame(self.body, bg=BG)
        self.ho_frame.pack(anchor="w", padx=12, fill="x")
        self._ho_sig = None
        self._ho_refs = []
        self.l_ho_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                 font=("DejaVu Sans", 7))
        self.l_ho_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # -------------- seção BRENT · CRUDE (benchmark, v6.3) --------------
        self.brent_frame = tk.Frame(self.body, bg=BG)
        self.brent_frame.pack(anchor="w", padx=12, fill="x")
        self._brent_sig = None
        self._brent_refs = []
        self.l_brent_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                    font=("DejaVu Sans", 7))
        self.l_brent_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ------------- seção CHINA · CRUDE SC (XANGAI, v6.8) ---------------
        self.sc_frame = tk.Frame(self.body, bg=BG)
        self.sc_frame.pack(anchor="w", padx=12, fill="x")
        self._sc_sig = None
        self._sc_refs = []
        self.l_sc_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                 font=("DejaVu Sans", 7))
        self.l_sc_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ------------- seção EMIRADOS · CRUDE MURBAN (v6.9) ----------------
        self.murban_frame = tk.Frame(self.body, bg=BG)
        self.murban_frame.pack(anchor="w", padx=12, fill="x")
        self._murban_sig = None
        self._murban_refs = []
        self.l_murban_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                     font=("DejaVu Sans", 7))
        self.l_murban_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # --------------- seção RÚSSIA · CRUDE URALS (v6.2) ----------------
        self.urals_frame = tk.Frame(self.body, bg=BG)
        self.urals_frame.pack(anchor="w", padx=12, fill="x")
        self._urals_sig = None
        self._urals_refs = []
        self.l_urals_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                    font=("DejaVu Sans", 7))
        self.l_urals_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ------------- seção FERTILIZANTE · UREIA (v6.6) -------------------
        self.urea_frame = tk.Frame(self.body, bg=BG)
        self.urea_frame.pack(anchor="w", padx=12, fill="x")
        self._urea_sig = None
        self._urea_refs = []
        self.l_urea_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                   font=("DejaVu Sans", 7))
        self.l_urea_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ---------------- seção ENXOFRE · SPOT CN (v6.7) -------------------
        self.sulfur_frame = tk.Frame(self.body, bg=BG)
        self.sulfur_frame.pack(anchor="w", padx=12, fill="x")
        self._sulfur_sig = None
        self._sulfur_refs = []
        self.l_sulfur_sub = tk.Label(self.body, text="", bg=BG, fg=TXT_DIM,
                                     font=("DejaVu Sans", 7))
        self.l_sulfur_sub.pack(anchor="w", padx=12, pady=(2, 8))

        # ----------------------- menu de botão direito ----------------------
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Atualizar agora", command=self.update_now)
        # dropdown do vencimento do yield (v8.0): radiobuttons; a escolha
        # persiste no cache e o rótulo da linha acompanha
        _ysel0 = self.last.get("yield_sel")
        if _ysel0 not in YIELD_MATS:
            _ysel0 = YIELD_DEFAULT
        self._yield_sel_var = tk.StringVar(value=_ysel0)
        try:
            self.menu_yield = tk.Menu(root, tearoff=0)
            for _mat in sorted(YIELD_MATS,
                               key=lambda k: YIELD_MATS[k]["ordem"]):
                self.menu_yield.add_radiobutton(
                    label=YIELD_MATS[_mat]["nome"], value=_mat,
                    variable=self._yield_sel_var,
                    command=self._set_yield_mat)
        except Exception:
            self.menu_yield = None
        # dropdown do vencimento do yield EUA (v8.1): radiobuttons com o
        # tipo (bill/note/bond) no nome; a escolha persiste no cache
        _uysel0 = self.last.get("us_yield_sel")
        if _uysel0 not in US_YIELD_MATS:
            _uysel0 = US_YIELD_DEFAULT
        self._us_yield_sel_var = tk.StringVar(value=_uysel0)
        try:
            self.menu_us_yield = tk.Menu(root, tearoff=0)
            for _mat in sorted(US_YIELD_MATS,
                               key=lambda k: US_YIELD_MATS[k]["ordem"]):
                self.menu_us_yield.add_radiobutton(
                    label=US_YIELD_MATS[_mat]["nome"], value=_mat,
                    variable=self._us_yield_sel_var,
                    command=self._set_us_yield_mat)
        except Exception:
            self.menu_us_yield = None
        try:
            gmenu = tk.Menu(self.menu, tearoff=0)
            for _lbl, _hk in (
                    ("Ouro spot USD", "spot_usd"),
                    ("Ouro spot BRL", "spot_brl"),
                    ("Cobre (COMEX HG=F)", "copper"),
                    ("Cobre SHFE (China)", "cu_shfe"),
                    ("Gasolina EUA", "fuel_gas"),
                    ("Diesel EUA", "fuel_diesel"),
                    ("CDS Brasil 5 anos", "cds_5y"),
                    ("Diesel NYMEX", "ho_f"),
                    ("Brent (benchmark)", "brent"),
                    ("Crude SC (Xangai)", "sc_f"),
                    ("Murban (Emirados)", "murban"),
                    ("Urals (Rússia)", "urals"),
                    ("Uréia (spot intl.)", "urea_me"),
                    ("Uréia CFR Brasil", "urea_br"),
                    ("Enxofre (spot CN)", "sulfur")):
                gmenu.add_command(label=_lbl,
                                  command=lambda k=_hk: self.open_history(k))
            gmenu.add_command(
                label="Yield nominal Brasil (venc. atual)",
                command=lambda: self.open_history(
                    "br_yield:" + (self._yield_sel_var.get()
                                   if self._yield_sel_var.get() in YIELD_MATS
                                   else YIELD_DEFAULT)))
            gmenu.add_command(
                label="Yield Treasury EUA (venc. atual)",
                command=lambda: self.open_history(
                    "us_yield:" + (self._us_yield_sel_var.get()
                                   if self._us_yield_sel_var.get() in US_YIELD_MATS
                                   else US_YIELD_DEFAULT)))
            self.menu.add_cascade(label="Ver grafico", menu=gmenu)
        except Exception:
            pass
        self.menu.add_checkbutton(label="Manter no topo",
                                  variable=self.var_top,
                                  command=self._toggle_top)
        self.menu.add_command(label="Encostar no canto", command=self.snap_corner)
        self.menu.add_command(label="Minimizar p/ bandeja", command=self.hide_to_tray)
        self.menu.add_separator()
        self.menu.add_command(label="Sair", command=self.quit)

        # ----------------------- arrastar com o mouse ------------------------
        self._drag_off = (0, 0)
        self._user_moved = False
        for w, hk in ((root, None), (self.frame, None), (self.body, None),
                         (self.canvas, None), (self.l_title, None),
                         (self.l_usd, "spot_usd"),
                         (self.l_usd_var, "spot_usd"),
                         (self.l_usd_var_week, "spot_usd"),
                         (self.l_brl, "spot_brl"),
                         (self.l_brl_var, "spot_brl"),
                         (self.l_brl_var_week, "spot_brl"),
                          (self.l_sub, None),
                          (self.l_fx_title, None),
                          (self.l_usdbrl, None),
                          (self.l_copper_sub, None),
                         (self.l_us_sub, None), (self.l_cds_sub, None),
                          (self.l_yield_sub, None),
                          (self.l_us_yield_sub, None),
                         (self.l_ho_sub, None), (self.l_brent_sub, None),
                         (self.l_sc_sub, None),
                         (self.l_murban_sub, None),
                         (self.l_urals_sub, None), (self.l_urea_sub, None),
                         (self.l_sulfur_sub, None)):
            self._bind(w, hk)

        # ------------- v7.1: rolagem oculta (wheel, sem scrollbar) ----------
        # O bind no root vale para todo descendente (bindtags incluem o
        # toplevel): cobre também os labels criados dinamicamente nos
        # renders. Popups de grafico têm outro toplevel -> não interferem.
        root.bind("<Button-4>", self._on_wheel)
        root.bind("<Button-5>", self._on_wheel)
        root.bind("<MouseWheel>", self._on_wheel)

        # ---------- v7.1: resize por arraste (área INVISÍVEL, bordas) -------
        # Faixas transparentes (bg igual ao fundo) nas 4 BORDAS e 4 CANTOS.
        # O cursor muda ao passar por cima, mas nada aparece na UI. O
        # tamanho escolhido é salvo no cache e restaurado no boot. O resize
        # é direcional: arrastar a borda esquerda/superior move a janela e
        # ancora o lado oposto (v7.1.1).
        self._resizing = False
        self._resize = None            # (x0, y0, w0, h0, wx0, wy0, modo)
        self._win_size = None          # tamanho fixado pelo usuário (ou salvo)
        G = EDGE_PX + 8                # área dos cantos
        edge_r = tk.Frame(self.frame, name="edge_r", bg=BG,
                          cursor="sb_h_double_arrow")
        edge_r.place(relx=1.0, rely=0.0, anchor="ne",
                     relheight=1.0, width=EDGE_PX)
        edge_l = tk.Frame(self.frame, name="edge_l", bg=BG,
                          cursor="sb_h_double_arrow")
        edge_l.place(relx=0.0, rely=0.0, anchor="nw",
                     relheight=1.0, width=EDGE_PX)
        edge_b = tk.Frame(self.frame, name="edge_b", bg=BG,
                          cursor="sb_v_double_arrow")
        edge_b.place(relx=0.0, rely=1.0, anchor="sw",
                     relwidth=1.0, height=EDGE_PX)
        edge_t = tk.Frame(self.frame, name="edge_t", bg=BG,
                          cursor="sb_v_double_arrow")
        edge_t.place(relx=0.0, rely=0.0, anchor="nw",
                     relwidth=1.0, height=EDGE_PX)
        grip_se = tk.Frame(self.frame, name="grip_se", bg=BG,
                           cursor="bottom_right_corner")
        grip_se.place(relx=1.0, rely=1.0, anchor="se", width=G, height=G)
        grip_sw = tk.Frame(self.frame, name="grip_sw", bg=BG,
                           cursor="bottom_left_corner")
        grip_sw.place(relx=0.0, rely=1.0, anchor="sw", width=G, height=G)
        grip_ne = tk.Frame(self.frame, name="grip_ne", bg=BG,
                           cursor="top_right_corner")
        grip_ne.place(relx=1.0, rely=0.0, anchor="ne", width=G, height=G)
        grip_nw = tk.Frame(self.frame, name="grip_nw", bg=BG,
                           cursor="top_left_corner")
        grip_nw.place(relx=0.0, rely=0.0, anchor="nw", width=G, height=G)
        # cantos criados por último: ficam por cima das faixas de borda
        for rz, mode in ((edge_r, "e"), (edge_l, "w"),
                         (edge_b, "s"), (edge_t, "n"),
                         (grip_se, "se"), (grip_sw, "sw"),
                         (grip_ne, "ne"), (grip_nw, "nw")):
            rz.bind("<Button-1>",
                    lambda e, m=mode: self._resize_start(e, m))
            rz.bind("<B1-Motion>", self._resize_motion)
            rz.bind("<ButtonRelease-1>", self._resize_end)

        # tamanho salvo em ciclo anterior (cache: last["win"])
        try:
            win = self.last.get("win") or {}
            sw = int(win.get("w", 0))
            sh = int(win.get("h", 0))
        except Exception:
            sw = sh = 0
        if sw >= MIN_W and sh >= MIN_H:
            sw = min(sw, root.winfo_screenwidth())
            sh = min(sh, root.winfo_screenheight())
            self._win_size = (sw, sh)
            root.geometry(f"{sw}x{sh}")

        # posição inicial: canto superior direito
        self.snap_corner()

        # mostra último preço conhecido enquanto não chega dado novo
        self._render()

        # ---------------- v8.3: bandeja (sempre inicia minimizado) -------
        # O usuário pediu boot SEMPRE oculto; --show inicia visível (fuga).
        # Se a bandeja falhar, NUNCA some: segue visível como antes.
        self._visible = True
        self._tray = None
        self._tray_ok = False
        self._tray_refresh_job = None
        start_hidden = "--show" not in sys.argv
        try:
            self._tray = TrayController(self)
            self._tray_ok = bool(self._tray.start())
        except Exception as e:
            log(f"bandeja: exceção ao iniciar ({e}); seguindo sem tray")
            self._tray = None
            self._tray_ok = False
        if self._tray_ok and start_hidden:
            try:
                self.hide_to_tray(silent=True)
            except Exception as e:
                log(f"bandeja: falha ao ocultar no boot ({e})")
        if self._tray_ok:
            try:
                self._tray.refresh()
            except Exception:
                pass
            try:
                self._tray_refresh_job = self.root.after(
                    5000, self._tray_refresh_tick)
            except Exception:
                pass
        else:
            log("bandeja inativa; widget segue visível (fallback seguro)")
        if start_hidden and self._tray_ok:
            log("boot minimizado na bandeja (v8.3)")
        elif "--show" in sys.argv:
            log("boot visível (--show)")

        # v8.3.2 (a pedido do usuário): o X da janela NÃO encerra — minimiza
        # p/ a bandeja (igual "Minimizar p/ bandeja"). Sem bandeja ativa,
        # encerra de verdade (exit 0; com Restart=on-failure o systemd NÃO
        # relança — só relança em crash). O Sair (bandeja e janela) segue
        # chamando quit() e encerrando de verdade.
        try:
            root.protocol("WM_DELETE_WINDOW", self._on_close_window)
        except Exception as e:
            log(f"aviso: WM_DELETE_WINDOW não registrado ({e})")

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

    @staticmethod
    def _urea_hist_key(name):
        return "urea_br" if "CFR" in name else "urea_me"

    def _hist_meta(self, key):
        if key.startswith("bank:"):
            return {"title": f"{key.split(':', 1)[1]} (R$/g) · ref. SGE",
                    "fmt": lambda v: f"R$ {fmt_brl(v)}/g",
                    "yfmt": lambda v: fmt_brl(v).split(",")[0],
                    "ranges": (7, 30, 90, 180, 365)}
        if key.startswith("br_yield:"):
            mat = key.split(":", 1)[1]
            meta = YIELD_MATS.get(mat) or {}
            lbl = meta.get("nome") or mat
            return {"title": f"Brasil · Yield nominal {lbl} (% a.a.)",
                    "fmt": lambda v: f"{fmt_yield(v)}%",
                    "yfmt": lambda v: f"{v:.2f}".replace(".", ","),
                    "ranges": (7, 30, 90, 180, 365)}
        if key.startswith("us_yield:"):
            mat = key.split(":", 1)[1]
            meta = US_YIELD_MATS.get(mat) or {}
            lbl = meta.get("nome") or mat
            return {"title": f"EUA · Yield nominal {lbl} (% a.a.)",
                    "fmt": lambda v: f"{fmt_yield(v)}%",
                    "yfmt": lambda v: f"{v:.2f}".replace(".", ","),
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
        # v7.1: se há tamanho fixado (salvo/resized), encosta por ele;
        # senão usa o tamanho natural do conteúdo (comportamento antigo).
        if self._win_size:
            w, h = self._win_size
        else:
            w = self.root.winfo_reqwidth()
            h = self.root.winfo_reqheight()
        x = self.root.winfo_screenwidth() - w - MARGIN
        y = MARGIN_Y
        self.root.geometry(f"+{x}+{y}")

    # ---------------- v7.1: rolagem oculta + resize por arraste -------------
    def _on_canvas_cfg(self, e):
        """Canvas mudou de tamanho: o body interno acompanha a largura
        (conteúdo reflowa; o texto NÃO escala) e a scrollregion é
        recalculada."""
        try:
            self.canvas.itemconfigure(self._body_win, width=e.width)
        except Exception:
            pass
        self._update_scroll()

    def _on_body_cfg(self, e):
        self._update_scroll()

    def _update_scroll(self):
        try:
            cw = max(1, self.canvas.winfo_width())
            ch = max(1, self.canvas.winfo_height())
            bw = max(1, self.body.winfo_reqwidth())
            bh = max(1, self.body.winfo_reqheight())
            self.canvas.configure(scrollregion=(0, 0, bw, bh))
            if bh <= ch + 2:
                self.canvas.yview_moveto(0.0)
            if bw <= cw + 2:
                self.canvas.xview_moveto(0.0)
        except Exception:
            pass

    def _on_wheel(self, e):
        """Rolagem SEM barra: wheel rola o conteúdo; só age se houver
        overflow. Shift+wheel rola na horizontal. Eventos de popups de
        grafico não chegam aqui (outro toplevel nos bindtags)."""
        try:
            if e.widget.winfo_toplevel() is not self.root:
                return
            cv = self.canvas
            bh = max(1, self.body.winfo_reqheight())
            bw = max(1, self.body.winfo_reqwidth())
            up = (getattr(e, "num", None) == 4
                  or getattr(e, "delta", 0) > 0)
            horiz = bool(getattr(e, "state", 0) & 0x00000001)
            if horiz:
                if bw <= cv.winfo_width() + 2:
                    return
                cv.xview_scroll(-1 if up else 1, "units")
            else:
                if bh <= cv.winfo_height() + 2:
                    return
                cv.yview_scroll(-1 if up else 1, "units")
        except Exception:
            pass

    def _resize_start(self, e, mode="se"):
        self._resizing = True
        self._cancel_click()
        try:
            self.root.update_idletasks()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            if w <= 2 or h <= 2:
                w = self.root.winfo_reqwidth()
                h = self.root.winfo_reqheight()
            self._resize = (e.x_root, e.y_root, w, h,
                            self.root.winfo_x(), self.root.winfo_y(),
                            mode)
        except Exception:
            self._resize = None

    def _resize_motion(self, e):
        if not (self._resizing and self._resize):
            return
        try:
            x0, y0, w0, h0, wx0, wy0, mode = self._resize
            dx = e.x_root - x0
            dy = e.y_root - y0
            w, h, nx, ny = w0, h0, wx0, wy0
            # resize direcional: letras do modo indicam que bordas se movem
            if "e" in mode:
                w = w0 + dx
            if "w" in mode:
                w = w0 - dx
            if "s" in mode:
                h = h0 + dy
            if "n" in mode:
                h = h0 - dy
            w = max(MIN_W, min(w, self.root.winfo_screenwidth()))
            h = max(MIN_H, min(h, self.root.winfo_screenheight()))
            # bordas oeste/norte ancoram o lado oposto (a janela cresce
            # para o lado arrastado, posicao acompanha o clamp)
            if "w" in mode:
                nx = wx0 + (w0 - w)
            if "n" in mode:
                ny = wy0 + (h0 - h)
            self._win_size = (w, h)
            self.root.geometry(f"{w}x{h}+{nx}+{ny}")
            self._user_moved = True
        except Exception:
            pass

    def _resize_end(self, e):
        if not self._resizing:
            return
        self._resizing = False
        self._resize = None
        # persiste: o poller também salva o cache, mas garante agora
        try:
            self.last["win"] = {"w": self._win_size[0],
                                "h": self._win_size[1]}
            save_cache(self.last)
        except Exception:
            pass

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
        if self._resizing:                      # v7.1: resize em andamento
            return
        self._cancel_click()
        self._drag_off = (e.x_root - self.root.winfo_x(),
                          e.y_root - self.root.winfo_y())
        self._press_xy = (e.x_root, e.y_root)
        self._press_t = time.time()
        self._dragged = False

    def _on_drag(self, e):
        if self._resizing:                      # v7.1: resize em andamento
            return
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
            if self._resizing:                  # v7.1: resize em andamento
                return
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

        # ---- Cobre · COMEX HG=F (v7.2): intraday, refetch no máx.
        #      1/5min; cadeia Yahoo -> FXEmpire -> TradingEconomics ->
        #      cache; falha isolada das demais seções ----
        cu = self.last.get("copper")
        if _due("copper", cu, HG_REFETCH):
            try:
                self.last["copper"] = fetch_copper()
                _cooldown_clear("copper")
            except Exception as e:
                log(f"cobre COMEX indisponível ({e}); mantendo cache")
                _cooldown("copper", HG_REFETCH, str(e))
        cu = self.last.get("copper")
        if cu and time.time() - cu.get("ts", 0) > HG_MAX_AGE:
            self.last.pop("copper", None)
            log("cobre COMEX: cache >4 dias sem fonte; removido")

        # ---- Cobre · SHFE CU0 (China, v7.3): intraday (sessão noturna
        #      21h-1h BJT), refetch no máx. 1/5min; cadeia Sina ->
        #      futsseapi -> push2delay -> cache; US$/lb = CNY/t ÷ USDCNY
        #      ÷ 2204.62 (só câmbio fresco; sem câmbio: CNY/t cru);
        #      falha isolada das demais seções ----
        cuc = self.last.get("cu_shfe")
        if _due("cu_shfe", cuc, CU_REFETCH):
            try:
                self.last["cu_shfe"] = fetch_cu_shfe(fx)
                _cooldown_clear("cu_shfe")
            except Exception as e:
                log(f"cobre SHFE indisponível ({e}); mantendo cache")
                _cooldown("cu_shfe", CU_REFETCH, str(e))
        cuc = self.last.get("cu_shfe")
        if cuc and time.time() - cuc.get("ts", 0) > CU_MAX_AGE:
            self.last.pop("cu_shfe", None)
            log("cobre SHFE: cache >4 dias sem fonte; removido")

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

        # ---- Brasil · Yield nominal (v8.0): refetch no máx. 1/15min;
        #      cadeia Investing-tabela (www/m.) -> TE 10y -> instrumento ->
        #      API historical -> cache; MESCLA por vencimento (rec fresco
        #      substitui o mesmo vencimento, os outros ficam de cache);
        #      falha isolada das demais seções ----
        _ysel = self.last.get("yield_sel")
        if _ysel not in YIELD_MATS:
            _ysel = YIELD_DEFAULT
        yb = self.last.get("br_yield")
        if _due("yield", yb, YIELD_REFETCH):
            try:
                got = fetch_yield_br(_ysel)
                merged = dict((yb or {}).get("curve") or {})
                merged.update({m: r for m, r in got.items() if r.get("yield")})
                self.last["br_yield"] = {"curve": merged}
                _cooldown_clear("yield")
            except Exception as e:
                log(f"yield Brasil indisponível ({e}); mantendo cache")
                _cooldown("yield", YIELD_REFETCH, str(e))
        yb = self.last.get("br_yield")
        if yb:
            keep = {m: r for m, r in (yb.get("curve") or {}).items()
                    if time.time() - r.get("ts", 0) <= YIELD_MAX_AGE}
            if keep:
                yb["curve"] = keep
            else:
                self.last.pop("br_yield", None)
                log("yield Brasil: cache >4 dias sem fonte; removido")

        # ---- EUA · Yield Treasury (v8.1): refetch no máx. 1/15min;
        #      cadeia Investing-tabela (www/m.) -> TE -> instrumento ->
        #      API historical -> FRED (completa a curva) -> cache;
        #      MESCLA por vencimento (rec fresco substitui o mesmo
        #      vencimento, os outros ficam de cache); falha isolada ----
        _uysel = self.last.get("us_yield_sel")
        if _uysel not in US_YIELD_MATS:
            _uysel = US_YIELD_DEFAULT
        uy = self.last.get("us_yield")
        if _due("us_yield", uy, US_YIELD_REFETCH):
            try:
                got = fetch_us_yield(_uysel)
                merged = dict((uy or {}).get("curve") or {})
                merged.update({m: r for m, r in got.items() if r.get("yield")})
                self.last["us_yield"] = {"curve": merged}
                _cooldown_clear("us_yield")
            except Exception as e:
                log(f"yield EUA indisponível ({e}); mantendo cache")
                _cooldown("us_yield", US_YIELD_REFETCH, str(e))
        uy = self.last.get("us_yield")
        if uy:
            keep = {m: r for m, r in (uy.get("curve") or {}).items()
                    if time.time() - r.get("ts", 0) <= US_YIELD_MAX_AGE}
            if keep:
                uy["curve"] = keep
            else:
                self.last.pop("us_yield", None)
                log("yield EUA: cache >4 dias sem fonte; removido")

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

        # ---- China · Crude SC (v6.8): intraday (sessão noturna), refetch
        #      no máx. 1/5min; cadeia Sina -> futsseapi -> push2delay ->
        #      cache; conversão US$/bbl só com câmbio fresco; falha isolada
        sc = self.last.get("sc_fut")
        if _due("sc", sc, SC_REFETCH):
            try:
                self.last["sc_fut"] = fetch_sc(fx)
                _cooldown_clear("sc")
            except Exception as e:
                log(f"crude SC indisponível ({e}); mantendo cache")
                _cooldown("sc", SC_REFETCH, str(e))
        sc = self.last.get("sc_fut")
        if sc and time.time() - sc.get("ts", 0) > SC_MAX_AGE:
            self.last.pop("sc_fut", None)
            log("crude SC: cache >4 dias sem fonte; removido")

        # ---- Emirados · Crude Murban (v6.9): avaliação ADNOC com delay,
        #      refetch no máx. 1/h; cadeia tabela -> freewidgets -> cache;
        #      falha isolada das demais seções ----
        mu = self.last.get("murban")
        if _due("murban", mu, MURBAN_REFETCH):
            try:
                self.last["murban"] = fetch_murban()
                _cooldown_clear("murban")
            except Exception as e:
                log(f"crude Murban indisponível ({e}); mantendo cache")
                _cooldown("murban", MURBAN_REFETCH, str(e))
        mu = self.last.get("murban")
        if mu and time.time() - mu.get("ts", 0) > MURBAN_MAX_AGE:
            self.last.pop("murban", None)
            log("crude Murban: cache >7 dias sem fonte; removido")
        ur = self.last.get("urals")
        if ur and time.time() - ur.get("ts", 0) > URALS_MAX_AGE:
            self.last.pop("urals", None)
            log("crude Urals: cache >7 dias sem fonte; removido")

        # ---- Fertilizante · Uréia (v6.6): 2 linhas independentes (spot +
        #      CFR Brasil), refetch no máx. 1/h, falha isolada uma da outra
        #      (TE -> TV -> Pink -> cache / Yahoo-UFB -> TV -> cache) ----
        um = self.last.get("urea_me")
        if _due("urea_me", um, UREA_REFETCH):
            try:
                self.last["urea_me"] = fetch_urea_me()
                _cooldown_clear("urea_me")
            except Exception as e:
                log(f"uréia (spot) indisponível ({e}); mantendo cache")
                _cooldown("urea_me", UREA_REFETCH, str(e))
        um = self.last.get("urea_me")
        if um and time.time() - um.get("ts", 0) > UREA_MAX_AGE:
            self.last.pop("urea_me", None)
            log("uréia (spot): cache >14 dias sem fonte; removido")
        ub = self.last.get("urea_br")
        if _due("urea_br", ub, UREA_REFETCH):
            try:
                self.last["urea_br"] = fetch_urea_br()
                _cooldown_clear("urea_br")
            except Exception as e:
                log(f"uréia CFR Brasil indisponível ({e}); mantendo cache")
                _cooldown("urea_br", UREA_REFETCH, str(e))
        ub = self.last.get("urea_br")
        if ub and time.time() - ub.get("ts", 0) > UREA_MAX_AGE:
            self.last.pop("urea_br", None)
            log("uréia CFR Brasil: cache >14 dias sem fonte; removido")

        # ---- Enxofre · spot CN (v6.7): diário, refetch no máx. 1/h;
        #      cadeia TE -> SunSirs -> cache; conversão US$/t só com
        #      câmbio fresco (sem câmbio: mostra CNY/t cru) ----
        sf = self.last.get("sulfur")
        if _due("sulfur", sf, SULFUR_REFETCH):
            try:
                self.last["sulfur"] = fetch_sulfur(fx)
                _cooldown_clear("sulfur")
            except Exception as e:
                log(f"enxofre indisponível ({e}); mantendo cache")
                _cooldown("sulfur", SULFUR_REFETCH, str(e))
        sf = self.last.get("sulfur")
        if sf and time.time() - sf.get("ts", 0) > SULFUR_MAX_AGE:
            self.last.pop("sulfur", None)
            log("enxofre: cache >14 dias sem fonte; removido")

        # ---- Câmbio · USD/BRL (v8.2): refetch 90s; cadeia 10 degraus
        #      (intraday -> BCB); falha da cadeia mantém cache ≤24h ----
        ub = self.last.get("usdbrl")
        if _due("usdbrl", ub, USDBRL_REFETCH):
            try:
                self.last["usdbrl"] = fetch_usdbrl()
                _cooldown_clear("usdbrl")
            except Exception as e:
                log(f"USD/BRL indisponível ({e}); mantendo cache")
                _cooldown("usdbrl", USDBRL_REFETCH, str(e))
        ub = self.last.get("usdbrl")
        if ub and (ub.get("rate") is None
                   or time.time() - ub.get("ts", 0) > USDBRL_MAX_AGE):
            self.last.pop("usdbrl", None)
            log("USD/BRL: cache >24h sem fonte; removido")

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
            _cu = _L.get("copper") or {}
            if _cu.get("price"):
                log_hist_point(_H, "copper", _cu["price"])
            _cuc = _L.get("cu_shfe") or {}
            if _cuc.get("price") and _cuc.get("usdcny_used"):
                log_hist_point(_H, "cu_shfe", _cuc["price"])
            _cds = _L.get("cds_br") or {}
            if _cds.get("bps"):
                log_hist_point(_H, "cds_5y", _cds["bps"])
            for _ym, _yr in ((_L.get("br_yield") or {}).get("curve") or {}).items():
                if _yr.get("yield"):
                    log_hist_point(_H, f"br_yield:{_ym}", _yr["yield"])
            for _ym, _yr in ((_L.get("us_yield") or {}).get("curve") or {}).items():
                if _yr.get("yield"):
                    log_hist_point(_H, f"us_yield:{_ym}", _yr["yield"])
            _ho = _L.get("ho_fut") or {}
            if _ho.get("price"):
                log_hist_point(_H, "ho_f", _ho["price"])
            _ur = _L.get("urals") or {}
            if _ur.get("price"):
                log_hist_point(_H, "urals", _ur["price"])
            _br = _L.get("brent") or {}
            if _br.get("price"):
                log_hist_point(_H, "brent", _br["price"])
            _sc = _L.get("sc_fut") or {}
            if _sc.get("price") and _sc.get("usdcny_used"):
                log_hist_point(_H, "sc_f", _sc["price"])
            _mu = _L.get("murban") or {}
            if _mu.get("price"):
                log_hist_point(_H, "murban", _mu["price"])
            _um = _L.get("urea_me") or {}
            if _um.get("price"):
                log_hist_point(_H, "urea_me", _um["price"])
            _ub = _L.get("urea_br") or {}
            if _ub.get("price"):
                log_hist_point(_H, "urea_br", _ub["price"])
            _sf = _L.get("sulfur") or {}
            if _sf.get("price") and _sf.get("usdcny_used"):
                log_hist_point(_H, "sulfur", _sf["price"])
            save_hist_log(_H)
        except Exception as e:
            log(f"falha no log de historico: {e}")
        save_cache(self.last)
        self.root.after(0, self._set_spot_offline,
                        not (usd_ok or brl_ok))
        self.root.after(0, self._render)
        try:
            self.root.after(0, self._tray_refresh_soon)
        except Exception:
            pass
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

    def _tray_refresh_soon(self):
        """Refresh da bandeja após novo ciclo (label/título). Nunca levanta."""
        try:
            if getattr(self, "_tray_ok", False) and self._tray is not None:
                self._tray.refresh()
        except Exception:
            pass

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

        # seção CÂMBIO · USD/BRL (v8.2)
        self._render_usdbrl()

        # seção COBRE · COMEX HG=F (v7.2)
        self._render_copper()
        self._render_copper_sub()

        # seção EUA · combustível (v5.4 local)
        self._render_us()
        self._render_us_sub()

        # seção BRASIL · CDS 5 anos (v5.7)
        self._render_cds()
        self._render_cds_sub()

        # seção BRASIL · yield nominal (v8.0)
        self._render_yield()
        self._render_yield_sub()

        # seção EUA · yield Treasury (v8.1)
        self._render_us_yield()
        self._render_us_yield_sub()

        # seção NYMEX · diesel HO=F (v6.1)
        self._render_ho()
        self._render_ho_sub()

        # seção BRENT · crude benchmark (v6.3)
        self._render_brent()
        self._render_brent_sub()

        # seção CHINA · crude SC Xangai (v6.8)
        self._render_sc()
        self._render_sc_sub()

        # seção EMIRADOS · crude Murban (v6.9)
        self._render_murban()
        self._render_murban_sub()

        # seção RÚSSIA · crude Urals (v6.2)
        self._render_urals()
        self._render_urals_sub()

        # seção FERTILIZANTE · ureia (v6.6)
        self._render_urea()
        self._render_urea_sub()

        # seção ENXOFRE · spot CN (v6.7)
        self._render_sulfur()
        self._render_sulfur_sub()

        # re-encosta no canto com a largura real (a menos que o user arrastou)
        if not self._user_moved:
            self.snap_corner()

        # v8.4: a bandeja acompanha o widget — todo _render (que roda na
        # thread do Tk após cada poll via _poll_once_impl) também empurra
        # o label/título BRL para a barra de notificações.
        try:
            self._tray_refresh_soon()
        except Exception:
            pass

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

    def _render_usdbrl(self):
        """Campo visível USD/BRL (v8.2): só o valor, mid 4 dec pt-BR.
        Cache ≤24h se a cadeia caiu; senão "—"."""
        d = self.last.get("usdbrl") or {}
        rate = d.get("rate")
        if rate is None or time.time() - d.get("ts", 0) > USDBRL_MAX_AGE:
            self.l_usdbrl.config(text="—")
            return
        self.l_usdbrl.config(text=f"US$ 1 = R$ {fmt_fx4(rate)}")

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

    # ----------------- exibição · seção COBRE (v7.2/v7.3) ------------------
    # 2 linhas na MESMA seção: COMEX HG=F (US$/lb) e SHFE CU0 (US$/lb,
    # China) — unidades idênticas p/ comparar o prêmio SHFE de graça.
    def _copper_label(self, rec=None):
        """Rótulo da linha COMEX: 'HG=F · COMEX · dez/26' (+ ' · (cache)'
        após FUT_STALE). Mês vem do futuresMonth da FXEmpire ('Dec 2026')
        ou do shortName do Yahoo (ex.: 'Copper Dec 26'); sem mês, fica só
        'HG=F · COMEX'."""
        rec = rec or {}
        nome = "HG=F · COMEX"
        month = rec.get("month") or ""
        if not month:
            parts = (rec.get("name") or "").split()
            if len(parts) >= 2 and parts[-2] in MONTH_PT:
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

    def _cu_label(self, rec=None):
        """Rótulo da linha SHFE: 'CU0 · SHFE' (+ ' · (cache)' após
        FUT_STALE) — mesmo padrão do rótulo do SC (v6.8)."""
        rec = rec or {}
        nome = "CU0 · SHFE"
        if rec.get("ts") and time.time() - rec["ts"] > FUT_STALE:
            nome += " · (cache)"
        return nome

    def _copper_rows(self):
        hg = self.last.get("copper") or {}
        cu = self.last.get("cu_shfe") or {}
        rows = []
        if hg.get("price") or cu.get("price"):
            rows.append((("h", "── COBRE ──"), None, None))
        if hg.get("price"):
            rows.append((("r", self._copper_label(hg)),
                         f"US$ {fmt_usd(hg['price'])}/lb",
                         hg.get("pct"), "copper"))
        if cu.get("price"):
            if cu.get("cny"):
                pre_str = f"CNY {cu['price']:,.0f}/t"
            else:
                pre_str = f"US$ {fmt_usd(cu['price'])}/lb"
            rows.append((("r", self._cu_label(cu)),
                         pre_str,
                         cu.get("pct"), "cu_shfe"))
        return rows

    def _render_copper(self):
        rows = self._copper_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._copper_sig:
            for w in self.copper_frame.winfo_children():
                w.destroy()
            self._copper_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.copper_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._copper_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.copper_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.copper_frame, text="—", bg=BG,
                                  fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.copper_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, r[3])
                    self._copper_refs.append(("r", ln, lp, lv))
                grid += 1
            self.copper_frame.columnconfigure(0, weight=1)
            self._copper_sig = sig

        for ref, r in zip(self._copper_refs, rows):
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

    def _render_copper_sub(self):
        hg = self.last.get("copper") or {}
        cu = self.last.get("cu_shfe") or {}
        hparts, cparts = [], []
        if hg.get("price"):
            if hg.get("high") is not None and hg.get("low") is not None:
                hparts.append(f"HG dia {hg['low']:.2f}-{hg['high']:.2f}")
            if hg.get("oi"):
                hparts.append(f"OI {hg['oi']:,.0f}")
            if hg.get("vendor_ts"):
                hparts.append(str(hg["vendor_ts"]).replace("T", " ")[:16] + "Z")
        if hg.get("ts"):
            hparts.append(f"{hg.get('src', '?')} há "
                          f"{max(0, int(time.time() - hg['ts']))}s")
            if time.time() - hg["ts"] > HG_REFETCH * 2:
                hparts.append("(cache)")
        if cu.get("price"):
            if cu.get("cny"):
                cparts.append("sem câmbio fresco: CU0 cru em CNY")
            elif cu.get("cny_price"):
                cparts.append(f"CU0 CNY {cu['cny_price']:,.0f}/t")
            if cu.get("usdcny_used"):
                cparts.append(f"USDCNY {cu['usdcny_used']:.4f}")
            cparts.append(f"{cu.get('src', '?')} há "
                          f"{max(0, int(time.time() - cu.get('ts', 0)))}s")
            if time.time() - cu.get("ts", 0) > CU_REFETCH * 2:
                cparts.append("(cache)")
        groups = [" · ".join(g) for g in (hparts, cparts) if g]
        self.l_copper_sub.config(text="   |   ".join(groups), fg=TXT_DIM)

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

    # ------------- exibição · seção BRASIL · YIELD NOMINAL (v8.0) ----------
    def _yield_rows(self):
        """1ª linha = vencimento do dropdown; vencimento sem dado local
        ainda mostra a linha com '—' (o dropdown continua acessível)."""
        d = self.last.get("br_yield") or {}
        curve = d.get("curve") or {}
        sel = self._yield_sel_var.get()
        if sel not in YIELD_MATS:
            sel = YIELD_DEFAULT
        rows = []
        if curve:
            rows.append((("h", "── BRASIL · YIELD GOVERNO (NOMINAL) ──"),
                         None, None))
            rec = curve.get(sel) or {}
            nome = f"Yield nominal (LTN/NTN) · {sel}"
            if rec.get("ts") and time.time() - rec["ts"] > YIELD_REFETCH * 2:
                nome += " · (cache)"
            rows.append((("r", nome),
                         (f"{fmt_yield(rec['yield'])}%" if rec.get("yield")
                          else "—"),
                         rec.get("chg_pp")))
        return rows

    def _render_yield(self):
        rows = self._yield_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._yield_sig:
            for w in self.yield_frame.winfo_children():
                w.destroy()
            self._yield_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.yield_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._yield_refs.append(("h", lab))
                else:
                    sel = (self._yield_sel_var.get()
                           if self._yield_sel_var.get() in YIELD_MATS
                           else YIELD_DEFAULT)
                    ln = tk.Label(self.yield_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.yield_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.yield_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    dd = tk.Button(self.yield_frame, text="▾", bg=BG,
                                   fg=TXT_BRL, font=("DejaVu Sans", 8, "bold"),
                                   bd=0, highlightthickness=0,
                                   activebackground=BG, activeforeground=TXT_BRL,
                                   cursor="hand2", padx=2, pady=0,
                                   command=self._open_yield_menu)
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    dd.grid(row=grid, column=3, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, f"br_yield:{sel}")
                    self._yield_refs.append(("r", ln, lp, lv, dd))
                grid += 1
            self.yield_frame.columnconfigure(0, weight=1)
            self._yield_sig = sig

        for ref, r in zip(self._yield_refs, rows):
            if ref[0] == "h":
                continue
            _, lp, lv = ref[1], ref[2], ref[3]
            price_str, chg = r[1], r[2]
            lp.config(text=price_str, fg=TXT_USD)
            if chg is None:
                lv.config(text="")
            else:
                lv.config(text=f"{fmt_pct(chg)[:1]} {fmt_pp(chg)}",
                          fg=UP_COLOR if chg >= 0 else DOWN_COLOR)

    def _open_yield_menu(self):
        if not self.menu_yield:
            return
        try:
            self.menu_yield.tk_popup(self.root.winfo_pointerx(),
                                     self.root.winfo_pointery())
        finally:
            try:
                self.menu_yield.grab_release()
            except Exception:
                pass

    def _set_yield_mat(self):
        mat = self._yield_sel_var.get()
        if mat not in YIELD_MATS:
            return
        self.last["yield_sel"] = mat
        save_cache(self.last)
        self._render()

    def _render_yield_sub(self):
        d = self.last.get("br_yield") or {}
        curve = d.get("curve") or {}
        parts = []
        if curve:
            sel = self._yield_sel_var.get()
            if sel not in YIELD_MATS:
                sel = YIELD_DEFAULT
            rec = curve.get(sel) or {}
            if rec.get("ts"):
                parts.append(f"{rec.get('src', '?')} há "
                             f"{max(0, int(time.time() - rec['ts']))}s")
            else:
                newest = max((r.get("ts", 0) for r in curve.values()), default=0)
                if newest:
                    src = next((r.get("src", "?") for r in curve.values()
                                if r.get("ts") == newest), "?")
                    parts.append(f"{src} há {max(0, int(time.time() - newest))}s")
            items = []
            for mat in sorted(YIELD_MATS, key=lambda k: YIELD_MATS[k]["ordem"]):
                r = curve.get(mat)
                if r and r.get("yield"):
                    items.append(f"{mat} {r['yield']:.2f}%".replace(".", ","))
            if items:
                parts.append("curva " + " · ".join(items))
        self.l_yield_sub.config(text="  ·  ".join(parts), fg=TXT_DIM)

    # ------------- exibição · seção EUA · YIELD TREASURY (v8.1) -----------
    def _us_yield_rows(self):
        """1ª linha = vencimento do dropdown (nome c/ bill/note/bond);
        vencimento sem dado local ainda mostra a linha com '—' (o dropdown
        continua acessível)."""
        d = self.last.get("us_yield") or {}
        curve = d.get("curve") or {}
        sel = self._us_yield_sel_var.get()
        if sel not in US_YIELD_MATS:
            sel = US_YIELD_DEFAULT
        rows = []
        if curve:
            rows.append((("h", "── EUA · YIELD GOVERNO (TREASURY) ──"),
                         None, None))
            rec = curve.get(sel) or {}
            nome = (f"Yield nominal (UST) · "
                    f"{US_YIELD_MATS[sel]['nome']}")
            if rec.get("ts") and time.time() - rec["ts"] > US_YIELD_REFETCH * 2:
                nome += " · (cache)"
            rows.append((("r", nome),
                         (f"{fmt_yield(rec['yield'])}%" if rec.get("yield")
                          else "—"),
                         rec.get("chg_pp")))
        return rows

    def _render_us_yield(self):
        rows = self._us_yield_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._us_yield_sig:
            for w in self.us_yield_frame.winfo_children():
                w.destroy()
            self._us_yield_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.us_yield_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._us_yield_refs.append(("h", lab))
                else:
                    sel = (self._us_yield_sel_var.get()
                           if self._us_yield_sel_var.get() in US_YIELD_MATS
                           else US_YIELD_DEFAULT)
                    ln = tk.Label(self.us_yield_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.us_yield_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.us_yield_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    dd = tk.Button(self.us_yield_frame, text="▾", bg=BG,
                                   fg=TXT_BRL, font=("DejaVu Sans", 8, "bold"),
                                   bd=0, highlightthickness=0,
                                   activebackground=BG, activeforeground=TXT_BRL,
                                   cursor="hand2", padx=2, pady=0,
                                   command=self._open_us_yield_menu)
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    dd.grid(row=grid, column=3, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, f"us_yield:{sel}")
                    self._us_yield_refs.append(("r", ln, lp, lv, dd))
                grid += 1
            self.us_yield_frame.columnconfigure(0, weight=1)
            self._us_yield_sig = sig

        for ref, r in zip(self._us_yield_refs, rows):
            if ref[0] == "h":
                continue
            _, lp, lv = ref[1], ref[2], ref[3]
            price_str, chg = r[1], r[2]
            lp.config(text=price_str, fg=TXT_USD)
            if chg is None:
                lv.config(text="")
            else:
                lv.config(text=f"{fmt_pct(chg)[:1]} {fmt_pp(chg)}",
                          fg=UP_COLOR if chg >= 0 else DOWN_COLOR)

    def _open_us_yield_menu(self):
        if not self.menu_us_yield:
            return
        try:
            self.menu_us_yield.tk_popup(self.root.winfo_pointerx(),
                                        self.root.winfo_pointery())
        finally:
            try:
                self.menu_us_yield.grab_release()
            except Exception:
                pass

    def _set_us_yield_mat(self):
        mat = self._us_yield_sel_var.get()
        if mat not in US_YIELD_MATS:
            return
        self.last["us_yield_sel"] = mat
        save_cache(self.last)
        self._render()

    def _render_us_yield_sub(self):
        d = self.last.get("us_yield") or {}
        curve = d.get("curve") or {}
        parts = []
        if curve:
            sel = self._us_yield_sel_var.get()
            if sel not in US_YIELD_MATS:
                sel = US_YIELD_DEFAULT
            rec = curve.get(sel) or {}
            if rec.get("ts"):
                parts.append(f"{rec.get('src', '?')} há "
                             f"{max(0, int(time.time() - rec['ts']))}s")
            else:
                newest = max((r.get("ts", 0) for r in curve.values()), default=0)
                if newest:
                    src = next((r.get("src", "?") for r in curve.values()
                                if r.get("ts") == newest), "?")
                    parts.append(f"{src} há {max(0, int(time.time() - newest))}s")
            items = []
            for mat in sorted(US_YIELD_MATS, key=lambda k: US_YIELD_MATS[k]["ordem"]):
                r = curve.get(mat)
                if r and r.get("yield"):
                    items.append(f"{mat} {r['yield']:.2f}%".replace(".", ","))
            if items:
                parts.append("curva " + " · ".join(items))
        self.l_us_yield_sub.config(text="  ·  ".join(parts), fg=TXT_DIM)

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

    # ------------- exibição · seção CHINA · CRUDE SC (v6.8) ----------------
    def _sc_label(self, rec=None):
        """Rótulo da linha: 'SC · contínuo' (+ ' · (cache)' após FUT_STALE)."""
        rec = rec or {}
        nome = "SC · contínuo (INE)"
        if rec.get("ts") and time.time() - rec["ts"] > FUT_STALE:
            nome += " · (cache)"
        return nome

    def _sc_rows(self):
        d = self.last.get("sc_fut") or {}
        rows = []
        if d.get("price"):
            rows.append((("h", "── CHINA · CRUDE SC (XANGAI) ──"), None, None))
            unit = "CNY" if d.get("cny") else "US$"
            rows.append((("r", self._sc_label(d)),
                         f"{unit} {fmt_usd(d['price'])}/bbl",
                         d.get("pct")))
        return rows

    def _render_sc(self):
        rows = self._sc_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._sc_sig:
            for w in self.sc_frame.winfo_children():
                w.destroy()
            self._sc_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.sc_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._sc_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.sc_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.sc_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.sc_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, "sc_f")
                    self._sc_refs.append(("r", ln, lp, lv))
                grid += 1
            self.sc_frame.columnconfigure(0, weight=1)
            self._sc_sig = sig

        for ref, r in zip(self._sc_refs, rows):
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

    def _render_sc_sub(self):
        d = self.last.get("sc_fut") or {}
        parts = []
        if d.get("price"):
            if d.get("cny"):
                parts.append("sem câmbio fresco: valor cru em CNY")
            if d.get("cny_price"):
                parts.append(f"original CNY {d['cny_price']:,.2f}/bbl")
            if d.get("usdcny_used"):
                parts.append(f"USDCNY {d['usdcny_used']:.4f}")
            p = [f"spot {d.get('src', '?')}"]
            if d.get("ts"):
                p.append(f"há {max(0, int(time.time() - d['ts']))}s")
            parts.append(" · ".join(p))
        self.l_sc_sub.config(text="  ·  ".join(parts), fg=TXT_DIM)

    # --------------- exibição · seção EMIRADOS · MURBAN (v6.9) -------------
    def _murban_rows(self):
        d = self.last.get("murban") or {}
        rows = []
        if d.get("price"):
            rows.append((("h", "── EMIRADOS · CRUDE MURBAN ──"), None, None))
            nome = "Murban (FOB)"
            if d.get("ts") and time.time() - d["ts"] > MURBAN_REFETCH * 2:
                nome += " · (cache)"
            rows.append((("r", nome),
                         f"US$ {fmt_usd(d['price'])}/bbl",
                         d.get("pct")))
        return rows

    def _render_murban(self):
        rows = self._murban_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._murban_sig:
            for w in self.murban_frame.winfo_children():
                w.destroy()
            self._murban_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.murban_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._murban_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.murban_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.murban_frame, text="—", bg=BG,
                                  fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.murban_frame, text="", bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, "murban")
                    self._murban_refs.append(("r", ln, lp, lv))
                grid += 1
            self.murban_frame.columnconfigure(0, weight=1)
            self._murban_sig = sig

        for ref, r in zip(self._murban_refs, rows):
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

    def _render_murban_sub(self):
        d = self.last.get("murban") or {}
        parts = []
        if d.get("price"):
            if d.get("delay"):
                parts.append(f"avaliação spot · delay {d['delay']}")
            if d.get("day"):
                parts.append(f"dado {d['day']}")
        ts = d.get("ts")
        if ts:
            parts.append(f"{d.get('src', '?')} há {max(0, int(time.time() - ts))}s")
            if time.time() - ts > MURBAN_REFETCH * 2:
                parts.append("(cache)")
        self.l_murban_sub.config(text=" · ".join(parts), fg=TXT_DIM)

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

    # -------------- exibição · seção FERTILIZANTE · UREIA (v6.6) -----------
    def _urea_br_label(self, rec=None):
        """Rótulo da linha CFR: 'UFB=F' (+ mês se o shortName do Yahoo
        traz mês tipo 'Nov 26'; o TV scanner não traz mês) + '(cache)'
        quando o dado passa de 2 refetches."""
        rec = rec or {}
        nome = "Uréia CFR Brasil (UFB=F)"
        parts = (rec.get("name") or "").split()
        if len(parts) >= 2 and parts[-2] in MONTH_PT:
            nome += f" · {MONTH_PT[parts[-2]]}/{parts[-1]}"
        if rec.get("ts") and time.time() - rec["ts"] > UREA_REFETCH * 2:
            nome += " · (cache)"
        return nome

    def _urea_rows(self):
        me = self.last.get("urea_me") or {}
        br = self.last.get("urea_br") or {}
        rows = []
        if me.get("price") or br.get("price"):
            rows.append((("h", "── FERTILIZANTE · UREIA ──"), None, None))
            if me.get("price"):
                nome = "Uréia (spot intl.)"
                if me.get("mensal"):
                    nome = "Uréia (mensal · f.o.b. Oriente Médio)"
                if (me.get("ts")
                        and time.time() - me["ts"] > UREA_REFETCH * 2):
                    nome += " · (cache)"
                rows.append((("r", nome),
                             f"US$ {fmt_usd(me['price'])}/t", me.get("pct")))
            if br.get("price"):
                rows.append((("r", self._urea_br_label(br)),
                             f"US$ {fmt_usd(br['price'])}/t", br.get("pct")))
        return rows

    def _render_urea(self):
        rows = self._urea_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._urea_sig:
            for w in self.urea_frame.winfo_children():
                w.destroy()
            self._urea_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.urea_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._urea_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.urea_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.urea_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.urea_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, self._urea_hist_key(r[0][1]))
                    self._urea_refs.append(("r", ln, lp, lv))
                grid += 1
            self.urea_frame.columnconfigure(0, weight=1)
            self._urea_sig = sig

        for ref, r in zip(self._urea_refs, rows):
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

    def _render_urea_sub(self):
        parts = []
        me = self.last.get("urea_me") or {}
        if me.get("price"):
            p = [f"spot {me.get('src', '?')}"]
            if me.get("day"):
                p.append(str(me["day"]))
            if me.get("ts"):
                p.append(f"há {max(0, int(time.time() - me['ts']))}s")
            parts.append(" · ".join(p))
        br = self.last.get("urea_br") or {}
        if br.get("price"):
            p = [f"CFR {br.get('src', '?')}"]
            if br.get("ts"):
                p.append(f"há {max(0, int(time.time() - br['ts']))}s")
            parts.append(" · ".join(p))
        self.l_urea_sub.config(text="  ·  ".join(parts), fg=TXT_DIM)

    # ---------------- exibição · seção ENXOFRE · SPOT CN (v6.7) -----------
    def _sulfur_rows(self):
        d = self.last.get("sulfur") or {}
        rows = []
        if d.get("price"):
            rows.append((("h", "── ENXOFRE · SPOT CN ──"), None, None))
            nome = "Enxofre (spot CN)"
            if d.get("ts") and time.time() - d["ts"] > SULFUR_REFETCH * 2:
                nome += " · (cache)"
            if d.get("cny"):
                rows.append((("r", nome),
                             f"CNY {fmt_usd(d['price'])}/t", d.get("pct")))
            else:
                rows.append((("r", nome),
                             f"US$ {fmt_usd(d['price'])}/t", d.get("pct")))
        return rows

    def _render_sulfur(self):
        rows = self._sulfur_rows()
        sig = tuple(r[0] for r in rows)
        if sig != self._sulfur_sig:
            for w in self.sulfur_frame.winfo_children():
                w.destroy()
            self._sulfur_refs = []
            grid = 0
            for r in rows:
                kind = r[0][0]
                if kind == "h":
                    lab = tk.Label(self.sulfur_frame, text=r[0][1], bg=BG,
                                   fg=TITLE, font=("DejaVu Sans", 7, "bold"),
                                   anchor="w")
                    lab.grid(row=grid, column=0, columnspan=3, sticky="w",
                             pady=(7 if grid else 0, 1))
                    self._bind(lab)
                    self._sulfur_refs.append(("h", lab))
                else:
                    ln = tk.Label(self.sulfur_frame, text=r[0][1], bg=BG,
                                  fg=TXT_DIM, font=("DejaVu Sans", 8),
                                  anchor="w")
                    lp = tk.Label(self.sulfur_frame, text="—", bg=BG, fg=TXT_USD,
                                  font=("DejaVu Sans", 8, "bold"), anchor="e")
                    lv = tk.Label(self.sulfur_frame, text="", bg=BG, fg=TXT_DIM,
                                  font=("DejaVu Sans", 8), anchor="e")
                    ln.grid(row=grid, column=0, sticky="w")
                    lp.grid(row=grid, column=1, sticky="e", padx=(16, 6))
                    lv.grid(row=grid, column=2, sticky="e")
                    for w in (ln, lp, lv):
                        self._bind(w, "sulfur")
                    self._sulfur_refs.append(("r", ln, lp, lv))
                grid += 1
            self.sulfur_frame.columnconfigure(0, weight=1)
            self._sulfur_sig = sig

        for ref, r in zip(self._sulfur_refs, rows):
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

    def _render_sulfur_sub(self):
        d = self.last.get("sulfur") or {}
        parts = []
        if d.get("price"):
            if d.get("cny"):
                parts.append("sem câmbio fresco: valor cru em CNY")
            p = [f"spot {d.get('src', '?')}"]
            if d.get("day"):
                p.append(str(d["day"]))
            if d.get("ts"):
                p.append(f"há {max(0, int(time.time() - d['ts']))}s")
            if d.get("usdcny_used"):
                p.append(f"USDCNY {d['usdcny_used']:.4f}")
            parts.append(" · ".join(p))
        self.l_sulfur_sub.config(text="  ·  ".join(parts), fg=TXT_DIM)

    def _tick(self):
        if self.stop.is_set():
            return
        self._render_sub()
        self._render_us_sub()
        self._render_cds_sub()      # reavalia idade/cache do CDS
        self._render_yield_sub()    # reavalia idade/cache do yield
        self._render_us_yield_sub()  # reavalia idade/cache do yield EUA
        self._render_ho_sub()       # reavalia idade/cache do HO=F
        self._render_brent_sub()    # reavalia idade/cache do Brent
        self._render_sc_sub()       # reavalia idade/cache do crude SC
        self._render_murban_sub()   # reavalia idade/cache do Murban
        self._render_urals_sub()    # reavalia idade/cache do Urals
        self._render_urea_sub()     # reavalia idade/cache da ureia
        self._render_sulfur_sub()   # reavalia idade/cache do enxofre
        self._pump_tray_loop()      # v8.3.1: mantém o registro SNI vivo
        self.root.after(5000, self._tick)

    def _pump_tray_loop(self):
        """Bombeia o mainloop GLib/Gtk sem bloquear o Tk.

        O AppIndicator precisa do despacho GLib para manter o registro
        StatusNotifierItem vivo (sem isso o ícone some ~5s após o boot,
        mesmo com set_status(ACTIVE)). main_context_iteration(False) só
        despacha o que já está pendente — nunca bloqueia. Qualquer falha
        aqui é ignorada: o widget jamais pode quebrar por causa do tray.
        """
        try:
            tray = getattr(self, "_tray", None)
            GLib = getattr(tray, "GLib", None) if tray is not None else None
            if GLib is None or not getattr(tray, "ok", False):
                return
            try:
                ctx = GLib.main_context_default()
            except Exception:
                return
            try:
                for _ in range(20):
                    if not ctx.iteration(False):
                        break
            except Exception:
                pass
        except Exception:
            pass

    # ----------------------------- saída --------------------------------
    def quit(self):
        self.stop.set()
        try:
            if self._tray_refresh_job is not None:
                try:
                    self.root.after_cancel(self._tray_refresh_job)
                except Exception:
                    pass
                self._tray_refresh_job = None
        except Exception:
            pass
        try:
            if self._tray is not None:
                self._tray.stop()
        except Exception:
            pass
        self.root.destroy()

    def _on_close_window(self):
        """Handler do X da janela (v8.3.2): minimiza p/ bandeja se ativa,
        senão encerra de verdade (quit -> exit 0 -> sem relançamento)."""
        try:
            if getattr(self, "_tray_ok", False):
                self.hide_to_tray()
                return
        except Exception as e:
            log(f"bandeja: falha ao minimizar via X ({e})")
        self.quit()

    # ---------------- v8.3: bandeja (mostrar / ocultar) -------------------
    def is_visible(self):
        """Visível = flag interna E janela mapeada. Nunca levanta."""
        try:
            if not getattr(self, "_visible", True):
                return False
            try:
                return bool(self.root.winfo_viewable())
            except Exception:
                return bool(getattr(self, "_visible", True))
        except Exception:
            return True

    def show_from_tray(self):
        """Reexibe a janela (chamado via menu da bandeja)."""
        try:
            self.root.deiconify()
        except Exception:
            pass
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        # recoloca na camada desktop/BOTTOM configurada no boot
        try:
            if getattr(self, "_desktop_layer", False):
                try:
                    self.root.attributes(
                        "-type", "normal" if self.var_top.get() else "desktop")
                except Exception:
                    pass
                try:
                    self._below_applied = False
                    self._apply_below_layer()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.root.lift()
        except Exception:
            pass
        self._visible = True
        try:
            if self._tray_ok and self._tray is not None:
                self._tray.refresh()
        except Exception:
            pass
        log("widget visível (via bandeja)")

    def hide_to_tray(self, silent=False):
        """Oculta a janela; o processo segue rodando (polling/cache/log).

        Sem bandeja ativa vira no-op seguro (nunca some sem tray).
        """
        if not getattr(self, "_tray_ok", False):
            if not silent:
                log("minimizar p/ bandeja ignorado: bandeja inativa")
            return
        try:
            self.root.withdraw()
        except Exception as e:
            log(f"bandeja: falha ao ocultar ({e})")
            return
        self._visible = False
        try:
            if self._tray is not None:
                self._tray.refresh()
        except Exception:
            pass
        if not silent:
            log("widget minimizado p/ bandeja")

    def toggle_visible(self):
        """Alterna visível <-> bandeja (item Mostrar/Ocultar)."""
        try:
            if self.is_visible():
                self.hide_to_tray()
            else:
                self.show_from_tray()
        except Exception as e:
            log(f"bandeja: falha no toggle ({e})")

    def tray_graph_entries(self):
        """Entradas do submenu 'Ver gráfico' da bandeja (mesmas da janela)."""
        entries = [
            ("Ouro spot USD", "spot_usd"),
            ("Ouro spot BRL", "spot_brl"),
            ("Cobre (COMEX HG=F)", "copper"),
            ("Cobre SHFE (China)", "cu_shfe"),
            ("Gasolina EUA", "fuel_gas"),
            ("Diesel EUA", "fuel_diesel"),
            ("CDS Brasil 5 anos", "cds_5y"),
            ("Diesel NYMEX", "ho_f"),
            ("Brent (benchmark)", "brent"),
            ("Crude SC (Xangai)", "sc_f"),
            ("Murban (Emirados)", "murban"),
            ("Urals (Rússia)", "urals"),
            ("Uréia (spot intl.)", "urea_me"),
            ("Uréia CFR Brasil", "urea_br"),
            ("Enxofre (spot CN)", "sulfur"),
        ]
        try:
            ysel = (self._yield_sel_var.get()
                    if getattr(self, "_yield_sel_var", None) is not None
                    and self._yield_sel_var.get() in YIELD_MATS
                    else YIELD_DEFAULT)
        except Exception:
            ysel = YIELD_DEFAULT
        try:
            uysel = (self._us_yield_sel_var.get()
                     if getattr(self, "_us_yield_sel_var", None) is not None
                     and self._us_yield_sel_var.get() in US_YIELD_MATS
                     else US_YIELD_DEFAULT)
        except Exception:
            uysel = US_YIELD_DEFAULT
        entries.append(("Yield nominal Brasil (venc. atual)", "br_yield:" + ysel))
        entries.append(("Yield Treasury EUA (venc. atual)", "us_yield:" + uysel))
        return entries

    def _tray_refresh_tick(self):
        """Reagenda o refresh da bandeja (label/título + Mostrar/Ocultar)."""
        self._tray_refresh_job = None
        if self.stop.is_set():
            return
        try:
            if self._tray_ok and self._tray is not None:
                self._tray.refresh()
        except Exception:
            pass
        try:
            self._tray_refresh_job = self.root.after(
                5000, self._tray_refresh_tick)
        except Exception:
            pass

# ------------------------------- DUMP ------------------------------------
def dump():
    """Modo sem interface: busca tudo e imprime já normalizado
    (grama -> BRL; onça troy -> USD)."""
    last = {}
    fx = None
    try:
        u = fetch_usdbrl()
        print(f"USD/BRL [{u['src']}]: {u['rate']:.4f} (mid)")
    except Exception as e:
        print(f"USD/BRL (10 fontes): FALHOU ({e})")
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
        cu = fetch_copper()
        last["copper"] = cu
        extra = []
        if cu.get("pct") is not None:
            extra.append(f"{cu['pct']:+.2f}%")
        if cu.get("day_chg") is not None:
            extra.append(f"Δ {cu['day_chg']:+.4f}")
        if cu.get("high") is not None and cu.get("low") is not None:
            extra.append(f"dia {cu['low']:.2f}-{cu['high']:.2f}")
        if cu.get("oi"):
            extra.append(f"OI {cu['oi']:,.0f}")
        if cu.get("month"):
            extra.append(f"contrato {cu['month']}")
        print(f"COBRE COMEX [{cu['src']}]: {cu['price']:,.2f} US$/lb "
              f"({', '.join(extra) if extra else '—'})")
    except Exception as e:
        print(f"COBRE COMEX: FALHOU ({e})")

    try:
        cuc = fetch_cu_shfe(last.get("fx"))
        last["cu_shfe"] = cuc
        extra = []
        if cuc.get("pct") is not None:
            extra.append(f"{cuc['pct']:+.2f}%")
        if cuc.get("cny_price"):
            extra.append(f"cru CNY {cuc['cny_price']:,.0f}/t")
        if cuc.get("usdcny_used"):
            extra.append(f"USDCNY {cuc['usdcny_used']:.4f}")
        unit = "CNY/t (cru)" if cuc.get("cny") else "US$/lb"
        print(f"COBRE SHFE CU0 [{cuc['src']}]: {cuc['price']:,.2f} {unit} "
              f"({', '.join(extra) if extra else '—'})")
    except Exception as e:
        print(f"COBRE SHFE CU0: FALHOU ({e})")

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
        y = fetch_yield_br(YIELD_DEFAULT)
        last["br_yield"] = {"curve": y, "sel": YIELD_DEFAULT}
        itens = []
        for mat in sorted(YIELD_MATS, key=lambda k: YIELD_MATS[k]["ordem"]):
            r = y.get(mat)
            if r and r.get("yield"):
                itens.append(f"{mat} {fmt_yield(r['yield'])}%"
                             f"({r['chg_pp']:+.2f}pp)" if r.get("chg_pp") is not None
                             else f"{mat} {fmt_yield(r['yield'])}%")
        srcs = sorted({r.get("src", "?") for r in y.values()})
        print(f"YIELD BR NOMINAL [{'/'.join(srcs)}]: {' · '.join(itens)}")
    except Exception as e:
        print(f"YIELD BR NOMINAL: FALHOU ({e})")

    try:
        y = fetch_us_yield(US_YIELD_DEFAULT)
        last["us_yield"] = {"curve": y, "sel": US_YIELD_DEFAULT}
        itens = []
        for mat in sorted(US_YIELD_MATS, key=lambda k: US_YIELD_MATS[k]["ordem"]):
            r = y.get(mat)
            if r and r.get("yield"):
                itens.append(f"{mat} {fmt_yield(r['yield'])}%"
                             f"({r['chg_pp']:+.2f}pp)" if r.get("chg_pp") is not None
                             else f"{mat} {fmt_yield(r['yield'])}%")
        srcs = sorted({r.get("src", "?") for r in y.values()})
        print(f"US YIELD TREASURY [{'/'.join(srcs)}]: {' · '.join(itens)}")
    except Exception as e:
        print(f"US YIELD TREASURY: FALHOU ({e})")

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
        s = fetch_sc(last.get("fx"))
        last["sc_fut"] = s
        extra = []
        if s.get("pct") is not None:
            extra.append(f"{s['pct']:+.2f}%")
        if s.get("cny_price"):
            extra.append(f"cru CNY {s['cny_price']:,.2f}")
        if s.get("usdcny_used"):
            extra.append(f"USDCNY {s['usdcny_used']:.4f}")
        unit = "CNY/bbl (cru)" if s.get("cny") else "US$/bbl"
        print(f"CRUDE SC XANGAI [{s['src']}]: {s['price']:,.2f} {unit} "
              f"({', '.join(extra) if extra else '—'})")
    except Exception as e:
        print(f"CRUDE SC XANGAI: FALHOU ({e})")

    try:
        mu = fetch_murban()
        last["murban"] = mu
        extra = []
        if mu.get("pct") is not None:
            extra.append(f"{mu['pct']:+.2f}%")
        if mu.get("day_chg") is not None:
            extra.append(f"Δ {mu['day_chg']:+.2f}")
        if mu.get("delay"):
            extra.append(f"delay {mu['delay']}")
        print(f"CRUDE MURBAN [{mu['src']}]: {mu['price']:,.2f} US$/bbl "
              f"({', '.join(extra) if extra else '—'} · dado {mu.get('day', '?')})")
    except Exception as e:
        print(f"CRUDE MURBAN: FALHOU ({e})")

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

    try:
        um = fetch_urea_me()
        last["urea_me"] = um
        extra = []
        if um.get("pct") is not None:
            extra.append(f"{um['pct']:+.2f}%")
        if um.get("day"):
            extra.append(f"dado {um['day']}")
        if um.get("mensal"):
            extra.append("série mensal")
        print(f"UREIA SPOT [{um['src']}]: {um['price']:,.2f} US$/t "
              f"({', '.join(extra) if extra else '—'})")
    except Exception as e:
        print(f"UREIA SPOT: FALHOU ({e})")

    try:
        ub = fetch_urea_br()
        last["urea_br"] = ub
        extra = []
        if ub.get("pct") is not None:
            extra.append(f"{ub['pct']:+.2f}%")
        if ub.get("month") or ub.get("name"):
            extra.append(f"contrato {ub.get('month') or ub.get('name')}")
        print(f"UREIA CFR BRASIL [{ub['src']}]: {ub['price']:,.2f} US$/t "
              f"({', '.join(extra) if extra else '—'})")
    except Exception as e:
        print(f"UREIA CFR BRASIL: FALHOU ({e})")

    try:
        sf = fetch_sulfur(last.get("fx"))
        last["sulfur"] = sf
        extra = []
        if sf.get("pct") is not None:
            extra.append(f"{sf['pct']:+.2f}%")
        if sf.get("day"):
            extra.append(f"dado {sf['day']}")
        if sf.get("cny_price"):
            extra.append(f"cru CNY {sf['cny_price']:,.2f}")
        if sf.get("usdcny_used"):
            extra.append(f"USDCNY {sf['usdcny_used']:.4f}")
        unit = "CNY/t (cru)" if sf.get("cny") else "US$/t"
        print(f"ENXOFRE SPOT CN [{sf['src']}]: {sf['price']:,.2f} {unit} "
              f"({', '.join(extra) if extra else '—'})")
    except Exception as e:
        print(f"ENXOFRE SPOT CN: FALHOU ({e})")

    print("\nCHINA/COMEX: removidos a pedido do usuário")
    return 0

# ------------------------------- MAIN ------------------------------------
def main():
    if "--dump" in sys.argv:
        # --dump NUNCA trava: consulta pontual de terminal (teste/cron),
        # roda livre mesmo com o widget aberto.
        log("modo --dump (sem interface)")
        return dump()

    # Instância única: 2ª GUI sai em silêncio (exit 0 — limpo p/ o caso de
    # autostart duplo global+usuário; só o log registra).
    if not acquire_instance_lock():
        log("segunda instância detectada; saindo sem abrir janela")
        return 0

    if tk is None:
        log("tkinter indisponível")
        print("Erro: tkinter não disponível neste sistema.", file=sys.stderr)
        return 1

    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("Sem display gráfico (DISPLAY não definido).", file=sys.stderr)
        return 1

    log("iniciando widget (v8.3: SEMPRE inicia minimizado na bandeja"
        " AyatanaAppIndicator3 — menu Mostrar/Ocultar + Atualizar agora + Ver"
        " gráfico + Sair, label com spot BRL (R$/g, v8.4), ícone dourado gerado com"
        " Pillow; --show inicia visível; sem bandeja segue visível sem"
        " quebrar; v8.2: + seção CÂMBIO · USD/BRL — linha só com o"
        " valor mid e cadeia de 10 degraus awesomeapi -> Yahoo -> TE ->"
        " floatrates -> currency-api -> er-api -> frankfurter -> BCB SGS ->"
        " Olinda PTAX -> BCB SOAP, cache 24h; v8.1: + seção EUA · YIELD"
        " GOVERNO TREASURY (UST bills/notes/bonds, dropdown por vencimento"
        " — cadeia Investing tabela www/m. -> TE -> instrumento -> API"
        " historical -> FRED DGS* -> cache 4d; v8.0: BRASIL · YIELD GOVERNO"
        " NOMINAL (LTN/NTN) com DROPDOWN por vencimento — cadeia Investing"
        " tabela www/m. -> TE 10y -> instrumento -> API historical -> cache"
        " 4d, Δ em pp; mantém v7.1: janela redimensionável + rolagem oculta"
        " + tamanho persistente)")
    root = tk.Tk()
    GoldWidget(root)
    root.mainloop()
    log("widget encerrado")
    return 0

if __name__ == "__main__":
    sys.exit(main())
