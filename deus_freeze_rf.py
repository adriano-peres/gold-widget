#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEUS-Freeze RF v3.2 — RATING-FREE (zero opinião de agência).
================================================================
v3.2 (out/26): MKT +vol de bonds. Pesquisa prévia (DGS10 2006→hoje):
correl. bondvol×VIX 0,67 (normas 0,57) — não redundante; explica o que o
VIX não vê (BREIT nov/22 com VIX calmo, rate-vol 2023, run-up 2007);
não lidera (breach empatado). Peso 0,20 no MKT (quinta voz igual →
5% efetivo): placar segue 7/7, placebo 2022 +3 meses (custo conhecido).
  1. MKT ..... preço de tela: 0,20×BONDVOL realizada DGS10 (stdev 21d
              das variações diárias em bp, média mensal; tudo Treasury)
              + 0,80×média de {VIX, DISTRESS<80c, OAS, TED} disponíveis.
  2. SLOOS ... survey do Fed — mantém âncoras v2.2.
  3. SOLV .... NCO FDIC (CORALACBN, ffill causal) + falências US Courts.
  4. FREEZE .. fila (eventos 0-1) — idêntico v2.2.
  1. MKT ..... preço de tela: VIX (2006→hoje) + DISTRESS <80c (LCD,
              âncoras mensais; pré-2023 = reconstrução aproximada
              PROVISÓRIA, 2026-07 = 6,89% LCD exato) + OAS HY e TED
              quando disponíveis (média das normas disponíveis).
              OAS é PREÇO de mercado, não voto de comitê (universo do
              cesto usa rating só p/ inclusão — limitação documentada).
  2. SLOOS ... survey do Fed (já era rating-free) — mantém âncoras v2.2.
  3. SOLV .... solvência realizada sem agência, 2 séries explícitas:
              a) NCO FDIC (FRED CORALACBN, trimestral → mensal por
                 forward-fill causal, 2006→hoje; pico 3,14% Q4/09);
              b) Falências US Courts (totais anuais, milhões;
                 2008 1,12 / 2009 1,40 / 2010 1,53 pico / 2020 0,52 /
                 2022 0,38 / 2023 0,43; 2006-07 e 2024-26 PROVISÓRIOS).
              n_solv = média das 2 normas. BDC/PIK (história curta,
              sem 2008) fica em WARN-ONLY, fora do causal.
  4. FREEZE .. fila (eventos 0-1) — idêntico v2.2, rating-free por natureza.

Fórmula: 25% mkt + 15% sloos + 25% solv + 35% freeze (pesos inalterados).

BANDAS: 0-30 CALMO / 30-60 ATENÇÃO / 60-80 TRAVA / 80-100 QUEBRA.

USO:
    python3 deus_index_rf.py [--out DIR] [--op DIR] [--end YYYY-MM]

SAÍDAS em OUT:
    - DEUS_RF_monthly.csv ..... série mensal causal + componentes
    - DEUS_RF_sensitivity.csv . 7 esquemas de peso nas 7 datas-chave
    - DEUS_RF_backtest.svg .... gráfico causal (linha única, sem legado)

