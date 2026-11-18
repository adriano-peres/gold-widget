#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Suite USDT/BRL (v8.7) — campo visível CÂMBIO · USDT/BRL.

Cobre, offline (mocks, sem rede):
  * validação numérica (faixa 1..20, NaN/inf/lixo) e mid bid/ask/buy/sell;
  * parser de cada exchange: Binance (api + espelho vision), Bybit, Bitget
    e BitPreco — payload bom, um lado só, zeros, strings, símbolo errado,
    retCode/code de erro, lista vazia, 429;
  * cascata Binance -> Bybit -> Bitget -> BitPreco, cooldown por fonte,
    429 = falha dupla, sucesso limpa cooldown, todas mortas = RuntimeError;
  * séries históricas: Binance klines -> Bybit -> CoinGecko -> Bitget,
    normalização/dedupe/sort, dia UTC, janelas 7/30/90/180/365, log local;
  * rota fetch_history("usdtbrl"), HIST_META, backfill, render e migração
    do cache fiat antigo;
  * fuzz com milhares de payloads aleatórios (não trava, não vaza fiat).

Roda offline (padrão):  python3 test_usdtbrl.py
Roda com rede real:     python3 test_usdtbrl.py --live
"""
import inspect
import math
import random
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import gold_widget as gw

LIVE = "--live" in sys.argv
_log_patch = None


def setUpModule():
    global _log_patch
    _log_patch = patch.object(gw, "log", lambda *a, **k: None)
    _log_patch.start()


def tearDownModule():
    if _log_patch is not None:
        _log_patch.stop()


def _ms(dt):
    """datetime UTC -> epoch ms (klines/candles)."""
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def _days(n, start="2026-08-01"):
    d0 = datetime.strptime(start, "%Y-%m-%d")
    return [d0 + timedelta(days=i) for i in range(n)]


def _json_router(mapping, default=None):
    """_get_json falso: escolhe a resposta pela substring da URL."""
    calls = []

    def _fake(url, headers=None, timeout=None):
        calls.append(url)
        for frag, val in mapping.items():
            if frag in url:
                if isinstance(val, Exception):
                    raise val
                return val
        if isinstance(default, Exception):
            raise default
        return default
    _fake.calls = calls
    return _fake


class _Base(unittest.TestCase):
    def setUp(self):
        gw._SRC_RETRY.clear()
        gw._RETRY.clear()


# =========================== VALIDAÇÃO NUMÉRICA ===========================
class TestNumericos(_Base):
    def test_num_pos_aceita(self):
        for v in (1, 5.8, "5.8", " 5.8103 ", 1e-3, "1e1", 19.99):
            with self.subTest(v=v):
                out = gw._num_pos(v)
                self.assertIsNotNone(out)
                self.assertGreater(out, 0)

    def test_num_pos_rejeita(self):
        for v in (None, "", "  ", "x", "5,8", 0, -0.0, -1, float("nan"),
                  float("inf"), float("-inf"), [], {}, object()):
            with self.subTest(v=v):
                self.assertIsNone(gw._num_pos(v))

    def test_mid_price(self):
        self.assertAlmostEqual(gw._mid_price(5.8, 5.9), 5.85)
        self.assertAlmostEqual(gw._mid_price("5.8", "5.9"), 5.85)
        self.assertEqual(gw._mid_price(None, 5.9), 5.9)
        self.assertEqual(gw._mid_price(5.8, None), 5.8)
        self.assertEqual(gw._mid_price(0, 5.9), 5.9)
        self.assertEqual(gw._mid_price(5.8, 0), 5.8)
        self.assertEqual(gw._mid_price("x", 5.9), 5.9)
        for a, b in ((None, None), (0, 0), ("x", "y"), (float("nan"), None)):
            with self.assertRaises(ValueError):
                gw._mid_price(a, b)

    def test_ok_limites(self):
        for v in (1.0, 1.0001, 5.8123, 19.999, 20.0, "5.8", 6):
            with self.subTest(v=v):
                self.assertGreaterEqual(gw._ok_usdtbrl(v), 1.0)
        for v in (0.99, 20.0001, 0, -1, "x", None, float("nan"),
                  float("inf"), float("-inf"), [], {}):
            with self.subTest(v=v):
                with self.assertRaises(ValueError):
                    gw._ok_usdtbrl(v)

    def test_fuzz_numericos_3000(self):
        rnd = random.Random(20261118)
        pool = [None, "", " ", "abc", "5,8", "NaN", "inf", "-inf",
                0, -0.0, -1, 1.0, 20.0, 20.0001, 5.8123, 1e-9, 1e9,
                float("nan"), float("inf"), float("-inf"), [], {}, True]
        for i in range(3000):
            v = rnd.choice(pool + [rnd.uniform(-30, 30),
                                   str(rnd.uniform(-30, 30))])
            n = gw._num_pos(v)
            if n is not None:
                self.assertTrue(math.isfinite(n))
                self.assertGreater(n, 0)
            try:
                ok = gw._ok_usdtbrl(v)
                self.assertTrue(math.isfinite(ok))
                self.assertTrue(1.0 <= ok <= 20.0)
            except ValueError:
                pass
            except Exception as e:
                self.fail(f"_ok_usdtbrl({v!r}) erro inesperado no caso {i}: {e}")


# ================================ BINANCE =================================
class TestBinance(_Base):
    def test_book_ok_mid(self):
        p = {"symbol": "USDTBRL", "bidPrice": "5.8102",
             "askPrice": "5.8104"}
        with patch.object(gw, "_get_json", return_value=p):
            self.assertAlmostEqual(gw._usdtbrl_binance(), 5.8103)

    def test_um_lado_so(self):
        for p, exp in (({"symbol": "USDTBRL", "bidPrice": "5.81",
                         "askPrice": "0"}, 5.81),
                       ({"symbol": "USDTBRL", "bidPrice": "", "askPrice": "5.82"},
                        5.82)):
            with self.subTest(p=p):
                with patch.object(gw, "_get_json", return_value=p):
                    self.assertAlmostEqual(gw._usdtbrl_binance(), exp)

    def test_sem_preco(self):
        with patch.object(gw, "_get_json",
                          return_value={"symbol": "USDTBRL"}):
            with self.assertRaises(ValueError):
                gw._usdtbrl_binance()

    def test_simbolo_errado(self):
        p = {"symbol": "BTCUSDT", "bidPrice": "5.8", "askPrice": "5.9"}
        with patch.object(gw, "_get_json", return_value=p):
            with self.assertRaises(ValueError):
                gw._usdtbrl_binance()

    def test_nan(self):
        p = {"symbol": "USDTBRL", "bidPrice": "NaN", "askPrice": "inf"}
        with patch.object(gw, "_get_json", return_value=p):
            with self.assertRaises(ValueError):
                gw._usdtbrl_binance()

    def test_espelho_vision(self):
        calls = []

        def fake(url, headers=None, timeout=None):
            calls.append(url)
            if "api.binance.com" in url:
                raise Exception("HTTP 429")
            return {"symbol": "USDTBRL", "bidPrice": "5.80",
                    "askPrice": "5.82"}
        with patch.object(gw, "_get_json", side_effect=fake):
            self.assertAlmostEqual(gw._usdtbrl_binance(), 5.81)
        self.assertTrue(any("vision" in u for u in calls))

    def test_hosts_mortos(self):
        with patch.object(gw, "_get_json", side_effect=Exception("HTTP 500")):
            with self.assertRaises(ValueError) as cm:
                gw._usdtbrl_binance()
            self.assertIn("Binance", str(cm.exception))

    def test_payload_none(self):
        with patch.object(gw, "_get_json", return_value=None):
            with self.assertRaises(ValueError):
                gw._usdtbrl_binance()


# ================================= BYBIT ==================================
class TestBybit(_Base):
    def _p(self, **kw):
        t = {"symbol": "USDTBRL", "bid1Price": "5.8304",
             "ask1Price": "5.8380", "lastPrice": "5.835"}
        t.update(kw)
        return {"retCode": 0, "retMsg": "OK",
                "result": {"symbol": "USDTBRL", "list": [t]}}

    def test_ok_mid(self):
        with patch.object(gw, "_get_json", return_value=self._p()):
            self.assertAlmostEqual(gw._usdtbrl_bybit(), 5.8342)

    def test_last_fallback(self):
        p = self._p(bid1Price="", ask1Price="0")
        with patch.object(gw, "_get_json", return_value=p):
            self.assertAlmostEqual(gw._usdtbrl_bybit(), 5.835)

    def test_retcode_erro(self):
        with patch.object(gw, "_get_json",
                          return_value={"retCode": 10001, "retMsg": "erro"}):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bybit()

    def test_lista_vazia(self):
        p = {"retCode": 0, "result": {"list": []}}
        with patch.object(gw, "_get_json", return_value=p):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bybit()

    def test_simbolo_errado(self):
        p = self._p(symbol="ETHBRL")
        with patch.object(gw, "_get_json", return_value=p):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bybit()

    def test_sem_nenhum_preco(self):
        p = self._p(bid1Price="", ask1Price="", lastPrice="")
        with patch.object(gw, "_get_json", return_value=p):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bybit()


# ================================= BITGET =================================
class TestBitget(_Base):
    def _p(self, **kw):
        t = {"symbol": "USDTBRL", "bidPr": "5.8191", "askPr": "5.8260",
             "lastPr": "5.8308"}
        t.update(kw)
        return {"code": "00000", "msg": "success", "data": [t]}

    def test_ok_mid(self):
        with patch.object(gw, "_get_json", return_value=self._p()):
            self.assertAlmostEqual(gw._usdtbrl_bitget(), 5.82255)

    def test_last_fallback(self):
        p = self._p(bidPr="0", askPr="")
        with patch.object(gw, "_get_json", return_value=p):
            self.assertAlmostEqual(gw._usdtbrl_bitget(), 5.8308)

    def test_code_erro(self):
        with patch.object(gw, "_get_json",
                          return_value={"code": "40001", "msg": "erro"}):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bitget()

    def test_data_vazia(self):
        with patch.object(gw, "_get_json",
                          return_value={"code": "00000", "data": []}):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bitget()

    def test_simbolo_errado(self):
        p = self._p(symbol="BTCBRL")
        with patch.object(gw, "_get_json", return_value=p):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bitget()


# ================================ BITPRECO ================================
class TestBitPreco(_Base):
    def _p(self, **kw):
        p = {"success": True, "market": "USDT-BRL", "last": 5.8038,
             "buy": 5.8068, "sell": 5.8120}
        p.update(kw)
        return p

    def test_ok_mid(self):
        with patch.object(gw, "_get_json", return_value=self._p()):
            self.assertAlmostEqual(gw._usdtbrl_bitpreco(), 5.8094)

    def test_last_fallback(self):
        with patch.object(gw, "_get_json",
                          return_value=self._p(buy=None, sell=None)):
            self.assertAlmostEqual(gw._usdtbrl_bitpreco(), 5.8038)

    def test_success_false(self):
        with patch.object(gw, "_get_json",
                          return_value={"success": False, "market": "USDT-BRL"}):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bitpreco()

    def test_par_errado(self):
        with patch.object(gw, "_get_json",
                          return_value=self._p(market="BTC-BRL")):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bitpreco()

    def test_tudo_vazio(self):
        with patch.object(gw, "_get_json",
                          return_value=self._p(buy="", sell="", last="")):
            with self.assertRaises(ValueError):
                gw._usdtbrl_bitpreco()


# ================================ CADEIA ==================================
class TestCadeia(_Base):
    def _patch(self, **over):
        fns = {"_usdtbrl_binance": 5.81, "_usdtbrl_bybit": 5.83,
               "_usdtbrl_bitget": 5.82, "_usdtbrl_bitpreco": 5.80}
        fns.update(over)
        stack = []
        for name, val in fns.items():
            if isinstance(val, Exception):
                p = patch.object(gw, name, side_effect=val)
            elif val is None:
                p = patch.object(gw, name, return_value=None)
            else:
                p = patch.object(gw, name, return_value=val)
            stack.append(p)
            p.start()
            self.addCleanup(p.stop)
        return fns

    def test_binance_vence(self):
        fns = self._patch()
        with patch.object(gw, "_usdtbrl_bybit",
                          side_effect=AssertionError("não devia chamar")):
            r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "binance")
        self.assertAlmostEqual(r["rate"], 5.81)
        self.assertLess(abs(r["ts"] - time.time()), 5)
        for n in ("_usdtbrl_bybit", "_usdtbrl_bitget", "_usdtbrl_bitpreco"):
            self.assertNotIn(f"usdtbrl-{n.split('_')[-1]}", gw._SRC_RETRY)

    def test_binance_falha_bybit(self):
        self._patch(_usdtbrl_binance=Exception("HTTP 500"))
        r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "bybit")
        self.assertIn("usdtbrl-binance", gw._SRC_RETRY)

    def test_bybit_falha_bitget(self):
        self._patch(_usdtbrl_binance=Exception("morto"),
                    _usdtbrl_bybit=Exception("morto"))
        r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "bitget")

    def test_bitget_falha_bitpreco(self):
        self._patch(_usdtbrl_binance=Exception("morto"),
                    _usdtbrl_bybit=Exception("morto"),
                    _usdtbrl_bitget=Exception("morto"))
        r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "bitpreco")

    def test_todas_mortas(self):
        self._patch(_usdtbrl_binance=Exception("b"),
                    _usdtbrl_bybit=Exception("y"),
                    _usdtbrl_bitget=Exception("g"),
                    _usdtbrl_bitpreco=Exception("p"))
        with self.assertRaises(RuntimeError) as cm:
            gw.fetch_usdtbrl()
        msg = str(cm.exception)
        for name in ("binance", "bybit", "bitget", "bitpreco"):
            self.assertIn(name, msg)

    def test_cooldown_pula_sem_martelar(self):
        gw._src_cooldown("usdtbrl-binance", 300, "429")
        with patch.object(gw, "_usdtbrl_binance",
                          side_effect=AssertionError("não devia chamar")), \
             patch.object(gw, "_usdtbrl_bybit", return_value=5.83):
            r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "bybit")

    def test_429_falha_dupla(self):
        with patch.object(gw, "_usdtbrl_binance",
                          side_effect=Exception("HTTP Error 429")), \
             patch.object(gw, "_usdtbrl_bybit", return_value=5.83):
            gw.fetch_usdtbrl()
        self.assertGreaterEqual(gw._SRC_RETRY["usdtbrl-binance"][1], 2)

    def test_sucesso_limpa_cooldown(self):
        gw._SRC_RETRY["usdtbrl-binance"] = [0.0, 4]
        with patch.object(gw, "_usdtbrl_binance", return_value=5.81):
            r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "binance")
        self.assertNotIn("usdtbrl-binance", gw._SRC_RETRY)

    def test_rate_fora_faixa_cai(self):
        self._patch(_usdtbrl_binance=0.5)
        r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "bybit")
        self.assertIn("usdtbrl-binance", gw._SRC_RETRY)

    def test_rate_nan_cai(self):
        self._patch(_usdtbrl_binance=float("nan"))
        r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "bybit")

    def test_rate_none_cai(self):
        self._patch(_usdtbrl_binance=None)
        r = gw.fetch_usdtbrl()
        self.assertEqual(r["src"], "bybit")

    def test_nunca_usa_fiat(self):
        src = inspect.getsource(gw.fetch_usdtbrl)
        for proibido in ("awesomeapi", "USDBRL", "usdbrl", "bcb", "PTAX",
                         "olinda", "yahoo", "floatrates", "frankfurter"):
            self.assertNotIn(proibido.lower(), src.lower())
        for fn in (gw._usdtbrl_binance, gw._usdtbrl_bybit,
                   gw._usdtbrl_bitget, gw._usdtbrl_bitpreco):
            fs = inspect.getsource(fn).lower()
            for proibido in ("awesomeapi", "ptax", "olinda", "yahoo"):
                self.assertNotIn(proibido, fs)

    def test_ordem_correta(self):
        src = inspect.getsource(gw.fetch_usdtbrl)
        pos = [src.index(x) for x in
               ("usdtbrl-binance", "usdtbrl-bybit", "usdtbrl-bitget",
                "usdtbrl-bitpreco")]
        self.assertEqual(pos, sorted(pos))

    def test_fuzz_cadeia_1000(self):
        rnd = random.Random(7)
        outs = [5.81, "5.82", 0.5, 99.0, float("nan"), None,
                Exception("morto"), Exception("429"), 5.799]
        fns = ("_usdtbrl_binance", "_usdtbrl_bybit",
               "_usdtbrl_bitget", "_usdtbrl_bitpreco")
        for i in range(1000):
            gw._SRC_RETRY.clear()
            stack = []
            try:
                for name in fns:
                    val = rnd.choice(outs)
                    p = patch.object(gw, name,
                                     side_effect=val if isinstance(val, Exception)
                                     else (lambda v=val: v))
                    stack.append(p)
                    p.start()
                try:
                    r = gw.fetch_usdtbrl()
                except RuntimeError:
                    r = None
                if r is not None:
                    self.assertGreaterEqual(r["rate"], 1.0)
                    self.assertLessEqual(r["rate"], 20.0)
                    self.assertTrue(math.isfinite(r["rate"]))
                    self.assertIn(r["src"], ("binance", "bybit",
                                             "bitget", "bitpreco"))
            except Exception as e:
                self.fail(f"cadeia explodiu no caso {i}: {e}")
            finally:
                for p in stack:
                    p.stop()


# =============================== HISTÓRICO ================================
class TestHistorico(_Base):
    def _binance_rows(self, n=10, start="2026-08-01", base=5.8):
        return [[_ms(d), str(base), str(base + 0.1), str(base - 0.1),
                 str(base + i * 0.01), "100", 0]
                for i, d in enumerate(_days(n, start))]

    def test_ubrl_daily_ordena_dedupe_filtra(self):
        d = _days(3)
        rows = [[_ms(d[1]), 0, 0, 0, 5.80, 0],
                [_ms(d[0]), 0, 0, 0, 5.70, 0],
                [_ms(d[1]), 0, 0, 0, 5.85, 0],       # mesmo dia: vence
                [_ms(d[2]), 0, 0, 0, 99.0, 0],       # fora de faixa: fora
                [_ms(d[2]), 0, 0, 0, 5.90, 0]]
        out = gw._ubrl_daily(rows)
        self.assertEqual([dt for dt, _ in out],
                         [d[0].strftime("%Y-%m-%d"),
                          d[1].strftime("%Y-%m-%d"),
                          d[2].strftime("%Y-%m-%d")])
        self.assertEqual(out[1][1], 5.85)
        self.assertEqual(out[2][1], 5.90)

    def test_ubrl_daily_lixo(self):
        rows = [None, [], ["x"], [float("nan"), 0, 0, 0, 5.8],
                [_ms(_days(1)[0]), 0, 0, 0, "x"],
                [_ms(_days(1)[0]), 0, 0, 0, -5],
                [_ms(_days(1)[0]), 0, 0, 0, 5.8]]
        out = gw._ubrl_daily(rows)
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out[0][1], 5.8)

    def test_binance_serie(self):
        rows = self._binance_rows(10)
        with patch.object(gw, "_get_json", return_value=rows):
            pts, src = gw._hist_usdtbrl_binance(7)
        self.assertEqual(len(pts), 7)
        self.assertIn("Binance", src)
        self.assertEqual(pts[-1][0],
                         _days(10)[-1].strftime("%Y-%m-%d"))

    def test_binance_poucos_pontos(self):
        with patch.object(gw, "_get_json", return_value=[]):
            with self.assertRaises(ValueError):
                gw._hist_usdtbrl_binance(7)
        with patch.object(gw, "_get_json",
                          return_value=self._binance_rows(1)):
            with self.assertRaises(ValueError):
                gw._hist_usdtbrl_binance(7)

    def test_bybit_ordem_inversa(self):
        rows = [[_ms(d), "5.8", "5.9", "5.7", str(5.8 + i * 0.01), "1", "1"]
                for i, d in enumerate(_days(8))]
        rows.reverse()          # Bybit entrega do mais novo p/ o mais velho
        p = {"retCode": 0, "result": {"symbol": "USDTBRL", "list": rows}}
        with patch.object(gw, "_get_json", return_value=p):
            pts, src = gw._hist_usdtbrl_bybit(7)
        self.assertEqual(len(pts), 7)
        self.assertEqual(pts, sorted(pts))
        self.assertIn("Bybit", src)

    def test_bybit_erros(self):
        with patch.object(gw, "_get_json",
                          return_value={"retCode": 1, "retMsg": "erro"}):
            with self.assertRaises(ValueError):
                gw._hist_usdtbrl_bybit(7)
        p = {"retCode": 0, "result": {"symbol": "BTCBRL",
                                      "list": self._binance_rows(3)}}
        with patch.object(gw, "_get_json", return_value=p):
            with self.assertRaises(ValueError):
                gw._hist_usdtbrl_bybit(7)

    def test_coingecko(self):
        prices = [[_ms(d), 5.7 + i * 0.01] for i, d in enumerate(_days(12))]
        with patch.object(gw, "_get_json", return_value={"prices": prices}):
            pts, src = gw._hist_usdtbrl_coingecko(7)
        self.assertEqual(len(pts), 7)
        self.assertIn("CoinGecko", src)
        self.assertEqual(pts, sorted(pts))

    def test_coingecko_erros(self):
        for p in ({}, {"prices": []}, {"prices": [[_ms(_days(1)[0]), 5.8]]}):
            with self.subTest(p=p):
                with patch.object(gw, "_get_json", return_value=p):
                    with self.assertRaises(ValueError):
                        gw._hist_usdtbrl_coingecko(7)

    def test_bitget(self):
        data = [[_ms(d), "5.8", "5.9", "5.7", str(5.8 + i * 0.01),
                 "1", "1"] for i, d in enumerate(_days(10))]
        with patch.object(gw, "_get_json",
                          return_value={"code": "00000", "data": data}):
            pts, src = gw._hist_usdtbrl_bitget(7)
        self.assertEqual(len(pts), 7)
        self.assertIn("Bitget", src)
        with patch.object(gw, "_get_json",
                          return_value={"code": "1", "msg": "erro"}):
            with self.assertRaises(ValueError):
                gw._hist_usdtbrl_bitget(7)

    def test_cadeia_historico(self):
        rows = self._binance_rows(10)
        # Binance ok
        with patch.object(gw, "_get_json", return_value=rows):
            pts, src = gw._hist_usdtbrl(7)
        self.assertIn("Binance", src)
        # Binance -> Bybit
        bybit = {"retCode": 0, "result": {"symbol": "USDTBRL",
                 "list": list(reversed([[_ms(d), "5.8", "5.9", "5.7",
                                         "5.81", "1", "1"]
                                        for d in _days(8)]))}}
        fake = _json_router({"binance": Exception("morto"),
                             "bybit": bybit})
        with patch.object(gw, "_get_json", side_effect=fake):
            pts, src = gw._hist_usdtbrl(7)
        self.assertIn("Bybit", src)
        # Binance+Bybit -> CoinGecko
        cg = {"prices": [[_ms(d), 5.8] for d in _days(10)]}
        fake = _json_router({"binance": Exception("morto"),
                             "bybit": Exception("morto"),
                             "coingecko": cg})
        with patch.object(gw, "_get_json", side_effect=fake):
            pts, src = gw._hist_usdtbrl(7)
        self.assertIn("CoinGecko", src)
        # Binance+Bybit+CoinGecko -> Bitget
        bg = {"code": "00000", "data": [[_ms(d), "5.8", "5.9", "5.7",
                                         "5.81", "1", "1"] for d in _days(10)]}
        fake = _json_router({"binance": Exception("morto"),
                             "bybit": Exception("morto"),
                             "coingecko": Exception("morto"),
                             "bitget": bg})
        with patch.object(gw, "_get_json", side_effect=fake):
            pts, src = gw._hist_usdtbrl(7)
        self.assertIn("Bitget", src)

    def test_cadeia_historico_toda_morta(self):
        with patch.object(gw, "_get_json", side_effect=Exception("morto")):
            with self.assertRaises(RuntimeError) as cm:
                gw._hist_usdtbrl(7)
        self.assertIn("USDT/BRL", str(cm.exception))

    def test_limites_de_candles(self):
        fake = _json_router({"binance": Exception("morto"),
                             "bybit": Exception("morto"),
                             "coingecko": Exception("morto"),
                             "bitget": {"code": "00000", "data": []}})
        with patch.object(gw, "_get_json", side_effect=fake):
            with self.assertRaises(RuntimeError):
                gw._hist_usdtbrl(365)
        urls = fake.calls
        bitget_url = [u for u in urls if "bitget" in u][0]
        self.assertIn("limit=300", bitget_url)

    def test_rota_fetch_history(self):
        pts = [("2026-08-01", 5.8), ("2026-08-02", 5.9)]
        with patch.object(gw, "_hist_usdtbrl", return_value=(pts, "Binance")):
            res = gw.fetch_history("usdtbrl", 7, {})
        self.assertEqual(res["points"], pts)
        self.assertIn("Binance", res["src"])

    def test_hist_meta(self):
        meta = gw.HIST_META["usdtbrl"]
        self.assertIn("USDT/BRL", meta["title"])
        self.assertIn(365, meta["ranges"])
        self.assertIn("R$", meta["fmt"](5.8123))

    def test_morto_cai_no_log_local(self):
        now = time.time()
        log = {"usdtbrl": [[now - 86400 * (10 - i), 5.8 + i * 0.001]
                           for i in range(10)]}
        with patch.object(gw, "_hist_usdtbrl",
                          side_effect=RuntimeError("morto")):
            res = gw.fetch_history("usdtbrl", 30, log)
        self.assertIn("cache local", res["src"])
        self.assertGreaterEqual(len(res["points"]), 2)

    def test_janela_7d_prefere_log(self):
        now = time.time()
        log = {"usdtbrl": [[now - 86400 * (5 - i), 5.8 + i * 0.01]
                           for i in range(5)]}
        with patch.object(gw, "_hist_usdtbrl",
                          side_effect=AssertionError("não devia chamar")):
            res = gw.fetch_history("usdtbrl", 7, log)
        self.assertIn("cache diário", res["src"])

    def test_fuzz_ubrl_daily_3000(self):
        rnd = random.Random(99)
        pool = [None, "", "x", 0, -1, 0.5, 1.0, 20.0, 20.1, 5.8,
                float("nan"), float("inf"), 1e18]
        for i in range(3000):
            rows = []
            for _ in range(rnd.randint(0, 6)):
                r = rnd.random()
                if r < 0.2:
                    rows.append(rnd.choice(pool))
                else:
                    rows.append([rnd.choice([_ms(_days(1)[0]),
                                             rnd.uniform(-1e12, 1e12),
                                             "x"]),
                                 "o", "h", "l", rnd.choice(pool)])
            try:
                out = gw._ubrl_daily(rows)
            except Exception as e:
                self.fail(f"_ubrl_daily explodiu no caso {i}: {e}")
            self.assertIsInstance(out, list)
            dates = [d for d, _ in out]
            self.assertEqual(dates, sorted(set(dates)))
            for _, v in out:
                self.assertGreaterEqual(v, 1.0)
                self.assertLessEqual(v, 20.0)


# ============================ RENDER / CACHE ==============================
class TestRenderCache(_Base):
    def _w(self, last):
        w = gw.GoldWidget.__new__(gw.GoldWidget)
        w.last = last
        w.l_usdtbrl = MagicMock()
        return w

    def test_valor(self):
        w = self._w({"usdtbrl": {"rate": 5.8123, "ts": time.time(),
                                 "src": "binance"}})
        w._render_usdtbrl()
        w.l_usdtbrl.config.assert_called_with(text="1 USDT = R$ 5,8123")

    def test_velho(self):
        w = self._w({"usdtbrl": {"rate": 5.8,
                                 "ts": time.time() - gw.USDTBRL_MAX_AGE - 5}})
        w._render_usdtbrl()
        w.l_usdtbrl.config.assert_called_with(text="—")

    def test_sem_key(self):
        w = self._w({})
        w._render_usdtbrl()
        w.l_usdtbrl.config.assert_called_with(text="—")

    def test_rate_lixo(self):
        w = self._w({"usdtbrl": {"rate": "x", "ts": time.time()}})
        w._render_usdtbrl()
        w.l_usdtbrl.config.assert_called_with(text="—")

    def test_ts_lixo(self):
        w = self._w({"usdtbrl": {"rate": 5.8, "ts": "ontem"}})
        w._render_usdtbrl()
        w.l_usdtbrl.config.assert_called_with(text="—")

    def test_cache_fiat_migrado(self):
        last = {"usdbrl": {"rate": 5.77, "ts": time.time()},
                "usdtbrl": {"rate": 5.81, "ts": time.time()},
                "spot_usd": 4000}
        old = gw.migrate_visible_fx_cache(last)
        self.assertEqual(old["rate"], 5.77)
        self.assertNotIn("usdbrl", last)
        self.assertIn("usdtbrl", last)
        self.assertIn("spot_usd", last)

    def test_migracao_tolerante(self):
        for v in (None, {}, {"x": 1}, "lixo", 42):
            with self.subTest(v=v):
                try:
                    gw.migrate_visible_fx_cache(v)
                except Exception as e:
                    self.fail(f"migração explodiu com {v!r}: {e}")

    def test_fuzz_render_1000(self):
        rnd = random.Random(3)
        pool = [None, "x", "", 0, -1, 5.8, float("nan"), float("inf"),
                5.8123, time.time(), time.time() - 10 ** 6, "ontem"]
        for i in range(1000):
            w = self._w({"usdtbrl": {"rate": rnd.choice(pool),
                                     "ts": rnd.choice(pool)}})
            try:
                w._render_usdtbrl()
            except Exception as e:
                self.fail(f"render explodiu no caso {i}: {e}")
            w.l_usdtbrl.config.assert_called()


# ================================= LIVE ===================================
@unittest.skipUnless(LIVE, "só com --live (bate na rede real)")
class TestLive(unittest.TestCase):
    def test_live_providers(self):
        rates = {}
        for name, fn in (("binance", gw._usdtbrl_binance),
                         ("bybit", gw._usdtbrl_bybit),
                         ("bitget", gw._usdtbrl_bitget),
                         ("bitpreco", gw._usdtbrl_bitpreco)):
            with self.subTest(exchange=name):
                v = fn()
                self.assertTrue(1.0 <= v <= 20.0)
                rates[name] = v
                print(f"LIVE {name}: {v:.4f}")
        lo, hi = min(rates.values()), max(rates.values())
        self.assertLess(hi / lo, 1.10, f"spread entre exchanges > 10%: {rates}")

    def test_live_cadeia(self):
        gw._SRC_RETRY.clear()
        r = gw.fetch_usdtbrl()
        self.assertTrue(1.0 <= r["rate"] <= 20.0)
        self.assertIn(r["src"], ("binance", "bybit", "bitget", "bitpreco"))
        print(f"LIVE cadeia: {r['src']} {r['rate']:.4f}")

    def test_live_series(self):
        for name, fn in (("binance", gw._hist_usdtbrl_binance),
                         ("bybit", gw._hist_usdtbrl_bybit),
                         ("coingecko", gw._hist_usdtbrl_coingecko),
                         ("bitget", gw._hist_usdtbrl_bitget)):
            with self.subTest(fonte=name):
                pts, src = fn(90)
                self.assertGreaterEqual(len(pts), 30)
                self.assertEqual([d for d, _ in pts], sorted(d for d, _ in pts))
                print(f"LIVE hist {name}: {len(pts)} pts ({src})")

    def test_live_serie_1a(self):
        pts, src = gw._hist_usdtbrl_binance(365)
        self.assertGreaterEqual(len(pts), 300)
        print(f"LIVE 1A: {len(pts)} pts via {src}")

    def test_live_fetch_history(self):
        res = gw.fetch_history("usdtbrl", 30, {})
        self.assertGreaterEqual(len(res["points"]), 10)
        print(f"LIVE fetch_history: {len(res['points'])} pts ({res['src']})")


if __name__ == "__main__":
    args = [a for a in sys.argv if a != "--live"]
    unittest.main(argv=args, verbosity=2)
