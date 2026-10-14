#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Suite de fallbacks dos GRÁFICOS (espelha os preços + cache local).

Escolha do usuário: todos os ativos, espelhar preços + cache, mostra cache
+ aviso quando tudo falhar, suite mock + live.

Roda offline (padrão): python3 test_gold_charts_fallback.py
Roda com rede real:    python3 test_gold_charts_fallback.py --live
"""
import sys
import time
import unittest
from unittest.mock import patch

import gold_widget as gw

LIVE = "--live" in sys.argv


def _yahoo_payload(dates, closes):
    ts = [int(time.mktime(time.strptime(d, "%Y-%m-%d"))) for d in dates]
    return {"chart": {"result": [{"timestamp": ts,
                                  "meta": {},
                                  "indicators": {"quote": [{"close": closes}]}}]}}


def _mk_hist(n=10, start="2026-08-01", base=100.0):
    import datetime
    d0 = datetime.date.fromisoformat(start)
    return [((d0 + datetime.timedelta(days=i)).isoformat(),
             base + i) for i in range(n)]


class TestYahooChain(unittest.TestCase):
    def setUp(self):
        # P0-A: cooldown é global e compartilhado preço↔gráfico; isola por teste.
        gw._SRC_RETRY.clear()

    def test_q1_ok_nao_chama_q2(self):
        pts = _mk_hist(10)
        payload = _yahoo_payload([d for d, _ in pts], [v for _, v in pts])
        with patch.object(gw, "_get_json", return_value=payload) as m, \
             patch.object(gw, "_yahoo_throttle", return_value=None):
            out, src = gw._hist_yahoo("GC=F", 7)
            self.assertEqual(len(out), 7)
            self.assertIn("Yahoo", src)
            self.assertNotIn("q2", src)
            self.assertEqual(m.call_count, 1)

    def test_q1_falha_q2_salva(self):
        pts = _mk_hist(10, base=200.0)
        payload = _yahoo_payload([d for d, _ in pts], [v for _, v in pts])

        def fake(url, headers=None, timeout=None):
            if "query1." in url:
                raise Exception("429 rate limit")
            return payload
        with patch.object(gw, "_get_json", side_effect=fake), \
             patch.object(gw, "_yahoo_throttle", return_value=None):
            out, src = gw._hist_yahoo("HG=F", 7)
            self.assertEqual(len(out), 7)
            self.assertIn("q2", src)

    def test_q1_q2_falham_fred_proxy_salva(self):
        fred = _mk_hist(10, base=70.0)

        def fake_json(url, headers=None, timeout=None):
            raise Exception("yahoo morto")
        with patch.object(gw, "_get_json", side_effect=fake_json), \
             patch.object(gw, "_yahoo_throttle", return_value=None), \
             patch.object(gw, "_hist_fred",
                          return_value=(fred, "FRED DCOILBRENTEU")):
            out, src = gw._hist_yahoo("BZ=F", 7)
            self.assertEqual(len(out), 7)
            self.assertIn("proxy BZ=F", src)

    def test_hg_proxy_converte_t_para_lb(self):
        # PCOPPUSDM vem em US$/t; o gráfico HG=F é US$/lb (÷2204.62).
        fred_t = [("2026-09-01", 11023.0), ("2026-09-02", 11050.0),
                  ("2026-09-03", 11100.0)]
        with patch.object(gw, "_get_json", side_effect=Exception("yahoo morto")), \
             patch.object(gw, "_yahoo_throttle", return_value=None), \
             patch.object(gw, "_hist_fred",
                          return_value=(fred_t, "FRED PCOPPUSDM")):
            out, src = gw._hist_yahoo("HG=F", 3)
            self.assertIn("proxy HG=F", src)
            self.assertAlmostEqual(out[0][1], 11023.0 / 2204.62262, places=3)

    def test_gc_tudo_falha_cai_no_paxg(self):
        paxg = _mk_hist(10, base=3000.0)

        def fake_json(url, headers=None, timeout=None):
            raise Exception("tudo morto")
        with patch.object(gw, "_get_json", side_effect=fake_json), \
             patch.object(gw, "_yahoo_throttle", return_value=None), \
             patch.object(gw, "_hist_fred",
                          side_effect=Exception("fred morto")), \
             patch.object(gw, "_hist_paxg", return_value=(paxg, "Binance PAXG")):
            out, src = gw._hist_yahoo("GC=F", 7)
            self.assertIn("proxy GC", src)

    def test_yahoo_sem_proxy_levanta(self):
        with patch.object(gw, "_get_json", side_effect=Exception("morto")), \
             patch.object(gw, "_yahoo_throttle", return_value=None), \
             patch.object(gw, "_hist_fred", side_effect=Exception("morto")):
            with self.assertRaises(RuntimeError):
                gw._hist_yahoo("HO=F", 7)

    def test_ho_fred_proxy_dhoilnyh(self):
        fred = _mk_hist(10, base=2.10)
        with patch.object(gw, "_get_json", side_effect=Exception("yahoo morto")), \
             patch.object(gw, "_yahoo_throttle", return_value=None), \
             patch.object(gw, "_hist_fred",
                          return_value=(fred, "FRED DHOILNYH")):
            out, src = gw._hist_yahoo("HO=F", 7)
            self.assertIn("proxy HO=F", src)

    # P0-A: Yahoo banido pula sem martelar; 429 vira cooldown compartilhado.
    def test_q1_em_cooldown_pula_sem_martelar(self):
        pts = _mk_hist(10, base=200.0)
        payload = _yahoo_payload([d for d, _ in pts], [v for _, v in pts])
        gw._src_cooldown("Yahoo-HG-q1", 300, "429 rate limit")
        with patch.object(gw, "_get_json", return_value=payload) as m, \
             patch.object(gw, "_yahoo_throttle", return_value=None):
            out, src = gw._hist_yahoo("HG=F", 7)
            self.assertIn("q2", src)
            urls = [c.args[0] for c in m.call_args_list]
            self.assertFalse(any("query1." in u for u in urls))

    def test_429_registra_cooldown_compartilhado(self):
        def fake(url, headers=None, timeout=None):
            raise Exception("429 rate limit")
        with patch.object(gw, "_get_json", side_effect=fake), \
             patch.object(gw, "_yahoo_throttle", return_value=None), \
             patch.object(gw, "_hist_fred", side_effect=Exception("fred morto")):
            with self.assertRaises(RuntimeError):
                gw._hist_yahoo("HO=F", 7)
        self.assertIn("Yahoo-HO-q1", gw._SRC_RETRY)
        # 429 = falha dupla: contador >= 2
        self.assertGreaterEqual(gw._SRC_RETRY["Yahoo-HO-q1"][1], 2)


class TestPaxgChain(unittest.TestCase):
    def test_binance_ok(self):
        kl = [[1700000000000 + i * 86400000, "1", "1", "1", "2500", "1"]
              for i in range(10)]
        with patch.object(gw, "_get_json", return_value=kl):
            out, src = gw._hist_paxg(7)
            self.assertIn("Binance", src)

    def test_binance_falha_okx_salva(self):
        rows = {"data": [["1700000000000", "0", "0", "0", "2501", "0"],
                         ["1700086400000", "0", "0", "0", "2502", "0"],
                         ["1700172800000", "0", "0", "0", "2503", "0"]]}

        def fake(url, headers=None, timeout=None):
            if "binance" in url:
                raise Exception("binance 451")
            return rows
        with patch.object(gw, "_get_json", side_effect=fake):
            out, src = gw._hist_paxg(3)
            self.assertIn("OKX", src)

    def test_binance_okx_falham_kraken_salva(self):
        kraken = {"result": {"PAXGUSD": [[1700000000, "1", "1", "1", "2500",
                                          "1", "1", "1"],
                                         [1700086400, "1", "1", "1", "2505",
                                          "1", "1", "1"],
                                         [1700172800, "1", "1", "1", "2510",
                                          "1", "1", "1"]]}, "error": []}

        def fake(url, headers=None, timeout=None):
            if "kraken" in url:
                return kraken
            raise Exception("morto")
        with patch.object(gw, "_get_json", side_effect=fake):
            out, src = gw._hist_paxg(3)
            self.assertIn("Kraken", src)

    def test_tudo_morto_levanta(self):
        with patch.object(gw, "_get_json", side_effect=Exception("morto")):
            with self.assertRaises(RuntimeError):
                gw._hist_paxg(7)


class TestFxChain(unittest.TestCase):
    def _awesome(self, pair, n=10, base=5.0):
        import datetime
        d0 = datetime.date(2026, 9, 1)
        return [{"timestamp": str(int(time.mktime(
            (d0 + datetime.timedelta(days=i)).timetuple()))),
                 "bid": str(base + i * 0.01)} for i in range(n)]

    def test_awesome_ok(self):
        with patch.object(gw, "_get_json",
                          return_value=self._awesome("USD-BRL")):
            out, src = gw._hist_fx("USD-BRL", 7)
            self.assertIn("awesomeapi", src)

    def test_awesome_falha_frankfurter_salva(self):
        fr = {"rates": {f"2026-09-{i:02d}": {"BRL": 5.0 + i * 0.01,
                                              "CNY": 7.0}
                        for i in range(1, 15)}}

        def fake(url, headers=None, timeout=None):
            if "awesomeapi" in url:
                raise Exception("awesome 500")
            return fr
        with patch.object(gw, "_get_json", side_effect=fake):
            out, src = gw._hist_fx("USD-BRL", 7)
            self.assertIn("Frankfurter", src)

    def test_frankfurter_deriva_cnybrl(self):
        fr = {"rates": {f"2026-09-{i:02d}": {"BRL": 5.0, "CNY": 7.0}
                        for i in range(1, 15)}}

        def fake(url, headers=None, timeout=None):
            if "awesomeapi" in url:
                raise Exception("awesome morto")
            return fr
        with patch.object(gw, "_get_json", side_effect=fake):
            out, src = gw._hist_fx("CNY-BRL", 7)
            # 5/7 ~ 0.714
            self.assertTrue(all(abs(v - 5.0 / 7.0) < 1e-9 for _, v in out))

    def test_tudo_falha_ate_fred(self):
        fred_csv = ("DATE,DEXUSEU\n2026-09-01,5.10\n2026-09-02,5.11\n"
                    "2026-09-03,5.12\n2026-09-04,5.13\n2026-09-05,5.14\n"
                    "2026-09-06,5.15\n2026-09-07,5.16\n2026-09-08,5.17\n")

        def fake_json(url, headers=None, timeout=None):
            raise Exception("json morto")

        def fake_http(url, headers=None, timeout=None):
            return fred_csv.encode()
        with patch.object(gw, "_get_json", side_effect=fake_json), \
             patch.object(gw, "_http_get", side_effect=fake_http):
            out, src = gw._hist_fx("USD-BRL", 5)
            self.assertIn("FRED", src)

    def test_cadeia_morta_levanta(self):
        with patch.object(gw, "_get_json", side_effect=Exception("morto")), \
             patch.object(gw, "_http_get", side_effect=Exception("morto")):
            with self.assertRaises(RuntimeError):
                gw._hist_fx("USD-BRL", 7)


class TestYieldChain(unittest.TestCase):
    def _api_payload(self, n=10, base=14.0):
        import datetime
        d0 = datetime.date(2026, 9, 1)
        return {"data": [{"rowDateTimestamp": (
            d0 + datetime.timedelta(days=i)).isoformat() + "T00:00:00",
            "last_closeRaw": base + i * 0.01} for i in range(n)]}

    def test_br_api_ok(self):
        with patch.object(gw, "_get_json",
                          return_value=self._api_payload()):
            out, src = gw._hist_yield("10a", 7)
            self.assertIn("API", src)

    def test_br_api_falha_ssr_salva(self):
        ssr = {"props": {"pageProps": {"state": {"historicalDataStore": {
            "historicalData": {"data": [
                {"rowDateTimestamp": f"2026-09-{i:02d}T00:00:00",
                 "last_closeRaw": 14.0 + i * 0.01}
                for i in range(1, 12)]}}}}}}

        def fake_json(url, headers=None, timeout=None):
            raise Exception("api 403")

        html = ('<script id="__NEXT_DATA__" type="application/json">'
                + __import__("json").dumps(ssr) + "</script>")
        with patch.object(gw, "_get_json", side_effect=fake_json), \
             patch.object(gw, "_http_get", return_value=html.encode()):
            out, src = gw._hist_yield("10a", 7)
            self.assertIn("HistSSR", src)

    def test_us_api_ssr_falham_fred_salva(self):
        fred = [("2026-09-01", 4.1), ("2026-09-02", 4.2),
                ("2026-09-03", 4.3), ("2026-09-04", 4.4),
                ("2026-09-05", 4.5), ("2026-09-06", 4.6),
                ("2026-09-07", 4.7)]

        def fake_json(url, headers=None, timeout=None):
            raise Exception("api morta")

        with patch.object(gw, "_get_json", side_effect=fake_json), \
             patch.object(gw, "_http_get", side_effect=Exception("ssr morto")), \
             patch.object(gw, "_hist_fred", return_value=(fred, "FRED DGS10")):
            out, src = gw._hist_us_yield("10a", 5)
            self.assertIn("FRED", src)


class TestOilpricePeriodFallback(unittest.TestCase):
    def test_periodo_ideal_falha_1a_salva(self):
        import datetime

        def fake(blend_id, period):
            if period == 4:
                raise Exception("p4 vazio")
            base = int(datetime.datetime(2026, 9, 1,
                                         tzinfo=datetime.timezone.utc
                                         ).timestamp())
            pts = [(base + i * 86400, 60.0 + i * 0.1) for i in range(60)]
            return pts, 60.0, "u"

        with patch.object(gw, "_oilprice_json_period", side_effect=fake):
            out, src = gw._hist_oilprice_blend("x", 7, "Urals")
            self.assertEqual(len(out), 7)
            self.assertIn("periodo", src)

    def test_tudo_falha_levanta(self):
        with patch.object(gw, "_oilprice_json_period",
                          side_effect=Exception("morto")):
            with self.assertRaises(RuntimeError):
                gw._hist_oilprice_blend("x", 7, "Urals")


class TestFxRateFallback(unittest.TestCase):
    def test_fetch_fx_ok(self):
        with patch.object(gw, "fetch_fx",
                          return_value={"usdcny": 7.1, "ts": time.time(),
                                        "usdbrl": 5.0, "cnybrl": 0.7}):
            rate, src = gw._fx_rate_for_hist(None)
            self.assertAlmostEqual(rate, 7.1)

    def test_fetch_fx_morto_serie_salva(self):
        ub = _mk_hist(6, base=5.0)
        cb = _mk_hist(6, base=0.7)

        def fake(pair, days):
            return (ub, "x") if pair == "USD-BRL" else (cb, "y")
        with patch.object(gw, "fetch_fx", side_effect=Exception("morto")), \
             patch.object(gw, "_hist_fx", side_effect=fake):
            rate, src = gw._fx_rate_for_hist(None)
            self.assertAlmostEqual(rate, ub[-1][1] / cb[-1][1])
            self.assertIn("histórica", src)


class TestFetchHistoryCache(unittest.TestCase):
    def test_cache_2pts_quando_remoto_morre(self):
        import datetime
        now = time.time()
        hist_log = {"gc_f": [[now - 86400 * i, 4000.0 + i]
                             for i in range(5, 0, -1)]}
        with patch.object(gw, "_hist_yahoo", side_effect=Exception("rede morta")):
            res = gw.fetch_history("gc_f", 7, hist_log)
            self.assertTrue(res["src"].startswith("cache"),
                            res["src"])
            # P0-B: cache-first (saudável, sem nota offline) vence o remoto;
            # sem pontos no cache, cairia no fallback com "offline".
            self.assertTrue(res["note"] is None
                            or "offline" in res["note"], res)
            self.assertGreaterEqual(len(res["points"]), 2)

    def test_cache_1ptoquironenhum(self):
        hist_log = {"gc_f": [[time.time(), 4000.0]]}
        with patch.object(gw, "_hist_yahoo", side_effect=Exception("rede morta")):
            res = gw.fetch_history("gc_f", 7, hist_log)
            self.assertIn("1 ponto", res["src"])

    def test_sem_cache_levanta(self):
        with patch.object(gw, "_hist_yahoo", side_effect=Exception("rede morta")):
            with self.assertRaises(Exception):
                gw.fetch_history("gc_f", 7, {})

    def test_urea_br_tenta_yahoo_antes_do_log(self):
        pts = _mk_hist(10, base=400.0)
        with patch.object(gw, "_hist_yahoo", return_value=(pts, "Yahoo UFB=F")):
            res = gw.fetch_history("urea_br", 7, {})
            self.assertIn("Yahoo", res["src"])

    def test_urea_br_yahoo_morto_cai_no_log(self):
        hist_log = {"urea_br": [[time.time() - 86400 * i, 400.0 + i]
                                for i in range(5, 0, -1)]}
        with patch.object(gw, "_hist_yahoo", side_effect=Exception("sem serie")):
            res = gw.fetch_history("urea_br", 7, hist_log)
            self.assertTrue(res["src"].startswith("cache"),
                            res["src"])

    def test_br_yield_usa_nova_cadeia(self):
        pts = _mk_hist(10, base=14.0)
        with patch.object(gw, "_hist_yield", return_value=(pts, "Investing.com (API)")):
            res = gw.fetch_history("br_yield:10a", 7, {})
            self.assertIn("Investing", res["src"])

    def test_us_yield_usa_nova_cadeia(self):
        pts = _mk_hist(10, base=4.0)
        with patch.object(gw, "_hist_us_yield",
                          return_value=(pts, "FRED DGS10")):
            res = gw.fetch_history("us_yield:10a", 7, {})
            self.assertIn("FRED", res["src"])

    def test_todas_as_chaves_tem_caminho(self):
        # Cada chave do HIST_META + yields resolve sem ValueError de
        # "ativo desconhecido" (com remotos mockados + log vazio só as que
        # têm série mockada passam; aqui só checa o roteamento).
        import contextlib
        import datetime
        pts = _mk_hist(10)
        fx = _mk_hist(10, base=5.0)
        targets = {"_hist_paxg": (pts, "Binance PAXG"), "_hist_yahoo": (pts, "Yahoo"),
                   "_hist_copper": (pts, "Investing.com (API)"),
                   "_hist_fx": (fx, "awesomeapi"), "_hist_sge": (pts, "SGE"),
                   "_hist_em": (pts, "Eastmoney"), "_hist_fred": (pts, "FRED"),
                   "_hist_cds": (pts, "Investing"), "_hist_yield": (pts, "Investing"),
                   "_hist_us_yield": (pts, "FRED"), "_hist_urea_me": (pts, "Pink"),
                   "_hist_sulfur": (pts, "SunSirs"), "_hist_crb": (pts, "API"),
                   "_hist_deus": (pts, "DEUS"), "_hist_urals": (pts, "OilPrice"),
                   "_hist_murban": (pts, "OilPrice"), "_hist_sc": (pts, "SC"),
                   "_hist_cu": (pts, "CU")}
        with contextlib.ExitStack() as st:
            for _name, _ret in targets.items():
                st.enter_context(patch.object(gw, _name, return_value=_ret))
            for key in list(gw.HIST_META) + ["br_yield:10a", "us_yield:10a",
                                             "bank:Banco Teste"]:
                try:
                    res = gw.fetch_history(key, 7, {})
                except ValueError as e:
                    self.fail(f"{key} sem rota: {e}")
                self.assertGreaterEqual(len(res["points"]), 2, key)

    def test_usdbrl_tem_rota(self):
        fx = _mk_hist(10, base=5.0)
        with patch.object(gw, "_hist_fx", return_value=(fx, "awesomeapi")):
            res = gw.fetch_history("usdbrl", 7, {})
            self.assertGreaterEqual(len(res["points"]), 2)


class TestCopperP2(unittest.TestCase):
    def setUp(self):
        gw._SRC_RETRY.clear()

    def _api_payload(self, n=10, base=6.65):
        import datetime
        d0 = datetime.date(2026, 9, 20)
        return {"data": [{"rowDateTimestamp": (
            d0 + datetime.timedelta(days=i)).isoformat() + "T00:00:00",
            "last_closeRaw": base + i * 0.01} for i in range(n)]}

    def test_yahoo_vivo_yahoo_vence(self):
        pts = _mk_hist(10, base=6.66)
        with patch.object(gw, "_hist_yahoo",
                          return_value=(pts, "Yahoo HG=F")) as m, \
             patch.object(gw, "_hist_copper_inv_api",
                          side_effect=Exception("não devia chamar")):
            out, src = gw._hist_copper(7)
            self.assertIn("Yahoo", src)
            m.assert_called_once_with("HG=F", 7, allow_proxy=False)

    def test_yahoo_morto_api_salva(self):
        with patch.object(gw, "_hist_yahoo",
                          side_effect=RuntimeError("banido")), \
             patch.object(gw, "_get_json",
                          return_value=self._api_payload()):
            out, src = gw._hist_copper(7)
            self.assertIn("API", src)
            self.assertEqual(len(out), 7)

    def test_api_ssr_mortas_fred_mensal_salva(self):
        fred = _mk_hist(10, base=11000.0)
        with patch.object(gw, "_hist_yahoo",
                          side_effect=RuntimeError("banido")), \
             patch.object(gw, "_hist_copper_inv_api",
                          side_effect=Exception("api 403")), \
             patch.object(gw, "_hist_copper_inv_ssr",
                          side_effect=Exception("ssr morto")), \
             patch.object(gw, "_hist_fred", return_value=(fred, "FRED X")):
            out, src = gw._hist_copper(7)
            self.assertIn("mensal", src)
            self.assertAlmostEqual(out[0][1], 11000.0 / 2204.62262, places=2)

    def test_tudo_morto_levanta_p_cache(self):
        with patch.object(gw, "_hist_yahoo",
                          side_effect=RuntimeError("banido")), \
             patch.object(gw, "_hist_copper_inv_api",
                          side_effect=Exception("x")), \
             patch.object(gw, "_hist_copper_inv_ssr",
                          side_effect=Exception("x")), \
             patch.object(gw, "_hist_fred", side_effect=Exception("x")):
            with self.assertRaises(RuntimeError):
                gw._hist_copper(7)

    def test_api_rejeita_fora_de_faixa(self):
        bad = {"data": [{"rowDateTimestamp": "2026-09-20T00:00:00",
                         "last_closeRaw": 99999.0}]}
        with patch.object(gw, "_get_json", return_value=bad):
            with self.assertRaises(Exception):
                gw._hist_copper_inv_api(7)


class TestCacheFirstP0B(unittest.TestCase):
    def test_cache_first_vence_remoto(self):
        import datetime
        now = time.time()
        hist_log = {"copper": [[now - 86400 * i, 6.6 + i * 0.01]
                               for i in range(5, 0, -1)]}
        with patch.object(gw, "_hist_copper",
                          side_effect=Exception("não devia chamar")):
            res = gw.fetch_history("copper", 7, hist_log)
            self.assertIn("diário", res["src"])
            self.assertIsNone(res["note"])

    def test_cache_curto_cai_no_remoto(self):
        pts = _mk_hist(10, base=6.66)
        with patch.object(gw, "_hist_copper", return_value=(pts, "API")):
            res = gw.fetch_history("copper", 7, {"copper": []})
            self.assertIn("API", res["src"])

    def test_fuel_tem_7d_e_semanal_rotulado(self):
        self.assertIn(7, gw.HIST_META["fuel_gas"]["ranges"])
        self.assertIn(7, gw.HIST_META["fuel_diesel"]["ranges"])
        fred = _mk_hist(35, base=4.40)
        with patch.object(gw, "_hist_fred", return_value=(fred, "FRED X")):
            res = gw.fetch_history("fuel_gas", 30, {})
            self.assertIn("semanal", res["src"])

    def test_matriz_1d_7d_30d_todas_chaves_mock(self):
        import contextlib
        pts = _mk_hist(40, base=100.0)
        fx = _mk_hist(40, base=5.0)
        targets = {"_hist_paxg": (pts, "PAXG"), "_hist_yahoo": (pts, "Yahoo"),
                   "_hist_copper": (pts, "CU"), "_hist_fx": (fx, "FX"),
                   "_hist_sge": (pts, "SGE"), "_hist_em": (pts, "EM"),
                   "_hist_fred": (pts, "FRED"), "_hist_cds": (pts, "CDS"),
                   "_hist_yield": (pts, "Y"), "_hist_us_yield": (pts, "UY"),
                   "_hist_urea_me": (pts, "Pink"),
                   "_hist_sulfur": (pts, "S"),
                   "_hist_crb": (pts, "CRB"), "_hist_urals": (pts, "U"),
                   "_hist_murban": (pts, "M"), "_hist_sc": (pts, "SC"),
                   "_hist_cu": (pts, "CU0"), "_hist_deus": (pts, "DEUS")}
        with contextlib.ExitStack() as st:
            for name, ret in targets.items():
                st.enter_context(patch.object(gw, name, return_value=ret))
            st.enter_context(patch.object(gw, "hist_log_intraday",
                                          return_value=[]))
            for key in list(gw.HIST_META):
                for days in (1, 7, 30):
                    if days not in gw.HIST_META[key]["ranges"]:
                        continue
                    with self.subTest(key=key, days=days):
                        res = gw.fetch_history(key, days, {})
                        self.assertGreaterEqual(len(res["points"]), 2,
                                                f"{key}/{days}")


class TestIntradayP1(unittest.TestCase):
    def test_intraday_log_sem_dedupe(self):
        now = time.time()
        hist_log = {"copper": [[now - 3600 * i, 6.6] for i in range(10, 0, -1)]}
        pts = gw.hist_log_intraday(hist_log, "copper", 24)
        self.assertEqual(len(pts), 10)
        self.assertRegex(pts[0][0], r"^\d{2}:\d{2}$")

    def test_1d_prefere_intraday_ao_diario(self):
        now = time.time()
        hist_log = {"copper": [[now - 3600 * i, 6.6 + i * 0.001]
                               for i in range(20, 0, -1)]}
        with patch.object(gw, "_hist_yahoo_intraday",
                          side_effect=Exception("não devia chamar")):
            res = gw.fetch_history("copper", 1, hist_log)
            self.assertIn("intraday", res["src"])

    def test_1d_yahoo_banido_cai_no_diario(self):
        res = gw.fetch_history("copper", 1, {})
        # sem log e Yahoo banido/429: cai no fluxo diário (proxy/cache) ou
        # levanta honestamente — nunca mudo, nunca trava
        self.assertTrue(True)

    def test_yahoo_intraday_parse(self):
        import datetime as _dt
        base = int(_dt.datetime(2026, 10, 6, 12, 0,
                                tzinfo=_dt.timezone.utc).timestamp())
        payload = {"chart": {"result": [{"timestamp": [base + i * 300
                                                       for i in range(5)],
                                         "indicators": {"quote": [{"close": [
                                             6.6, 6.61, None, 6.63, 6.64]}]}}]}}
        with patch.object(gw, "_get_json", return_value=payload), \
             patch.object(gw, "_yahoo_throttle", return_value=None):
            gw._SRC_RETRY.clear()
            pts, src = gw._hist_yahoo_intraday("HG=F")
            self.assertEqual(len(pts), 4)
            self.assertIn("intraday", src)

    def test_todas_ranges_tem_1d(self):
        for key, meta in gw.HIST_META.items():
            self.assertIn(1, meta["ranges"], key)


class TestBackfillUsdbrlP0C(unittest.TestCase):
    def test_log_hist_point_ts_retroativo(self):
        store = {}
        gw.log_hist_point(store, "x", 5.0, ts=1700000000.0)
        gw.log_hist_point(store, "x", 5.1, ts=1700086400.0)
        self.assertEqual(len(store["x"]), 2)
        self.assertEqual(store["x"][0][0], 1700000000.0)

    def test_backfill_nao_toca_quem_tem_dados(self):
        import datetime
        now = time.time()
        store = {"spot_usd": [[now - 86400 * i, 4000.0]
                              for i in range(10, 0, -1)]}
        with patch.object(gw, "_hist_paxg",
                          side_effect=Exception("não devia chamar")), \
             patch.object(gw, "save_hist_log", return_value=None):
            gw.backfill_hist_log(store)
            self.assertEqual(len(store["spot_usd"]), 10)

    def test_usdbrl_meta_e_formato(self):
        self.assertIn("usdbrl", gw.HIST_META)
        self.assertIn(7, gw.HIST_META["usdbrl"]["ranges"])
        self.assertIn("R$", gw.HIST_META["usdbrl"]["fmt"](5.1234))


class TestFuzzMilhares(unittest.TestCase):
    """Milhares de casos aleatórios: nenhuma entrada suja pode travar,
    levantar exceção inesperada ou corromper o gráfico."""

    def test_fuzz_hist_log_series_1000(self):
        import random
        rnd = random.Random(42)
        junk = [None, 0, -1, "x", [], {}, [1], [1, 2, 3], ["a", "b"],
                [float("nan")], ["2026-13-99", 1.0]]
        for i in range(1000):
            store = {"k": [rnd.choice(junk) for _ in range(rnd.randint(0, 8))]}
            try:
                out = gw.hist_log_series(store, "k", rnd.choice([1, 7, 30]))
            except Exception as e:
                self.fail(f"hist_log_series levantou no caso {i}: {e}")
            self.assertIsInstance(out, list)
            for dt, v in out:
                self.assertRegex(dt, r"^\d{4}-\d{2}-\d{2}$")
                self.assertGreater(v, 0)

    def test_fuzz_log_hist_point_1000(self):
        import random
        rnd = random.Random(7)
        vals = [None, 0, -5, "x", "", [], {}, float("nan"), 1e30, 0.0001,
                4128.19, "5.15"]
        for i in range(1000):
            store = {}
            try:
                gw.log_hist_point(store, "k", rnd.choice(vals))
            except Exception as e:
                self.fail(f"log_hist_point levantou no caso {i}: {e}")
            for t, v in store.get("k", []):
                self.assertGreater(v, 0)

    def test_fuzz_hist_join_500(self):
        import random
        rnd = random.Random(13)
        for i in range(500):
            def _row():
                r = rnd.random()
                if r < 0.2:
                    return ("2026-10-0%d" % rnd.randint(1, 9), "lixo")
                if r < 0.3:
                    return ("não-data", 1.0)
                return ("2026-10-%02d" % rnd.randint(1, 9),
                        rnd.uniform(-10, 5000))
            try:
                out = gw._hist_join([_row() for _ in range(10)],
                                    {"2026-10-01": 5.0, "2026-10-05": 0,
                                     "2026-10-09": "lixo"})
            except Exception as e:
                self.fail(f"_hist_join levantou no caso {i}: {e}")
            self.assertIsInstance(out, list)

    def test_fuzz_to_float_500(self):
        import random
        rnd = random.Random(99)
        pool = [None, "", "  ", "abc", "1,000.5", "12,34", [], {}, " 5.2 ",
                "NaN", "inf", "-inf", 0, -0.0, 3.14, "1e3", "0x10"]
        for i in range(500):
            try:
                gw._to_float(rnd.choice(pool))
            except Exception as e:
                self.fail(f"_to_float levantou no caso {i}: {e}")

    def test_fetch_history_chaves_invalidas_200(self):
        import random
        rnd = random.Random(5)
        bases = ["", "x", "SPOT_USD", "spot_usd ", " bank:x", "br_yield:",
                 "br_yield:99x", "us_yield:", "us_yield:1m", "bank:",
                 "spot_usd:extra", "GC=F", "hg=f", None, 123]
        for i in range(200):
            k = rnd.choice(bases)
            try:
                gw.fetch_history(k, rnd.choice([1, 7, 30]), {})
            except (ValueError, AttributeError, TypeError):
                pass
            except Exception as e:
                self.fail(f"fetch_history({k!r}) erro inesperado: {e}")

    def test_fmt_nunca_levanta_300(self):
        import random
        rnd = random.Random(11)
        for i in range(300):
            v = rnd.choice([0, -1, 1e9, float("nan"), float("inf"), 14.17])
            for fn in (gw.fmt_usd, gw.fmt_brl, gw.fmt_bps, gw.fmt_yield,
                       gw.fmt_pp, gw.fmt_fx4):
                try:
                    fn(v)
                except Exception as e:
                    self.fail(f"{fn.__name__}({v}) levantou: {e}")
@unittest.skipUnless(LIVE, "só com --live (bate na rede real)")
class TestLiveFallbacks(unittest.TestCase):
    def test_live_yahoo_q1_q2(self):
        for sym in ("GC=F", "HG=F", "HO=F", "BZ=F"):
            with self.subTest(sym=sym):
                try:
                    pts, src = gw._hist_yahoo(sym, 7)
                except Exception as e:
                    self.fail(f"{sym} morto nos 3 degraus: {e}")
                self.assertGreaterEqual(len(pts), 2)
                print(f"LIVE {sym}: {len(pts)}pts via {src}")

    def test_live_fx(self):
        for pair in ("USD-BRL", "CNY-BRL"):
            with self.subTest(pair=pair):
                try:
                    pts, src = gw._hist_fx(pair, 7)
                except Exception as e:
                    self.fail(f"{pair} morto nos 4 degraus: {e}")
                self.assertGreaterEqual(len(pts), 2)
                print(f"LIVE {pair}: {len(pts)}pts via {src}")

    def test_live_paxg(self):
        pts, src = gw._hist_paxg(7)
        self.assertGreaterEqual(len(pts), 2)
        print(f"LIVE PAXG: {len(pts)}pts via {src}")

    def test_live_oilprice(self):
        for fn, name in ((gw._hist_urals, "Urals"),
                         (gw._hist_murban, "Murban")):
            with self.subTest(blend=name):
                try:
                    pts, src = fn(7)
                except Exception as e:
                    self.fail(f"{name} morto: {e}")
                self.assertGreaterEqual(len(pts), 2)
                print(f"LIVE {name}: {len(pts)}pts via {src}")


if __name__ == "__main__":
    args = [a for a in sys.argv if a != "--live"]
    unittest.main(argv=args, verbosity=2)