DEPENDÊNCIAS: só stdlib.
"""

# ===========================================================================
# TRAVA ANTI-AGÊNCIA — NUNCA, JAMAIS, EM HIPÓTESE ALGUMA usar dados de
# agências de rating (Fitch / Moody's / S&P / Kroll / Morningstar DBRS / etc.)
# neste índice. Motivo: são dados de OPINIÃO HUMANA COLEGIADA (comitê de
# rating vota a nota; definição de "default" muda por metodologia) — não são
# fato observável de mercado, filing, Fed/FDIC ou tribunal. Este arquivo só
# aceita: preço de tela (VIX, TED, OAS), survey do Fed (SLOOS), filings
# contábeis/judiciais (FDIC QBP, US Courts, 10-Qs) e calendário de eventos.
# OAS (ICE BofA) entra como PREÇO de mercado — o número é spread negociado,
# não voto de comitê (o universo do cesto usa rating só p/ inclusão, limitação
# documentada; se um dia o OAS virar opinião, remover aqui também).
# ===========================================================================

BANNED_KEYWORDS = (
    "fitch", "moody", "moodys", "standardandpoor", "s&p", "snps",
    "kroll", "dbrs", "morningstar-rating", "pcdr", "dbaa", "daaa",
)
BANNED_COLUMNS = {"DBAA", "DAAA"}  # séries Moody's no FRED — proibidas aqui.


def _reject_agency_data(path, col):
    """Trava dura: aborta se path/col cheirar a agência de rating."""
    blob = f"{path} {col}".lower()
    if col in BANNED_COLUMNS or any(k in blob for k in BANNED_KEYWORDS):
        raise SystemExit(
            f"BLOQUEADO: '{col}' em '{path}' parece dado de agência de rating "
            f"(opinião humana colegiada). Este índice é rating-free por regra. "
            f"Use VIX/TED/OAS (preço), SLOOS (Fed), FDIC/Courts/10-Qs ou eventos."
        )

import argparse
import csv
import datetime as dt
import math
import os
import sys
import warnings
from collections import defaultdict

OUT_DEFAULT = os.environ.get("DEUS_OUT", "/tmp/tg-bridge/out")
OP_DEFAULT = os.environ.get("DEUS_OP", "/tmp/opencode")

W_MKT, W_SLOOS, W_SOLV, W_FREEZE = 0.25, 0.15, 0.25, 0.35

# Fed survey — não é agência de rating, mantido da v2.2.
SLOOS_ANCHORS = [
    ("2006-01", 0), ("2007-07", 10), ("2007-10", 30), ("2008-01", 55),
    ("2008-10", 70), ("2009-04", 50), ("2010-01", 5), ("2019-01", 10),
    ("2020-04", 70), ("2020-10", 10), ("2023-04", 45), ("2024-01", 15),
    ("2026-04", 0), ("2026-07", 0),
    ("2026-10", 0),  # PROVISÓRIO: repete Q2 até sair Q3 SLOOS fim-out/26.
]

# Solvência realizada SEM agência — séries explícitas (fase 1 v3.1).
# a) NCO vem do FRED (CORALACBN, FDIC/Call Reports) — ver main().
# b) Falências = totais anuais US Courts, em milhões. Pontos 2008-2023
#    conferem com estatísticas dos tribunais; 2006-07 e 2024-26 são
#    PROVISÓRIOS (TODO: confirmar em uscourts.gov e trocar por CSV).
BK_ANCHORS_RF = [
    ("2006-01", 0.80), ("2007-12", 0.85), ("2008-12", 1.12),
    ("2009-12", 1.40), ("2010-12", 1.53), ("2015-12", 0.84),
    ("2019-12", 0.77), ("2020-12", 0.52), ("2021-12", 0.40),
    ("2022-12", 0.38), ("2023-12", 0.43), ("2024-12", 0.49),
    ("2025-12", 0.54), ("2026-09", 0.56),  # PROVISÓRIOS (filings subindo).
]

# Distress <80c = PREÇO de tela (LCD/Morningstar LSTA), sem opinião.
# 2026-07 = 6,89% LCD (exato, tese #8b); 2022-12 = 7,0 (pico Q4 22 7,1-7,36%).
# Pré-2023 = reconstrução aproximada PROVISÓRIA (TODO: CSV LCD).
DISTRESS_ANCHORS_RF = [
    ("2006-01", 1.5), ("2007-07", 2.5), ("2008-03", 8.0),
    ("2008-09", 22.0), ("2008-12", 30.0), ("2009-12", 8.0),
    ("2015-12", 7.0), ("2019-12", 3.0), ("2020-03", 11.0),
    ("2020-07", 5.0), ("2022-12", 7.0), ("2024-12", 4.5),
    ("2026-07", 6.89), ("2026-08", 6.9),  # PROVISÓRIO pós-jul até LCD sair.
]

FREEZE_PERIODS = [
    ("2007-08", "2009-06", 1.0),
    ("2020-03", "2020-04", 1.0),
    ("2022-11", "2024-03", 0.4),
    ("2026-01", "2026-10", 0.7),
    ("2026-02", "2026-02", 0.85),  # OBDC II halt permanente 18/fev/26.
    ("2026-11", "2027-06", 0.5),   # PROJEÇÃO: backlog rolado. Revisar Q4/26.
]

KEY_DATES = ["2007-06", "2007-08", "2008-03", "2008-09", "2008-12", "2009-12",
             "2020-02", "2020-03", "2020-04", "2020-07", "2022-11", "2023-03",
             "2025-08", "2025-12", "2026-02", "2026-03", "2026-07", "2026-08",
             "2026-10", "2027-02"]


def load_fred(path, col):
    _reject_agency_data(path, col)  # trava anti-agência: opinião colegiada nunca entra.
    try:
        f = open(path, newline="", encoding="utf-8")
    except FileNotFoundError:
        serie = col.upper()
        raise SystemExit(
            f"FALTANDO {path}\nBaixe com:\n"
            f'  curl "https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}&cosd=2006-01-01" -o {path}'
        )
    with f:
        r = csv.DictReader(f)
        if col not in (r.fieldnames or []):
            raise SystemExit(f"{path}: coluna '{col}' não existe. Cabeçalho={r.fieldnames}")
        d = {}
        for row in r:
            txt = (row.get(col) or "").strip()
            if txt in ("", ".", "NA", "null", "None"):
                continue
            try:
                v = float(txt)
            except ValueError:
                continue
            day = (row.get("observation_date") or row.get("DATE") or "").strip()
            if day:
                d[day] = v
    if not d:
        raise SystemExit(f"{path}: zero linhas válidas na coluna {col}.")
    return d


def monthly_avg(daily):
    m = defaultdict(list)
    for d, v in daily.items():
        m[d[:7]].append(v)
    return {k: sum(v) / len(v) for k, v in m.items()}


def quarterly_ffill_monthly(q_daily, start, end):
    """Trimestral (ex: FRED CORALACBN) → mensal causal por forward-fill.

    Mês usa o último trimestre <= mês. Nunca vê o futuro.
    """
    qs = sorted(d for d in q_daily)
    out = {}
    qi = -1
    d = dt.datetime(start.year, start.month, 1)
    while d <= end:
        iso = d.strftime("%Y-%m-%d")
        while qi + 1 < len(qs) and qs[qi + 1][:10] <= iso:
            qi += 1
        if qi < 0:
            raise SystemExit("série trimestral começa após 2006-01.")
        out[d.strftime("%Y-%m")] = float(q_daily[qs[qi]])
        y, m = d.year, d.month
        d = dt.datetime(y + 1, 1, 1) if m == 12 else dt.datetime(y, m + 1, 1)
    return out


def realized_bondvol(dgs_daily, window=21):
    """Vol realizada de bonds sem agência: stdev móvel `window` dias das
    variações diárias do DGS10 em bp → média mensal. Tudo Treasury/FRED.
    Série mensal começa ~2006-02 (primeiros 21 pregões sem número)."""
    days = sorted(dgs_daily)
    rets = []
    prev = None
    for d in days:
        if prev is not None:
            rets.append((d, (dgs_daily[d] - prev) * 100.0))
        prev = dgs_daily[d]
    roll = {}
    for i in range(window - 1, len(rets)):
        win = [r for _, r in rets[i - window + 1:i + 1]]
        m = sum(win) / window
        var = sum((x - m) ** 2 for x in win) / window
        roll[rets[i][0]] = math.sqrt(var)
    return monthly_avg(roll)


W_BVOL = 0.20  # voz da bondvol dentro do MKT (pesquisa out/26: 5% efetivo).


def anchor_series(anchors, start, end):
    if not anchors:
        raise ValueError("anchors vazio.")
    pts = sorted((dt.datetime.strptime(k, "%Y-%m"), float(v)) for k, v in anchors)
    seen = [k for k, _ in pts]
    if len(set(seen)) != len(seen):
        warnings.warn("anchor duplicado; usando último valor de cada mês.")
        ded = {}
        for k, v in pts:
            ded[k] = v
        pts = sorted(ded.items())
    out = {}
    ai = 0
    d = start
    last_t, last_v = pts[-1]
    warned = False
    while d <= end:
        while ai + 1 < len(pts) and pts[ai + 1][0] <= d:
            ai += 1
        if ai + 1 < len(pts) and pts[ai][0] <= d < pts[ai + 1][0]:
            t0, v0 = pts[ai]
            t1, v1 = pts[ai + 1]
            span = (t1 - t0).days
            f_ = (d - t0).days / span if span > 0 else 0.0
            cur = v0 + (v1 - v0) * f_
        else:
            cur = pts[ai][1] if d >= pts[ai][0] else pts[0][1]
            if d > last_t and not warned:
                warnings.warn(
                    f"flat-forward após último anchor {last_t:%Y-%m} "
                    f"(valor {last_v}). Atualize anchors."
                )
                warned = True
        out[d.strftime("%Y-%m")] = cur
        y, m = d.year, d.month
        d = dt.datetime(y + 1, 1, 1) if m == 12 else dt.datetime(y, m + 1, 1)
    return out


def freeze_level(ym, periods):
    d = dt.datetime.strptime(ym, "%Y-%m")
    lv = 0.0
    for a, b, v in periods:
        if dt.datetime.strptime(a, "%Y-%m") <= d <= dt.datetime.strptime(b, "%Y-%m"):
            lv = max(lv, float(v))
    return lv


def expanding_norm(raw, min_window=24):
    months = sorted(raw)
    out = {}
    hist = []
    warned = False
    for m in months:
        v = float(raw[m])
        if len(hist) < min_window and not warned:
            warnings.warn(f"warmup {m}: n={len(hist)}<{min_window}, ruidoso (causal).",
                          stacklevel=2)
            warned = True
        if len(hist) >= 2:
            mean = sum(hist) / len(hist)
            var = sum((x - mean) ** 2 for x in hist) / len(hist)
            sd = math.sqrt(var) if var > 1e-12 else 1e-6
            z = (v - mean) / sd
        elif len(hist) == 1:
            z = 0.0 if v == hist[0] else (1.0 if v > hist[0] else -1.0)
        else:
            z = 0.0
        out[m] = max(0.0, min(100.0, 50.0 * (1.0 + math.erf(z / math.sqrt(2.0)))))
        hist.append(v)
    return out


def band(v):
    return "CALMO" if v < 30 else ("ATENÇÃO" if v < 60 else ("TRAVA" if v < 80 else "QUEBRA"))


def combine(n_mk, n_sl, n_sv, n_fr, w=(W_MKT, W_SLOOS, W_SOLV, W_FREEZE)):
    return {m: w[0] * n_mk[m] + w[1] * n_sl[m] + w[2] * n_sv[m] + w[3] * n_fr[m]
            for m in n_mk if m in n_sl and m in n_sv and m in n_fr}


def main(argv=None):
    ap = argparse.ArgumentParser(description="DEUS-Freeze RF v3.0 (rating-free).")
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--op", default=OP_DEFAULT)
    ap.add_argument("--end", default=None)
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    # --- MKT: VIX obrigatório (2006→hoje, puro mercado) + OAS/TED opcionais ---
    vix_d = load_fred(f"{args.op}/vix.csv", "VIXCLS")
    vix_m = monthly_avg(vix_d)
    opt_series = {}
    for fname, col, tag in [("oas.csv", "BAMLH0A0HYM2", "OAS"),
                            ("ted.csv", "TEDRATE", "TED")]:
        try:
            dd = load_fred(f"{args.op}/{fname}", col)
            mm = monthly_avg(dd)
            if len(mm) >= 12:
                opt_series[tag] = mm
            else:
                print(f"aviso: {tag} curto ({len(mm)} meses), ignorado no MKT.")
        except SystemExit as e:
            print(f"aviso: {tag} ausente ({e}). MKT usa VIX.")
    if args.end:
        end_dt = dt.datetime.strptime(args.end, "%Y-%m")
    else:
        end_dt = dt.datetime.strptime(sorted(vix_m)[-1][:7], "%Y-%m")
    start_dt = dt.datetime(2006, 1, 1)
    if end_dt < start_dt:
        raise SystemExit(f"--end antes de 2006-01.")

    sloos_m = anchor_series(SLOOS_ANCHORS, start_dt, end_dt)
    # SOLV explícito fase 1: NCO FDIC (FRED, ffill causal) + falências Courts.
    nco_d = load_fred(f"{args.op}/nco.csv", "CORALACBN")
    nco_m = quarterly_ffill_monthly(nco_d, start_dt, end_dt)
    bk_m = anchor_series(BK_ANCHORS_RF, start_dt, end_dt)
    distress_m = anchor_series(DISTRESS_ANCHORS_RF, start_dt, end_dt)
    bvol_m = realized_bondvol(load_fred(f"{args.op}/dgs10.csv", "DGS10"))
    months = sorted(set(vix_m) & set(sloos_m) & set(nco_m) & set(bk_m) & set(distress_m) & set(bvol_m))
    if len(months) < 200:
        raise SystemExit(f"meses com tudo: {len(months)} (<200). Verifique VIX/âncoras.")
    if months[0] != "2006-01":
        warnings.warn(f"série começa em {months[0]}, não 2006-01.")

    n_vix = expanding_norm({k: vix_m[k] for k in months})
    n_distress = expanding_norm({k: distress_m[k] for k in months})
    n_bvol = expanding_norm({k: bvol_m[k] for k in months})
    n_opts = [n_distress]  # vozes de preço p/ dividir os 80% (bondvol tem peso próprio).
    for tag, mm in opt_series.items():
        common = sorted(set(months) & set(mm))
        if len(common) >= 12:
            nn = expanding_norm({k: mm[k] for k in common})
            n_opts.append(nn)
    # MKT: W_BVOL p/ bondvol + resto dividido nas vozes de preço disponíveis.
    n_mkt = {}
    for m in months:
        base = [n_vix[m]] + [nn[m] for nn in n_opts if m in nn]
        n_mkt[m] = W_BVOL * n_bvol[m] + (1.0 - W_BVOL) * (sum(base) / len(base))
    n_sloos = expanding_norm({k: sloos_m[k] for k in months})
    # SOLV = média de charge-off realizado + falências (ambos sem agência).
    n_nco = expanding_norm({k: nco_m[k] for k in months})
    n_bk = expanding_norm({k: bk_m[k] for k in months})
    n_solv = {m: (n_nco[m] + n_bk[m]) / 2.0 for m in months}
    n_freeze = {k: freeze_level(k, FREEZE_PERIODS) * 100.0 for k in months}
    idx = combine(n_mkt, n_sloos, n_solv, n_freeze)

    last_fz = max(dt.datetime.strptime(b, "%Y-%m") for _, b, _ in FREEZE_PERIODS)
    end_ym = end_dt.strftime("%Y-%m")
    if end_ym not in idx:
        end_ym = months[-1]
        end_dt = dt.datetime.strptime(end_ym, "%Y-%m")
    if end_dt > last_fz:
        warnings.warn(f"fim {end_ym} PROJETADO após {last_fz:%Y-%m}: freeze=taper, não fato.")

    print(f"MKT: VIX {len(vix_m)} meses + DISTRESS(LCD) + opcionais {[k for k in opt_series]} (média de normas).")
    print(f"SOLV: NCO FDIC {len(nco_m)} meses (pico {max(nco_m.values()):.2f}%) + BK Courts (pico {max(bk_m.values()):.2f}M).")
    print(f"{'mes':<8} {'rf':>7}  banda      mkt  sloos  solv  frz")
    for m in KEY_DATES:
        if m in idx:
            print(f"{m:<8} {idx[m]:7.1f}  {band(idx[m]):<8} "
                  f"{n_mkt[m]:5.1f} {n_sloos[m]:5.1f} {n_solv[m]:5.1f} {n_freeze[m]:4.0f}")

    now = end_ym
    print(f"\nDECOMPOSIÇÃO {now} (RF {idx[now]:.1f} {band(idx[now])}):")
    for nome, w, n in [("mkt", W_MKT, n_mkt[now]), ("sloos", W_SLOOS, n_sloos[now]),
                       ("solv", W_SOLV, n_solv[now]), ("freeze", W_FREEZE, n_freeze[now])]:
        print(f"  {nome:<8} peso {w*100:4.0f}% x norm {n:5.1f} = {w*n:5.1f}pts")
    print(f"  (mkt: VIX {n_vix[now]:.1f} + DISTRESS {n_distress[now]:.1f} + BONDVOL {n_bvol[now]:.1f} = {n_mkt[now]:.1f}; "
          f"solv: NCO {nco_m[now]:.2f}%→{n_nco[now]:.1f} + BK {bk_m[now]:.2f}M→{n_bk[now]:.1f})")

    def checks(index):
        return [
            ("Bear mar/08 >60", index.get("2008-03", 0) > 60),
            ("Lehman set/08 >80", index.get("2008-09", 0) > 80),
            ("pico dez/08 >80", index.get("2008-12", 0) > 80),
            ("pré fev/20 <60", index.get("2020-02", 99) < 60),
            ("dash mar/20 >60", index.get("2020-03", 0) > 60),
            ("normalizou jul/20 <60", index.get("2020-07", 99) < 60),
            ("hoje 30-60", 30 <= index.get(now, 0) < 60),
        ]
    print("\nBACKTEST RF 2008/2020 (causal, sem agência):")
    ok = 0
    for name, p in checks(idx):
        ok += p
        print(f"  [{'OK' if p else 'FAIL'}] {name}")
    print(f"  {ok}/7")

    schemes = {
        "OFICIAL 25/15/25/35": (0.25, 0.15, 0.25, 0.35),
        "IGUAL 25/25/25/25": (0.25, 0.25, 0.25, 0.25),
        "SEM FREEZE": (0.25 / 0.65, 0.15 / 0.65, 0.25 / 0.65, 0.0),
        "SÓ MKT+SOLV": (0.5, 0.0, 0.5, 0.0),
        "FREEZE-50": (0.20, 0.10, 0.20, 0.50),
        "MKT-50": (0.50, 0.15, 0.25, 0.10),
        "AUDIT-SHOCK 25/15/35/25": (0.25, 0.15, 0.35, 0.25),
    }
    sens_dates = ["2008-03", "2008-09", "2008-12", "2020-02", "2020-03", "2020-07", now]
    print("\nSENSIBILIDADE (mesmos cortes):")
    print(f"  {'esquema':<22} " + " ".join(f"{d[2:]:>7}" for d in sens_dates) + "  placar")
    sens_rows = []
    for name, w in schemes.items():
        alt = combine(n_mkt, n_sloos, n_solv, n_freeze, w)
        vals = [alt.get(d, float("nan")) for d in sens_dates]
        sc = sum([vals[0] > 60, vals[1] > 80, vals[2] > 80, vals[3] < 60,
                  vals[4] > 60, vals[5] < 60, 30 <= vals[6] < 60])
        sens_rows.append((name, vals, sc))
        print(f"  {name:<22} " + " ".join(f"{v:7.1f}" for v in vals) + f"  {sc}/7")

    print("\nPLACEBO:")
    for label, a, b in [("2015-16", "2015-01", "2016-12"), ("2022", "2022-01", "2022-12")]:
        win = [idx[m] for m in months if a <= m <= b]
        if win:
            n_at = sum(v >= 30 for v in win)
            print(f"  {label}: max {max(win):.1f} {band(max(win))}, "
                  f"{n_at}/{len(win)} >=ATENÇÃO ({n_at/len(win)*100:.0f}%)")

    # ---- TESTES BACKLOG (fila) ----
    print("\nBACKLOG TESTS (fila/eventos):")
    bt = [
        ("freeze jan/26 ==0.70 (teto 5%)", abs(freeze_level("2026-01", FREEZE_PERIODS) - 0.70) < 1e-9),
        ("freeze fev/26 ==0.85 (OBDC II pico via max)", abs(freeze_level("2026-02", FREEZE_PERIODS) - 0.85) < 1e-9),
        ("freeze ago/25 ==0.00 (EO 401k não é stress)", abs(freeze_level("2025-08", FREEZE_PERIODS)) < 1e-9),
        ("freeze dez/26 ==0.50 (taper, sem cliff)", abs(freeze_level("2026-12", FREEZE_PERIODS) - 0.50) < 1e-9),
        ("freeze mar/20 ==1.00 (dash)", abs(freeze_level("2020-03", FREEZE_PERIODS) - 1.0) < 1e-9),
        ("overlap usa max (fev/26 >= jan/26)", freeze_level("2026-02", FREEZE_PERIODS) >= freeze_level("2026-01", FREEZE_PERIODS)),
        ("KEY_DATES com guard (2025-08 em idx)", "2025-08" in idx),
        ("KEY_DATES com guard (2026-02 em idx)", "2026-02" in idx),
        ("NCO pico 2009-Q4 ==3.14% (FDIC)", abs(nco_m.get("2009-10", 0) - 3.14) < 1e-9),
        ("BK pico 2010 (1.53M) > BK 2026 (0.56M)", bk_m.get("2010-12", 0) > bk_m.get("2026-09", 0)),
        ("distress dez/08 (30) > distress jul/26 (6.89)", distress_m.get("2008-12", 0) > distress_m.get("2026-07", 0)),
        ("bondvol out/08 pico > media (pesquisa 6/6)", bvol_m.get("2008-10", 0) > 5.16),
        ("bondvol mar/20 > fev/20 (spike no dash)", bvol_m.get("2020-03", 0) > bvol_m.get("2020-02", 0)),
        ("bondvol out/22 elevada no ciclo de hikes", bvol_m.get("2022-10", 0) > 5.0),
        ("bondvol nov/23 diverge do VIX (rates sem acoes)", bvol_m.get("2023-11", 0) > 7.0 and vix_m.get("2023-11", 99) < 15),
        ("bondvol fev/26 calma no halt (era credito)", bvol_m.get("2026-02", 0) < 4.0),
    ]
    bok = 0
    for name, p in bt:
        bok += bool(p)
        print(f"  [{'OK' if p else 'FAIL'}] {name}")
    print(f"  {bok}/{len(bt)}")

    print("\nWARN-ONLY (fora do placar): MCO>6 / PMR>9,5 / surrender>2% / secundário<80% / 401k / auditor.")

    with open(f"{args.out}/DEUS_RF_monthly.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mes", "deus_rf", "banda", "vix", "bondvol_bp", "nco_pct", "bk_mln", "distress_pct",
                    "sloos_tight", "freeze",
                    "n_mkt", "n_sloos", "n_solv", "n_freeze", "freeze_proj"])
        for m in months:
            proj = 1 if dt.datetime.strptime(m, "%Y-%m") > dt.datetime.strptime("2026-10", "%Y-%m") else 0
            w.writerow([m, f"{idx[m]:.1f}", band(idx[m]), f"{vix_m[m]:.2f}",
                        f"{bvol_m[m]:.2f}", f"{nco_m[m]:.2f}", f"{bk_m[m]:.3f}", f"{distress_m[m]:.2f}",
                        f"{sloos_m[m]:.1f}", f"{freeze_level(m, FREEZE_PERIODS):.2f}",
                        f"{n_mkt[m]:.1f}", f"{n_sloos[m]:.1f}", f"{n_solv[m]:.1f}",
                        f"{n_freeze[m]:.0f}", proj])
    print(f"\nCSV: {args.out}/DEUS_RF_monthly.csv ({len(months)} meses)")
    with open(f"{args.out}/DEUS_RF_sensitivity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["esquema"] + sens_dates + ["placar"])
        for name, vals, sc in sens_rows:
            w.writerow([name] + [f"{v:.1f}" for v in vals] + [f"{sc}/7"])
    print(f"CSV: {args.out}/DEUS_RF_sensitivity.csv")

    try:
        W, H, PL, PR, PT, PB = 1100, 420, 55, 15, 30, 35
        iw, ih = W - PL - PR, H - PT - PB
        n = len(months)
        if n < 2:
            raise ValueError("meses insuficientes.")
        X = lambda i: PL + iw * i / (n - 1)
        Y = lambda v: PT + ih * (1 - v / 100)
        pts = " ".join(f"{X(i):.1f},{Y(idx[m]):.1f}" for i, m in enumerate(months))
        bands = [(0, 30, "#e8f5e9"), (30, 60, "#fff9c4"), (60, 80, "#ffe0b2"), (80, 100, "#ffcdd2")]
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif">']
        svg.append(f'<rect width="{W}" height="{H}" fill="white"/>')
        svg.append(f'<text x="{W//2}" y="20" text-anchor="middle" font-size="15" font-weight="bold">'
                   f'DEUS-Freeze RF v3.2 2006-{end_ym[:4]} — rating-free (VIX+BONDVOL+DISTRESS+SLOOS+NCO+BK+FREEZE)</text>')
        for lo, hi, col in bands:
            svg.append(f'<rect x="{PL}" y="{Y(hi)}" width="{iw}" height="{Y(lo)-Y(hi)}" fill="{col}" opacity="0.55"/>')
        for y, t in [(30, "30 calmo"), (60, "60 trava"), (80, "80 quebra")]:
            svg.append(f'<line x1="{PL}" y1="{Y(y)}" x2="{W-PR}" y2="{Y(y)}" stroke="#888" stroke-dasharray="5,4" stroke-width="1"/>')
            svg.append(f'<text x="{PL+3}" y="{Y(y)-4}" font-size="10" fill="#555">{t}</text>')
        events = [("ABCP ago/07", "2007-08"), ("Bear mar/08", "2008-03"),
                  ("Lehman set/08", "2008-09"), ("dash mar/20", "2020-03"),
                  ("BREIT gate nov/22", "2022-11"), ("EO 401k ago/25", "2025-08"),
                  ("PC gates Q1/26", "2026-01"), ("OBDC II halt fev/26", "2026-02"),
                  ("PC stress ago/26 (ref)", "2026-08")]
        for label, c in events:
            if c in months:
                x = X(months.index(c))
                svg.append(f'<line x1="{x:.1f}" y1="{PT}" x2="{x:.1f}" y2="{H-PB}" stroke="#999" stroke-dasharray="2,3" stroke-width="1"/>')
                svg.append(f'<text x="{x+3:.1f}" y="{PT+10}" font-size="9" fill="#333" '
                           f'transform="rotate(90 {x+3:.1f},{PT+10})">{label}</text>')
        for i, m in enumerate(months):
            if m.endswith("-01") and int(m[:4]) % 2 == 0:
                svg.append(f'<text x="{X(i):.1f}" y="{H-12}" font-size="10" fill="#555" text-anchor="middle">{m[:4]}</text>')
        for v in [0, 20, 40, 60, 80, 100]:
            svg.append(f'<text x="{PL-8}" y="{Y(v)+3}" font-size="10" fill="#555" text-anchor="end">{v}</text>')
        svg.append(f'<polyline points="{pts}" fill="none" stroke="#2e7d32" stroke-width="2"/>')
        if now in months:
            i_now = months.index(now)
            svg.append(f'<circle cx="{X(i_now):.1f}" cy="{Y(idx[now]):.1f}" r="5" fill="#2e7d32"/>')
            svg.append(f'<text x="{X(i_now)-8:.1f}" y="{Y(idx[now])-10:.1f}" font-size="11" font-weight="bold" '
                       f'fill="#2e7d32" text-anchor="end">hoje {idx[now]:.0f}</text>')
        svg.append(f'<text x="{W-PR-5}" y="{H-12}" font-size="10" fill="#555" text-anchor="end">verde=RF v3 sem Fitch/Moody\'s/SP</text>')
        svg.append('</svg>')
        with open(f"{args.out}/DEUS_RF_backtest.svg", "w", encoding="utf-8") as f:
            f.write("\n".join(svg))
        print(f"SVG: {args.out}/DEUS_RF_backtest.svg")
    except Exception as e:
        print(f"sem gráfico: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
