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
            self.assertEqual(res["src"], "cache local")
            self.assertIn("offline", res["note"])
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
            self.assertEqual(res["src"], "cache local")

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
        import datetime
        pts = _mk_hist(10)
        fx = _mk_hist(10, base=5.0)
        with patch.object(gw, "_hist_paxg", return_value=(pts, "Binance PAXG")), \
             patch.object(gw, "_hist_yahoo", return_value=(pts, "Yahoo")), \
             patch.object(gw, "_hist_fx", return_value=(fx, "awesomeapi")), \
             patch.object(gw, "_hist_sge", return_value=(pts, "SGE")), \
             patch.object(gw, "_hist_em", return_value=(pts, "Eastmoney")), \
             patch.object(gw, "_hist_fred", return_value=(pts, "FRED")), \
             patch.object(gw, "_hist_cds", return_value=(pts, "Investing")), \
             patch.object(gw, "_hist_yield", return_value=(pts, "Investing")), \
             patch.object(gw, "_hist_us_yield", return_value=(pts, "FRED")), \
             patch.object(gw, "_hist_urea_me", return_value=(pts, "Pink")), \
             patch.object(gw, "_hist_sulfur",
                          return_value=(pts, "SunSirs")), \
             patch.object(gw, "_hist_crb", return_value=(pts, "API")), \
             patch.object(gw, "_hist_urals", return_value=(pts, "OilPrice")), \
             patch.object(gw, "_hist_murban", return_value=(pts, "OilPrice")), \
             patch.object(gw, "_hist_sc",
                          return_value=(pts, "SC")), \
             patch.object(gw, "_hist_cu",
                          return_value=(pts, "CU")):
            for key in list(gw.HIST_META) + ["br_yield:10a", "us_yield:10a",
                                             "bank:Banco Teste"]:
                try:
                    res = gw.fetch_history(key, 7, {})
                except ValueError as e:
                    self.fail(f"{key} sem rota: {e}")
                self.assertGreaterEqual(len(res["points"]), 2, key)


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
