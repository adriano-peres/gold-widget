# Ouro Widget

![Python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![Plataforma](https://img.shields.io/badge/plataforma-Linux%20%C2%B7%20X11-FCC624?logo=linux&logoColor=black)
![Dependências](https://img.shields.io/badge/depend%C3%AAncias-somente%20stdlib-00A86B)
![Versão](https://img.shields.io/badge/vers%C3%A3o-v7.3-c9a227)
![Licença](https://img.shields.io/badge/licen%C3%A7a-uso%20pessoal-lightgrey)

Widget de desktop em **Python puro** (tkinter) que vive na sua área de trabalho e mostra, em tempo quase real e **sem nenhuma chave de API**:

- **Ouro spot** em USD/onça e R$/grama;
- **Cobre** — COMEX `HG=F` (benchmark global) e SHFE `CU0` (China), ambos em US$/lb para comparar o prêmio chinês de graça;
- **Combustível EUA** — média nacional **diária** de varejo da bomba (gasolina regular e diesel, AAA);
- **Risco soberano do Brasil** — CDS 5 anos em bps + probabilidade de default implícita;
- **Petróleo e derivados** — NYMEX diesel `HO=F`, Brent `BZ=F`, Crude SC de Xangai, Murban (Emirados) e Urals (Rússia);
- **Fertilizante e commodity química** — uréia (spot internacional + CFR Brasil) e enxofre spot da China.

> Sem chaves de API, sem pip, sem dependências externas.
> Só a stdlib: `tkinter` + `urllib` (+ `ctypes` para o truque de camada no X11).
> Toda seção tem **cadeia de fallback própria** (2 a 6 fontes + cache) e **falha isolada**: uma API fora do ar não derruba as outras.

---

## Sumário

- [O que ele faz](#o-que-ele-faz)
- [Recursos](#recursos)
- [Seções e fontes de dados](#seções-e-fontes-de-dados)
- [Regras de normalização de preço](#regras-de-normalização-de-preço)
- [Instalação](#instalação)
- [Uso](#uso)
- [Interações com o widget](#interações-com-o-widget)
- [Modo `--dump` (sem interface)](#modo---dump-sem-interface)
- [Arquivos e cache](#arquivos-e-cache)
- [Configurações ajustáveis](#configurações-ajustáveis)
- [Como funciona a camada da área de trabalho](#como-funciona-a-camada-da-área-de-trabalho)
- [Changelog resumido](#changelog-resumido)
- [Licença](#licença)

---

## O que ele faz

Um cartão discreto no canto superior direito da tela que exibe (exemplo real, `--dump` de 23/09/2026):

```
OURO · SPOT
US$ 4,285.65   ▲ 0.42% no dia   ▲ 1.87% na semana
R$ 885,32/g    ▼ 0.11% no dia   ▲ 1.52% na semana
bid 4,285.1 · ask 4,286.2 · há 34s

── COBRE ──
HG=F · COMEX · dez/26     US$ 6.76/lb        ▼ 1.08%
CU0 · SHFE                US$ 7.38/lb        ▼ 0.10%
HG dia 6.75-6.91 · OI 175,200 · FXEmpire/Oanda há 12s   |   CU0 CNY 110.140/t · USDCNY 6.7674 · Sina nf_CU0 há 34s

── EUA · COMBUSTÍVEL (VAREJO · DIÁRIO) ──
Gasolina (regular)       US$ 4.474/g        ▼ 0.02%
Diesel (nacional)        US$ 6.522/g        ▼ 0.09%

── BRASIL · RISCO SOBERANO (CDS) ──
CDS 5 anos               119.75 bps         ▼ 3.61% 1m
PD implícita (rec. 40%)  2,00%

── NYMEX · DIESEL (HO=F · ATACADO) ──
HO=F · out/26            US$ 4.873/g        ▼ 1.40%
                         (= US$ 204.66/bbl · OI 67,982)

── BRENT · CRUDE (BENCHMARK) ──
BZ=F                     US$ 102.13/bbl     ▲ 1.33%

── CHINA · CRUDE SC (XANGAI) ──
SC · contínuo (INE)      US$ 107.07/bbl     ▲ 0.69%

── EMIRADOS · CRUDE MURBAN ──
Murban (FOB)             US$ 111.46/bbl     ▲ 2.57%

── RÚSSIA · CRUDE URALS ──
Urals (FOB)              US$ 107.23/bbl     ▼ 0.25%

── FERTILIZANTE · UREIA ──
Uréia (spot intl.)       US$ 459.00/t       ▼ 0.22%
Uréia CFR Brasil (UFB=F) US$ 475.00/t

── ENXOFRE · SPOT CN ──
Enxofre (spot CN)        US$ 1,145.55/t     ± 0.00%
```

Cada seção tem um rodapé próprio com a fonte usada, frescor do dado ("há Ns"), dia da cotação, delay de avaliação, faixa do dia, open interest e avisos (`(cache)`, `sem câmbio fresco: valor cru em CNY`).

## Recursos

- Spot **USD** (`goldprice.dev` → `goldprice.org`) e **BRL** derivado com câmbio fresco
- Câmbio USD/BRL e CNY/BRL com 3 fontes (`awesomeapi` → `currency-api`/jsDelivr → `open.er-api.com`)
- Baseline diário/semanal via **PAXG**: Binance → OKX (fora da quota da API principal)
- **Cobre COMEX HG=F** (v7.2): intraday US$/lb — Yahoo → FXEmpire (CFD Oanda) → TradingEconomics → cache 4d
- **Cobre SHFE CU0** (v7.3): o cobre da China em US$/lb = CNY/t ÷ USDCNY ÷ 2204,62 — Sina → Eastmoney futsseapi → Eastmoney push2delay → cache 4d; sem câmbio fresco mostra CNY/t cru (nunca com taxa velha)
- **Combustível EUA diário** (v5.9): média nacional de varejo da **AAA Fuel Prices** (rede OPIS/WEX, atualiza todo dia), variação vs ontem; refetch 1/h
- **CDS Brasil 5 anos** (v5.7/v5.8): worldgovernmentbonds.com (REST interno, intraday) → Investing.com (SSR, EOD com checagem de `lastUpdateTime`) → cache 7d; PD implícita com 40% de recuperação
- **NYMEX HO=F, Brent BZ=F, Crude SC, Murban, Urals, uréia (2 linhas) e enxofre** — cada um com cadeia dedicada (ver tabela abaixo)
- **Backoff em duas camadas** (v6.3/v6.4): cooldown **por fonte** (429 = falha dupla + jitter) e cooldown **por seção** com dobra a cada falha consecutiva (teto 30 min) — cadeia morta não vira martelada
- Tabela do OilPrice.com com cache de 2 min: serve Brent, Urals e Murban sem request duplicado
- **Cache local atômico** (`.tmp` + `os.replace`): reinicia mostrando o último preço conhecido
- Indicador de frescor: "há Ns", fonte alternativa em uso e aviso "spot offline (cache)"
- Derivação conservadora: BRL, US$/bbl do SC e US$/lb do CU0 só saem de câmbio com **até 15 min** de idade
- **Gráficos no clique** (v6.0): popup com Canvas puro, períodos 7D–1A; fallback no log local acumulado; sem dependência nova
- Modo `--dump`: busca tudo pela linha de comando, sem interface gráfica
- Arrastável, com menu de contexto, encostar no canto e opção "manter no topo"
- **Redimensionável** (v7.1): arraste a borda/canto invisível; rolagem oculta (roda do mouse, sem barra) quando o conteúdo não couber; tamanho persistente entre reinícios

## Seções e fontes de dados

Toda fonte tem plano B (e C, D...). Se uma responde erro **ou responde sem dado**, a próxima entra automaticamente — cada uma com cooldown próprio.

| Seção | Cadeia de fallback | Refetch | Cache vence |
|---|---|---|---|
| **Ouro spot USD** | `goldprice.dev` → `goldprice.org` | 90 s | — |
| **Ouro spot BRL** | `goldprice.dev` → derivado USD × USDBRL → `goldprice.org/BRL` | 90 s | — |
| **Câmbio USD/BRL, CNY/BRL** | awesomeapi → currency-api (jsDelivr) → open.er-api.com | 90 s | — |
| **Baseline dia/semana (PAXG)** | Binance klines → OKX candles 1Dutc | 90 s | — |
| **Cobre COMEX HG=F** (US$/lb) | Yahoo `HG=F` (chart, q1→q2 em 429) → FXEmpire `/commodities/copper` (CFD Oanda) → TradingEconomics (scrape) → cache 4d | 5 min | 4 dias |
| **Cobre SHFE CU0** (US$/lb) | Sina `nf_CU0` (contrato principal real) → Eastmoney futsseapi `113_cum_qt` (主连 emendado) → Eastmoney push2delay `113.cum` → cache 4d | 5 min | 4 dias |
| **Combustível EUA (varejo · diário)** | AAA Fuel Prices `gasprices.aaa.com` (tabela nacional, vs ontem) → cache 14d | 1 h | 14 dias |
| **CDS Brasil 5 anos (bps)** | WGB (REST interno; payload embutido → payload reextraído da página) → Investing.com SSR `BRGV5YUSAC=R` (EOD, checa `lastUpdateTime`) → cache 7d | 15 min | 7 dias |
| **NYMEX diesel HO=F** (US$/gal e /bbl) | Yahoo `HO=F` (q1→q2) → FXEmpire `/commodities/ho` (CFD Oanda) → TradingEconomics (scrape) → cache 4d | 5 min | 4 dias |
| **Brent BZ=F** (US$/bbl) | Yahoo `BZ=F` (q1→q2) → FXEmpire `/commodities/brent-crude-oil` (CFD BCO/USD) → OilPrice.com tabela (~11 min de atraso) → OilPrice.com freewidgets (POST + CSRF) → cache 4d | 5 min | 4 dias |
| **Crude SC · Xangai INE** (US$/bbl) | Sina `nf_SC0` → Eastmoney futsseapi `142_scm_qt` → Eastmoney push2delay `142.scm` → cache 4d; US$/bbl só com USDCNY fresco | 5 min | 4 dias |
| **Crude Murban** (US$/bbl) | OilPrice.com tabela (blend 4464; avaliação com delay de minutos) → OilPrice.com freewidgets (CSRF + XHR) → cache 7d | 1 h | 7 dias |
| **Crude Urals** (US$/bbl) | TradingEconomics `urals-oil` (T+1, data real do resumo) → minfin.com.ua (T+1, tabela diária) → OilPrice.com tabela (T+2) → OilPrice.com freewidgets (T+2) → cache 7d | 1 h | 7 dias |
| **Uréia spot intl.** (US$/t) | TradingEconomics (espelha o FOB Golfo EUA, == CBOT UFV1!) → TradingView scanner → World Bank Pink Sheet (xlsx mensal, série f.o.b. Oriente Médio) → cache 14d | 1 h | 14 dias |
| **Uréia CFR Brasil** (US$/t) | Yahoo `UFB=F` (CBOT/CME "Urea Granular CFR Brazil", q1→q2) → TradingView `CBOT:UFB1!` → cache 14d | 1 h | 14 dias |
| **Enxofre spot CN** (CNY/t → US$/t) | TradingEconomics `/commodity/sulfur` → SunSirs (tabela diária; anti-bot `HW_CHECK` replicado em 2 GETs) → cache 14d; US$/t só com USDCNY fresco | 1 h | 14 dias |

Notas de robustez:

- **Cobre:** o FXEmpire espelha o contrato **mais líquido** (dez/26, OI ~175 mil — o front set/26 tem OI ~1,3 mil), que é o benchmark do HG; o CU0 usa a variação vs **settlement** anterior (convenção chinesa) e a mesma unidade US$/lb do COMEX para o prêmio SHFE ser comparável de graça.
- **Urals:** não existe em bolsa (Yahoo/FRED/Investing não têm série de spot — verificado); o dado vem de avaliações Argus/Platts com atraso. A v7.0 derrubou o delay de T+2 (OilPrice) para **T+1** com TradingEconomics e minfin.com.ua. Tempo real verdadeiro exige terminal pago (Bloomberg/Argus/Platts).
- **Enxofre:** não existe público em US$/t (Pink Sheet sem a série, sem futuro em bolsa); as duas fontes vivas publicam CNY/t do mesmo mercado.
- Se o baseline (PAXG) for de outro dia UTC, a variação "no dia" entra em pausa em vez de mentir.
- Fallback que salva **não anistia** a fonte primária morta (bug clássico de martelada, corrigido na v6.4).

## Regras de normalização de preço

A variação percentual do BRL compõe ouro × dólar:
`(1 + var_ouro) × (1 + var_câmbio) − 1`.

Formatação local: padrão US para USD (`4,615.47`) e padrão BR para BRL (`23.823,37`).

Conversões que exigem câmbio (R$/g do spot, US$/bbl do SC, US$/lb do CU0, US$/t do enxofre) só acontecem com USDCNY/USDBRL de até **15 min**; sem câmbio fresco, o valor é exibido cru na moeda original (CNY) e o rodapé avisa.

## Instalação

Requisitos: **Linux com sessão X11**, Python 3 com tkinter e libX11.

```bash
# Debian/Ubuntu
sudo apt install python3-tk libx11-6

# Fedora
sudo dnf install python3-tkinter libX11

# Arch
sudo pacman -S tk libx11
```

```bash
git clone https://github.com/adriano-peres/gold-widget.git
cd gold-widget
python3 gold_widget.py
```

> **Wayland:** o posicionamento/camada usa X11 (`ctypes` + `_NET_WM_STATE`). Em Wayland puro o widget até roda (se o tkinter existir), mas os recursos de camada ficam desativados.

### Iniciar junto com a sessão (opcional)

Crie `~/.config/autostart/ouro-widget.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Ouro Widget
Exec=python3 /caminho/para/gold-widget/gold_widget.py
X-GNOME-Autostart-enabled=true
```

## Uso

```bash
python3 gold_widget.py          # abre o widget na área de trabalho
python3 gold_widget.py --dump   # busca tudo e imprime no terminal (sem interface)
```

O polling roda em thread separada a cada **90 s** (abaixo do teto anônimo de ~100 req/h da goldprice.dev). As seções mais lentas (diárias/avaliação) têm cadência própria — nada é martelado à toa.

## Interações com o widget

| Ação | Resultado |
|---|---|
| **Arrastar** com o botão esquerdo | move o widget para onde quiser |
| **Arrastar** uma borda ou canto (área invisível de ~6–14 px, cursor muda ao passar) | redimensiona — as bordas esquerda/superior ancoram o lado oposto; mínimo 200×150 |
| **Roda do mouse** sobre o widget | rola o conteúdo quando não couber na janela (sem barra de rolagem; Shift+roda rola na horizontal) |
| **Duplo clique** | encosta no canto superior direito (mantém o tamanho escolhido) |
| **Clique simples** num valor | abre o popup com o gráfico do ativo (período 7D–1A ajustável) |
| **Botão direito** | abre o menu |
| Menu → *Atualizar agora* | força um refresh imediato (não empilha com o poller em curso) |
| Menu → *Ver gráfico* | abre o gráfico de qualquer um dos 15 ativos sem precisar clicar nele |
| Menu → *Manter no topo* | alterna entre ficar sob as janelas (padrão) e sempre visível |
| Menu → *Encostar no canto* | volta para a posição padrão |
| Menu → *Sair* | encerra |

Por padrão o widget vive numa camada especial: **acima dos ícones do desktop e abaixo de qualquer janela** — ele não atrapalha seu trabalho e não some atrás dos ícones.

## Modo `--dump` (sem interface)

Útil para testar fontes, agendar via cron ou usar em servidor:

```text
$ python3 gold_widget.py --dump
FX [awesomeapi]: USDBRL 5.1526 · CNYBRL 0.7614 · USDCNY 6.7674
goldprice.dev XAU-USD-SPOT: 4,285.65 (bid None · ask None)
goldprice.dev XAU-BRL-SPOT: 22,150.95 (bid None · ask None)
Sina/China/COMEX GC=F: REMOVIDOS a pedido do usuário (sem busca)
COBRE COMEX [FXEmpire/Oanda]: 6.76 US$/lb (-1.08%, Δ -0.0740, dia 6.75-6.91, OI 175,200, contrato Dec 2026)
COBRE SHFE CU0 [Sina nf_CU0]: 7.38 US$/lb (-0.10%, cru CNY 110,140/t, USDCNY 6.7674)
US FUEL [AAA Fuel Prices]: gasolina 4.474 US$/gal · diesel 6.522 US$/gal (dia 2026-09-23) (Δ dia: gasolina -0.001, diesel -0.006)
CDS BR 5Y [WGB]: 119.75 bps (1s +6.17%, 1m -3.61%, 1a -5.13%) · PD implícita 2,00% — 23 Sep 2026, 2:15
NYMEX DIESEL [FXEmpire/Oanda]: 4.8729 US$/gal (= US$ 204.66/bbl · -1.40%, OI 67,982, contrato Oct 2026)
BRENT [FXEmpire/Oanda]: 102.13 US$/bbl (+1.33%, Δ +1.34 · dado 2026-09-23 14:53)
CRUDE SC XANGAI [Sina nf_SC0]: 107.07 US$/bbl (+0.69%, cru CNY 724.60, USDCNY 6.7674)
CRUDE MURBAN [OilPrice.com]: 111.46 US$/bbl (+2.57%, Δ +2.79, delay 16m · dado 2026-09-23)
CRUDE URALS [TradingEconomics]: 107.23 US$/bbl (-0.25%, Δ -0.27 · dado None)
UREIA SPOT [TradingEconomics]: 459.00 US$/t (-0.22%)
UREIA CFR BRASIL [TradingView]: 475.00 US$/t (—)
ENXOFRE SPOT CN [TradingEconomics]: 1,145.55 US$/t (+0.00%, cru CNY 7,752.33, USDCNY 6.7674)
```

*(valores de uma execução real; mudam a cada chamada)*

## Arquivos e cache

| Caminho | Função |
|---|---|
| `~/.local/share/gold-widget/last_price.json` | cache do último estado conhecido (**escrita atômica**; inclui o tamanho da janela da v7.1) |
| `~/.local/share/gold-widget/widget.log` | log de eventos, falhas de fonte e fallbacks acionados |
| `~/.local/share/gold-widget/history.json` | histórico extraído dos logs, usado como fallback dos gráficos |

No boot o widget renderiza imediatamente o cache enquanto busca dados novos; se tudo estiver offline, mostra o rodapé `spot offline (cache)`.

## Configurações ajustáveis

Constantes no topo do `gold_widget.py`:

| Constante | Padrão | Descrição |
|---|---|---|
| `POLL_SECONDS` | `90` | intervalo entre buscas (respeite a quota da API) |
| `NET_TIMEOUT` | `8` | timeout de rede em segundos |
| `FX_MAX_AGE` | `15 min` | câmbio mais velho que isso não é usado p/ derivação |
| `FUT_STALE` | `10 min` | idade a partir da qual o rótulo ganha "(cache)" |
| `HG_REFETCH` / `HG_MAX_AGE` | `5 min` / `4 dias` | cadência e expiração do cobre COMEX HG=F |
| `CU_REFETCH` / `CU_MAX_AGE` | `5 min` / `4 dias` | cadência e expiração do cobre SHFE CU0 |
| `FUEL_REFETCH` / `FUEL_MAX_AGE` | `1 h` / `14 dias` | cadência e expiração do combustível AAA (diário) |
| `CDS_POLL_SECONDS` / `CDS_MAX_AGE` | `15 min` / `7 dias` | cadência e expiração do CDS Brasil |
| `HO_REFETCH` / `HO_MAX_AGE` | `5 min` / `4 dias` | cadência e expiração do NYMEX HO=F |
| `BRENT_REFETCH` / `BRENT_MAX_AGE` | `5 min` / `4 dias` | cadência e expiração do Brent |
| `SC_REFETCH` / `SC_MAX_AGE` | `5 min` / `4 dias` | cadência e expiração do Crude SC |
| `MURBAN_REFETCH` / `MURBAN_MAX_AGE` | `1 h` / `7 dias` | cadência e expiração do Murban |
| `URALS_REFETCH` / `URALS_MAX_AGE` | `1 h` / `7 dias` | cadência e expiração do Urals |
| `UREA_REFETCH` / `UREA_MAX_AGE` | `1 h` / `14 dias` | cadência e expiração das duas linhas de uréia |
| `SULFUR_REFETCH` / `SULFUR_MAX_AGE` | `1 h` / `14 dias` | cadência e expiração do enxofre |
| `MIN_W` / `MIN_H` / `EDGE_PX` | `200` / `150` / `6` | tamanho mínimo da janela e espessura da alça de resize (v7.1) |
| `MARGIN` / `MARGIN_Y` | `16` / `40` | distância da borda ao encostar no canto |

## Como funciona a camada da área de trabalho

O detalhe mais interessante do código: no GNOME/Mutter (X11), os ícones do desktop são uma janela do tipo `_NET_WM_WINDOW_TYPE_DESKTOP` (extensão DING). Janelas DESKTOP ficam todas na camada mais baixa e a ordem entre elas é definida por quem mapeia por último — uma corrida na inicialização que deixava o widget aleatoriamente atrás dos ícones.

A solução: o widget cria-se como tipo `desktop` e depois envia ao WM um *client message* pedindo o estado `_NET_WM_STATE_BELOW`. O Mutter então o coloca na camada BOTTOM — **entre** a camada DESKTOP (ícones) e a NORMAL (janelas): nunca atrás dos ícones, nunca na frente das suas janelas. Tudo via `ctypes` carregando libX11, sem dependências extras. Ao ativar "Manter no topo", o estado BELOW é removido e a janela volta ao tipo normal para o topmost valer.

## Changelog resumido

| Versão | Destaques |
|---|---|
| **v4** | BRL por grama, camada desktop, polling 90 s, backoff 429, baseline PAXG |
| **v5** | Painel completo da China (SGE, SHFE, base China Gold, barras de banco) + regras de normalização |
| **v5.1** | Remoção de cotações de varejo/reciclagem; fallback do spot via Sina `hf_XAU`; modo `--dump` |
| **v5.2** | Cadeia de fallback em **todas** as fontes (spot, câmbio, baseline, SHFE, base CN, barras) |
| **v5.3** | Fallback também quando a fonte responde sem dado; derivação só com câmbio fresco (<15 min); cache atômico |
| **v5.4** | Seção **EUA · Combustível** (média de varejo da bomba: gasolina regular + diesel on-highway, EIA) |
| **v5.5** | **Cadeia de fallback do combustível**: AmericasOilWatch → EIA dnav → FRED → EIA API v2 (opcional); header `Accept` global |
| **v5.6** | **Fusão das forks**: o repo passa a ter tudo — spot, China, COMEX GC=F e combustível com fallbacks |
| **v5.7** | Seção **BRASIL · RISCO SOBERANO**: CDS 5 anos (WGB, intraday) + PD implícita (40% de recuperação) |
| **v5.8** | **Fallback do CDS**: Investing.com `BRGV5YUSAC=R` (EOD, check no `lastUpdateTime`; fechamento anterior real = last − change) |
| **v5.9** | **Troca da fonte do combustível**: sai a EIA semanal, entra a **AAA Fuel Prices diária** (média nacional de varejo, variação vs ontem, refetch 1/h) |
| **v6.0** | **Gráficos no clique**: popup Canvas puro (7D/1M/3M/6M/1A), fallback no log local, menu "Ver gráfico" |
| **v6.1** | Seção **NYMEX · DIESEL (HO=F)**: futuro ULSD em US$/gal + equivalente US$/bbl; cadeia Yahoo → FXEmpire → TE |
| **v6.2** | Seção **RÚSSIA · CRUDE URALS** via OilPrice.com (tabela + freewidgets com CSRF) |
| **v6.3** | Seção **BRENT · CRUDE (BENCHMARK)** (Yahoo BZ=F → FXEmpire CFD → OilPrice) + **backoff por seção** |
| **v6.4** | **Backoff por fonte** (429 = falha dupla + jitter; fallback não anistia a primária), Yahoo-q2 em todos os futuros, throttle 1,5 s no Yahoo |
| **v6.5** | **Remoção** do futuro COMEX (GC=F) e de toda a seção China (SGE/SHFE, Base China Gold, barras de banco), a pedido |
| **v6.6** | Seção **FERTILIZANTE · UREIA**: spot intl. (TE → TV → Pink Sheet mensal) + CFR Brasil (UFB=F Yahoo → TV) |
| **v6.7** | Seção **ENXOFRE · SPOT CN**: TE → SunSirs (anti-bot `HW_CHECK` replicado), CNY/t → US$/t com câmbio fresco |
| **v6.8** | Seção **CHINA · CRUDE SC (XANGAI)**: futuro da INE via Sina → futsseapi → push2delay; US$/bbl com USDCNY fresco |
| **v6.9** | Seção **EMIRADOS · CRUDE MURBAN** via OilPrice.com (avaliação com delay de minutos); tabela OilPrice agora serve Urals + Brent + Murban com cache de 2 min |
| **v7.0** | **Urals com delay halvo (T+1)**: TradingEconomics (data real do resumo) e minfin.com.ua à frente do OilPrice.com (T+2); delay exibido calculado da data real do dado |
| **v7.1** | **Janela redimensionável** com alças invisíveis nas 4 bordas/4 cantos (resize direcional, mínimo 200×150), **rolagem oculta** (roda do mouse, sem barra na UI; texto não escala) e **tamanho persistente** no cache |
| **v7.2** | **Seção COBRE · COMEX (HG=F)** logo abaixo do spot: intraday US$/lb com cadeia Yahoo → FXEmpire (CFD Oanda) → TradingEconomics → cache 4d, gráfico 7D–1A no clique |
| **v7.3** | **Linha CU0 · SHFE (cobre da China)** na seção COBRE: contrato principal contínuo da SHFE em US$/lb (= CNY/t ÷ USDCNY ÷ 2204,62, câmbio fresco obrigatório), cadeia Sina → futsseapi → push2delay → cache 4d, variação vs settlement (convenção chinesa) |

## Licença

Uso pessoal.
