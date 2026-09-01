# Ouro Widget

![Python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![Plataforma](https://img.shields.io/badge/plataforma-Linux%20%C2%B7%20X11-FCC624?logo=linux&logoColor=black)
![Dependências](https://img.shields.io/badge/depend%C3%AAncias-somente%20stdlib-00A86B)
![Versão](https://img.shields.io/badge/vers%C3%A3o-v5.6-c9a227)
![Licença](https://img.shields.io/badge/licen%C3%A7a-uso%20pessoal-lightgrey)

Widget de desktop em **Python puro** (tkinter) que mostra o **preço do ouro spot em tempo real** direto na sua área de trabalho — em **USD/onça** e **R$/grama** — além de um painel completo com as cotações do mercado chinês de ouro (SGE, SHFE, referência China Gold e barras de ouro dos grandes bancos), o **futuro COMEX (GC=F)** e a **média semanal de varejo dos combustíveis nos EUA** (gasolina e diesel de bomba, US$/gal).

> Sem chaves de API, sem pip, sem dependências externas.
> Só a stdlib: `tkinter` + `urllib` (+ `ctypes` para o truque de camada no X11).

---

## Sumário

- [O que ele faz](#o-que-ele-faz)
- [Recursos](#recursos)
- [Fontes de dados e cadeia de fallback](#fontes-de-dados-e-cadeia-de-fallback)
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

Um cartão discreto no canto superior direito da tela que exibe:

```
OURO · SPOT
US$ 4,615.47   ▲ 0.42% no dia   ▲ 1.87% na semana
R$ 885,32/g    ▼ 0.11% no dia   ▲ 1.52% na semana
bid 4,614.80 · ask 4,616.10 · há 34s

── COMEX · FUTURO (GC=F) ──
GC=F · dez/26 · contango +64          US$ 4,668.00        ▼ 0.21%

── CHINA · BOLSAS (SGE/SHFE) ──
SGE Au99.99              R$ 890,12/g        ▲ 0.35%
SGE Au(T+D)              R$ 888,90/g        ▲ 0.31%
SHFE futuro principal    R$ 892,44/g        ▲ 0.40%

── CHINA · REFERÊNCIA ──
Base China Gold          R$ 884,05/g

── CHINA · BARRAS DE BANCO ──
ICBC Ruyi                R$ 905,30/g
Banco da China           R$ 903,85/g
CCB Longding             R$ 906,10/g
...

── EUA · COMBUSTÍVEL (MÉDIA VAREJO) ──
Gasolina (regular)       US$ 3.134/g        ▲ 0.92%
Diesel (on-highway)      US$ 3.582/g        ▼ 0.44%

SGE 2108 14:30 Pequim · China há 41s
```

- **Linha principal:** spot internacional em USD/onça troy + equivalente em reais por grama.
- **Variação no dia:** comparada com a abertura do dia (UTC), medida pelo PAXG (ouro tokenizado, proxy grátis do spot).
- **Variação na semana:** comparada com o candle de 7 dias atrás.
- **Futuro COMEX (GC=F):** contrato contínuo do Yahoo Finance, com contango vs spot — rola sozinho para o vencimento mais líquido.
- **Painel China:** bolsas de Shangai (SGE/SHFE), base oficial de referência e barras de investimento vendidas por bancos chineses — tudo convertido pra R$/grama.
- **Combustível EUA:** média semanal de **varejo (bomba, com impostos)** da gasolina regular e do diesel on-highway da EIA.

## Recursos

- Spot **USD/BRL** com cadeia de fallback em 3 níveis (`goldprice.dev` → Sina → `goldprice.org`)
- Câmbio USD/BRL e CNY/BRL com 3 fontes (`awesomeapi` → `currency-api`/jsDelivr → `open.er-api.com`)
- Baseline diário/semanal via **PAXG**: Binance → OKX (fora da quota da API principal)
- Bolsas chinesas: **SGE** (Au99.99 e Au(T+D)) e futuro **SHFE**, via Sina/Eastmoney
- **Futuro COMEX (GC=F)** contínuo via chart do Yahoo Finance, com contango vs spot e marca "(cache)" após 10 min sem atualização
- **Combustível EUA (varejo/bomba)**: gasolina regular e diesel on-highway da EIA, com variação semanal
- Referência **China Gold** (jijinhao JO_52683) e barras de ouro de banco (xxapi), com nomes traduzidos
- Cada fonte falha isoladamente — uma API fora do ar não derruba as outras
- Tolerância a HTTP **429**: respeita o `retry_after_seconds` informado pela API
- **Cache local atômico** (`.tmp` + `os.replace`): reinicia mostrando o último preço conhecido
- Indicador de frescor: "há Ns", fonte alternativa em uso e aviso "spot offline (cache)"
- Derivação conservadora: só calcula BRL/base CN a partir de câmbio com **até 15 min** de idade
- Modo `--dump`: busca tudo pela linha de comando, sem interface gráfica
- Arrastável, com menu de contexto, encostar no canto e opção "manter no topo"

## Fontes de dados e cadeia de fallback

Toda fonte tem plano B (e C). Se uma responde erro **ou responde sem dado**, a próxima entra automaticamente.

| Dado | 1ª escolha | Fallback 1 | Fallback 2 |
|---|---|---|---|
| Spot USD (onça) | `goldprice.dev` | Sina `hf_XAU` (Londres) | `goldprice.org` |
| Spot BRL (onça) | `goldprice.dev` | derivado: USD × USDBRL | `goldprice.org/BRL` |
| Câmbio USD/BRL, CNY/BRL | awesomeapi | currency-api (jsDelivr) | open.er-api.com |
| Baseline do dia/semana (PAXG) | Binance klines | OKX candles 1Dutc | — |
| Variação semanal do dólar | awesomeapi daily | snapshot histórico jsDelivr (−7d) | — |
| SGE Au99.99 / Au(T+D) | Sina `gds_*` | Eastmoney `118.*` | cache |
| Futuro SHFE (contrato main) | Eastmoney `113.aum` | Sina `nf_AU0` | cache |
| Base China Gold | jijinhao JO_52683 | derivada do spot intl (hf_XAU × USDCNY ÷ 31.1034768) | — |
| Barras de ouro de banco | xxapi | cache de até 24h (depois sai da lista) | — |
| Futuro COMEX (GC=F) | Yahoo Finance chart | cache (marca "(cache)" após 10 min) | — |
| Combustível EUA — gasolina + diesel (varejo) | AmericasOilWatch | EIA dnav oficial (tabela HTML semanal) | FRED (só gasolina) · EIA API v2* |

\* A EIA API v2 é opcional: sem a variável de ambiente `EIA_API_KEY` (chave grátis em `eia.gov/opendata/register.php`) essa camada é pulada. Todas as fontes de combustível replicam a **mesma métrica de varejo de bomba com impostos** (séries EIA `EMM_EPMR_PTE_NUS_DPG` e `EMD_EPD2D_PTE_NUS_DPG`) — nada de preço de atacado.

Detalhes de robustez:

- A Sina exige header `Referer` e devolve GBK — tratado. O jijinhao bloqueia user-agent "de robô" — enviado UA de navegador.
- A Eastmoney às vezes responde **HTTP 200 sem preço** (`f43="-"`): isso também dispara o fallback.
- Barras de banco com mais de 24 h sem atualização são removidas da tela (nada de preço velho). Combustível vence após **14 dias** (2 releases semanais perdidas).
- As fontes de fallback do combustível usam timeout frouxo (30 s): só rodam quando a principal já falhou, e a tabela do dnav é lenta (~10 s) via urllib.
- Se o baseline (PAXG) for de outro dia UTC, a variação "no dia" entra em pausa em vez de mentir.

## Regras de normalização de preço

Para não misturar unidade com moeda, a exibição segue duas regras fixas:

| Cotação vem como | Exibida sempre como | Conversão |
|---|---|---|
| Preço **por grama** (CNY/g) | **R$/g** | `CNY/g × CNYBRL` |
| Preço **por onça troy** (qualquer moeda) | **USD/oz** | `CNY/oz ÷ USDCNY`, com `USDCNY = USDBRL ÷ CNYBRL` |

A variação percentual do BRL compõe ouro × dólar:
`(1 + var_ouro) × (1 + var_câmbio) − 1`.

Formatação local: padrão US para USD (`4,615.47`) e padrão BR para BRL (`23.823,37`).

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

O polling roda em thread separada a cada **90 s** (abaixo do teto anônimo de ~100 req/h da goldprice.dev).

## Interações com o widget

| Ação | Resultado |
|---|---|
| **Arrastar** com o botão esquerdo | move o widget para onde quiser |
| **Duplo clique** | encosta no canto superior direito |
| **Botão direito** | abre o menu |
| Menu → *Atualizar agora* | força um refresh imediato (não empilha com o poller em curso) |
| Menu → *Manter no topo* | alterna entre ficar sob as janelas (padrão) e sempre visível |
| Menu → *Encostar no canto* | volta para a posição padrão |
| Menu → *Sair* | encerra |

Por padrão o widget vive numa camada especial: **acima dos ícones do desktop e abaixo de qualquer janela** — ele não atrapalha seu trabalho e não some atrás dos ícones.

## Modo `--dump` (sem interface)

Útil para testar fontes, agendar via cron ou usar em servidor:

```text
$ python3 gold_widget.py --dump
FX [awesomeapi]: USDBRL 5.4120 · CNYBRL 0.7648 · USDCNY 7.0773
goldprice.dev XAU-USD-SPOT: 4,615.47 (bid 4614.9 · ask 4616.0)
goldprice.dev XAU-BRL-SPOT: 24,973.10 (bid 24970.0 · ask 24976.0)
Sina hf_XAU (spot Londres USD): 4,614.92 (+0.38% no dia)
Yahoo GC=F (Gold Dec 26) futuro COMEX: 4,668.00 (fech. ant. 4,658.20 · +0.21%)
US FUEL [EIA via AmericasOilWatch]: gasolina 3.134 US$/gal · diesel 3.582 US$/gal (semana 2026-08-24) (Δ semana: gasolina +0.029, diesel -0.016)

CHINA — normalizado (grama->BRL · onça->USD):
  SGE Au99.99                            782.10 CNY/g -> R$    598.17/g   +0.35%   Sina 2026-08-21 14:30:00
  SGE Au(T+D)                            780.95 CNY/g -> R$    597.29/g   +0.31%   Sina 2026-08-21 14:30:00
  SHFE futuro principal                  783.60 CNY/g -> R$    599.31/g   +0.40%   Eastmoney
  Base China Gold                        779.02 CNY/g -> R$    595.81/g            jijinhao
  Barra ICBC Ruyi                        793.00 CNY/g -> R$    606.53/g
  Barra Banco da China                   791.50 CNY/g -> R$    605.39/g
```

*(valores ilustrativos)*

## Arquivos e cache

| Caminho | Função |
|---|---|
| `~/.local/share/gold-widget/last_price.json` | cache do último estado conhecido (escrita **atômica**) |
| `~/.local/share/gold-widget/widget.log` | log de eventos, falhas de fonte e fallbacks acionados |

No boot o widget renderiza imediatamente o cache enquanto busca dados novos; se tudo estiver offline, mostra o rodapé `spot offline (cache)`.

## Configurações ajustáveis

Constantes no topo do `gold_widget.py`:

| Constante | Padrão | Descrição |
|---|---|---|
| `POLL_SECONDS` | `90` | intervalo entre buscas (respeite a quota da API) |
| `NET_TIMEOUT` | `8` | timeout de rede em segundos |
| `FX_MAX_AGE` | `15 min` | câmbio mais velho que isso não é usado p/ derivação |
| `BANKS_MAX_AGE` | `24 h` | idade máxima das barras de banco em cache |
| `FUT_STALE` | `10 min` | GC=F mais velho que isso exibe "(cache)" |
| `FUEL_MAX_AGE` | `14 dias` | cache de combustível expira (2 releases perdidas) |
| `EIA_API_KEY` (ambiente) | — | ativa a camada final da EIA API v2 (opcional) |
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
| **v5.3** | Fallback também quando a fonte responde sem dado; derivação só com câmbio fresco (<15 min); indicador independente para China; lock entre poller e refresh manual; cache atômico |
| **v5.4** | Seção **EUA · Combustível** (média de varejo da bomba: gasolina regular + diesel on-highway, EIA) e, na cópia instalada, o futuro **COMEX GC=F** |
| **v5.5** | **Cadeia de fallback do combustível**: AmericasOilWatch → EIA dnav → FRED → EIA API v2 (opcional); expiração do cache em 14 dias; header `Accept` global (FRED tarja requisições sem ele) |
| **v5.6** | **Fusão das forks**: o repo passa a ter tudo — spot, China, COMEX GC=F e combustível com fallbacks |

## Licença

Uso pessoal.
