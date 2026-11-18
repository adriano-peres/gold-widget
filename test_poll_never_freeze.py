#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bateria anti-travamento: manual nunca descartado + poll nunca morre. 200+ casos."""
import time, threading, unittest, contextlib
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import gold_widget as gw

def _today():
    return datetime.now(timezone.utc).date().isoformat()

def _mk_widget():
    w = gw.GoldWidget.__new__(gw.GoldWidget)
    w.last = {}
    w._hist_log = {}
    w.baseline = {"day": _today(), "paxg_open": 4000.0, "paxg_week_open": 3900.0,
                  "fx_day_pct": 0.5, "fx_week_pct": 1.0}
    w._poll_lock = threading.Lock()
    w._manual_pending = False
    w.root = MagicMock()
    def _after(ms, fn, *a):
        try:
            fn(*a)
        except Exception:
            pass
        return MagicMock()
    w.root.after.side_effect = _after
    w.stop = threading.Event()
    w._tray = MagicMock(); w._tray_ok = False
    w.spot_offline = False
    w.l_usd = MagicMock(); w.l_brl = MagicMock(); w.l_sub = MagicMock()
    w.l_usd_var = MagicMock(); w.l_usd_var_week = MagicMock()
    w.l_brl_var = MagicMock(); w.l_brl_var_week = MagicMock()
    w.l_usdtbrl = MagicMock()
    # mocks p/ _render não exigir sigs nem Tk real
    for m in ("_render_copper","_render_copper_sub","_render_us","_render_us_sub",
              "_render_cds","_render_cds_sub","_render_nvda","_render_nvda_sub",
              "_render_yield","_render_yield_sub",
              "_render_us_yield","_render_us_yield_sub","_render_ho","_render_ho_sub",
              "_render_brent","_render_brent_sub","_render_sc","_render_sc_sub",
              "_render_murban","_render_murban_sub","_render_urals","_render_urals_sub",
              "_render_urea","_render_urea_sub","_render_sulfur","_render_sulfur_sub",
              "_render_crb","_render_crb_sub","_render_deus","_render_deus_sub",
              "snap_corner","_tray_refresh_soon"):
        setattr(w, m, MagicMock())
    w._copper_sig = None; w._us_sig = None; w._cds_sig = None
    w._nvda_sig = None; w._nvda_refs = []
    w._user_moved = False; w._desktop_layer = False; w._below_applied = True
    w.canvas = MagicMock(); w.body = MagicMock(); w.frame = MagicMock()
    return w

def _poll_impl(w, usd, brl, fx, gorg_usd="raise", gorg_brl="raise"):
    w.last["fx"] = fx
    w._hist_log = {}
    def _tf(sym):
        return (usd, None) if sym == gw.SYMBOLS[0] else (brl, None)
    def _gorg(curr):
        if curr == "USD" and gorg_usd != "raise":
            return gorg_usd
        if curr == "BRL" and gorg_brl != "raise":
            return gorg_brl
        raise RuntimeError("gorg morto")
    with contextlib.ExitStack() as st:
        st.enter_context(patch.object(gw, "try_fetch", side_effect=_tf))
        st.enter_context(patch.object(gw, "collect_china", side_effect=lambda last: last.update({"fx": fx}) or None))
        mg = st.enter_context(patch.object(gw, "fetch_goldprice_org"))
        mg.side_effect = _gorg
        st.enter_context(patch.object(gw, "_due", return_value=False))
        st.enter_context(patch.object(gw, "save_cache"))
        st.enter_context(patch.object(gw, "save_hist_log", return_value=None))
        w._poll_once_impl()
    return w

class TestManual(unittest.TestCase):
    def test_01_livre(self):
        w = _mk_widget()
        with patch.object(w, "_poll_once_impl") as m:
            w._poll_now(); m.assert_called_once()
        self.assertFalse(w._poll_lock.locked())
    def test_02_ocupado_enfileira(self):
        w = _mk_widget(); w._poll_lock.acquire()
        try:
            with patch.object(w, "_poll_once_impl") as m, patch("gold_widget.log") as lg:
                w._poll_now(); m.assert_not_called()
                self.assertTrue(w._manual_pending); self.assertTrue(lg.called)
        finally: w._poll_lock.release()
    def test_03_ocupado_feedback(self):
        w = _mk_widget(); w._poll_lock.acquire()
        try: w._poll_now(); self.assertTrue(w.root.after.called)
        finally: w._poll_lock.release()
    def test_04_nao_solta_alheio(self):
        w = _mk_widget(); w._poll_lock.acquire()
        try: w._poll_now(); self.assertTrue(w._poll_lock.locked())
        finally: w._poll_lock.release()
    def test_05_explode_solta(self):
        w = _mk_widget()
        with patch.object(w, "_poll_once_impl", side_effect=RuntimeError("boom")), patch("gold_widget.log"):
            w._poll_now()
        self.assertFalse(w._poll_lock.locked())
    def test_06_thread_daemon(self):
        w = _mk_widget()
        with patch("gold_widget.threading.Thread") as th:
            w.update_now(); self.assertTrue(th.called)
    def test_07_poll_once_serializa(self):
        w = _mk_widget()
        with patch.object(w, "_poll_once_impl", return_value=None) as m:
            self.assertIsNone(w._poll_once()); m.assert_called_once()
    def test_08_loop_nunca_morre(self):
        w = _mk_widget(); c = {"n": 0}
        def _once():
            c["n"] += 1
            if c["n"] == 1: raise RuntimeError("boom")
            w.stop.set(); return None
        with patch.object(w, "_poll_once", side_effect=_once), patch("gold_widget.log"):
            w._poll_loop()
        self.assertGreaterEqual(c["n"], 2)

class TestSpot(unittest.TestCase):
    def test_20_ok(self):
        fx = {"usdbrl": 5.0, "ts": time.time()}
        w = _poll_impl(_mk_widget(), {"price": 3996.2, "bid": None, "ask": None}, {"price": 19893.0}, fx)
        self.assertEqual(w.last["usd_price"], 3996.2)
        self.assertTrue(time.time() - w.last["ts"] < 5)
    def test_21_repetido_atualiza(self):
        fx = {"usdbrl": 5.0, "ts": time.time()}
        w = _poll_impl(_mk_widget(), {"price": 4112.14, "bid": None, "ask": None}, {"price": 20662.0}, fx)
        self.assertIsNotNone(w.last["ts"])
    def test_22_gorg(self):
        fx = {"usdbrl": 5.0, "ts": time.time()}
        w = _poll_impl(_mk_widget(), None, None, fx, gorg_usd={"price": 3995.0}, gorg_brl={"price": 19900.0})
        self.assertEqual(w.last["usd_src"], "goldprice.org")
    def test_23_tudo_morto(self):
        w = _mk_widget()
        w.last = {"usd_price": 4112.14, "brl_price": 20662.0, "ts": time.time()-3600, "fx": {"usdbrl": 5.0, "ts": time.time()}}
        w._hist_log = {}
        with contextlib.ExitStack() as st:
            st.enter_context(patch.object(gw, "try_fetch", return_value=(None, None)))
            st.enter_context(patch.object(gw, "collect_china", side_effect=lambda last: None))
            st.enter_context(patch.object(gw, "fetch_goldprice_org", side_effect=RuntimeError("morto")))
            st.enter_context(patch.object(gw, "_due", return_value=False))
            st.enter_context(patch.object(gw, "save_cache"))
            st.enter_context(patch.object(gw, "save_hist_log", return_value=None))
            ts0 = w.last["ts"]; w._poll_once_impl()
            self.assertEqual(w.last["ts"], ts0)
    def test_24_derivado(self):
        fx = {"usdbrl": 5.4, "ts": time.time()}
        w = _poll_impl(_mk_widget(), {"price": 4000.0, "bid": 1, "ask": 1}, None, fx, gorg_brl={"price": 1.0})
        self.assertEqual(w.last["brl_src"], "derivado USDxBRL")
        self.assertAlmostEqual(w.last["brl_price"], 4000.0*5.4)
    def test_25_velho(self):
        fx = {"usdbrl": 5.4, "ts": time.time()-901}
        w = _poll_impl(_mk_widget(), {"price": 4000.0, "bid": 1, "ask": 1}, None, fx, gorg_brl={"price": 21600.0})
        self.assertEqual(w.last["brl_src"], "goldprice.org")
    def test_26_limite900(self):
        # margem p/ tempo de execução do poll (usa 890s, folga de 10s)
        fx = {"usdbrl": 5.4, "ts": time.time()-890}
        w = _poll_impl(_mk_widget(), {"price": 4000.0, "bid": 1, "ask": 1}, None, fx, gorg_brl={"price": 1.0})
        self.assertEqual(w.last["brl_src"], "derivado USDxBRL")
    def test_27_negativo(self):
        fx = {"usdbrl": -5.4, "ts": time.time()}
        w = _poll_impl(_mk_widget(), {"price": 4000.0, "bid": 1, "ask": 1}, None, fx, gorg_brl={"price": 21600.0})
        self.assertEqual(w.last["brl_src"], "goldprice.org")
    def test_28_string(self):
        self.assertTrue(gw._fx_fresh({"usdbrl": "5.4", "ts": time.time()}))
    def test_29_zero(self):
        fx = {"usdbrl": 5.0, "ts": time.time()}
        w = _poll_impl(_mk_widget(), {"price": 0, "bid": None, "ask": None}, {"price": 1.0}, fx, gorg_usd={"price": 3995.0})
        self.assertEqual(w.last["usd_src"], "goldprice.org")

class TestIsoladas(unittest.TestCase):
    def _base(self, fail_name):
        w = _mk_widget()
        w.last["fx"] = {"usdbrl": 5.0, "ts": time.time()}; w._hist_log = {}
        good = {"price": 1.0, "ts": time.time(), "usdcny_used": 6.5, "rate": 5.0, "bps": 120.0, "gas": 4.0, "value": 1.0}
        with contextlib.ExitStack() as st:
            st.enter_context(patch.object(gw, "try_fetch", side_effect=[({"price": 4000.0, "bid": 1, "ask": 1}, None), ({"price": 20000.0}, None)]))
            st.enter_context(patch.object(gw, "fetch_daily_baseline", return_value={"day": _today(), "paxg_open": 4000.0, "paxg_week_open": 3900.0, "fx_day_pct": 0.0, "fx_week_pct": 0.0}))
            st.enter_context(patch.object(gw, "collect_china", side_effect=lambda last: last.update({"fx": {"usdbrl": 5.0, "ts": time.time()}}) or None))
            for n in ("fetch_copper","fetch_cu_shfe","fetch_us_fuel","fetch_cds_br","fetch_ho_future","fetch_urals","fetch_brent","fetch_sc","fetch_murban","fetch_urea_me","fetch_urea_br","fetch_sulfur","fetch_crb","fetch_deus","fetch_usdtbrl"):
                if n == fail_name:
                    st.enter_context(patch.object(gw, n, side_effect=RuntimeError("morto")))
                else:
                    if n in ("fetch_cds_br",): st.enter_context(patch.object(gw, n, return_value={"bps": 1, "ts": time.time()}))
                    elif n in ("fetch_usdtbrl",): st.enter_context(patch.object(gw, n, return_value={"rate": 5, "ts": time.time()}))
                    elif n in ("fetch_us_fuel",): st.enter_context(patch.object(gw, n, return_value={"gas": 1, "diesel": 1, "ts": time.time()}))
                    elif n in ("fetch_deus",): st.enter_context(patch.object(gw, n, return_value={"value": 1, "ts": time.time()}))
                    else: st.enter_context(patch.object(gw, n, return_value={"price": 1, "ts": time.time(), "usdcny_used": 6.5}))
            if fail_name in ("fetch_yield_br", "fetch_us_yield"):
                if fail_name == "fetch_yield_br":
                    st.enter_context(patch.object(gw, "fetch_yield_br", side_effect=RuntimeError("morto")))
                    st.enter_context(patch.object(gw, "fetch_us_yield", return_value={}))
                else:
                    st.enter_context(patch.object(gw, "fetch_yield_br", return_value={}))
                    st.enter_context(patch.object(gw, "fetch_us_yield", side_effect=RuntimeError("morto")))
            else:
                st.enter_context(patch.object(gw, "fetch_yield_br", return_value={}))
                st.enter_context(patch.object(gw, "fetch_us_yield", return_value={}))
            sc = st.enter_context(patch.object(gw, "save_cache"))
            st.enter_context(patch.object(gw, "save_hist_log", return_value=None))
            # yield raise precisa de context separado pois patch acima com throw falha na criação; trata:
            w._poll_once_impl()
            self.assertEqual(w.last.get("usd_price"), 4000.0)
            self.assertTrue(sc.called)
for _fn in ["fetch_copper","fetch_cu_shfe","fetch_us_fuel","fetch_cds_br","fetch_ho_future","fetch_urals","fetch_brent","fetch_murban","fetch_crb","fetch_deus","fetch_usdtbrl","fetch_sulfur","fetch_urea_me","fetch_urea_br","fetch_yield_br","fetch_us_yield"]:
    def _mk(f=_fn):
        def _t(self): self._base(f)
        return _t
    setattr(TestIsoladas, f"test_iso_{_fn}", _mk())

class TestVar(unittest.TestCase):
    def _v(self, base):
        w = _mk_widget(); w.baseline = base
        w.last["fx"] = {"usdbrl": 5.0, "ts": time.time()}; w._hist_log = {}
        with contextlib.ExitStack() as st:
            st.enter_context(patch.object(gw, "try_fetch", side_effect=[({"price": 4000.0, "bid": 1, "ask": 1}, None), ({"price": 20000.0}, None)]))
            st.enter_context(patch.object(gw, "fetch_daily_baseline", return_value=base))
            st.enter_context(patch.object(gw, "collect_china", side_effect=lambda last: last.update({"fx": {"usdbrl": 5.0, "ts": time.time()}}) or None))
            st.enter_context(patch.object(gw, "_due", return_value=False))
            st.enter_context(patch.object(gw, "save_cache"))
            st.enter_context(patch.object(gw, "save_hist_log", return_value=None))
            w._poll_once_impl()
        return w
    def test_paxg_none(self):
        w = self._v({"day": _today(), "paxg_open": None, "paxg_week_open": 3900.0, "fx_day_pct": 0.0, "fx_week_pct": 0.0})
        self.assertEqual(w.last["usd_price"], 4000.0)
    def test_paxg_zero(self):
        w = self._v({"day": _today(), "paxg_open": 0, "paxg_week_open": 3900.0, "fx_day_pct": 0.0, "fx_week_pct": 0.0})
        self.assertEqual(w.last["usd_price"], 4000.0)
    def test_base_none(self):
        w = self._v(None); self.assertEqual(w.last["usd_price"], 4000.0)
    def test_base_ontem(self):
        from datetime import timedelta
        yd = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        w = self._v({"day": yd, "paxg_open": 4000.0, "paxg_week_open": 3900.0, "fx_day_pct": 0.0, "fx_week_pct": 0.0})
        self.assertNotIn("usd_day_pct", w.last)

class TestFx(unittest.TestCase):
    def test_fresh(self): self.assertTrue(gw._fx_fresh({"usdbrl": 5.0, "ts": time.time()}))
    def test_velho(self): self.assertFalse(gw._fx_fresh({"usdbrl": 5.0, "ts": time.time()-901}))
    def test_none(self): self.assertFalse(gw._fx_fresh(None))
    def test_neg(self): self.assertFalse(gw._fx_fresh({"usdbrl": -5.0, "ts": time.time()}))
    def test_zero(self): self.assertFalse(gw._fx_fresh({"usdbrl": 0, "ts": time.time()}))
    def test_ts_str(self): self.assertFalse(gw._fx_fresh({"usdbrl": 5.0, "ts": "ontem"}))
    def test_str_ok(self): self.assertTrue(gw._fx_fresh({"usdbrl": "5.4", "ts": time.time()}))
    def test_ok_limites(self):
        self.assertEqual(gw._ok_usdtbrl(1.0), 1.0); self.assertEqual(gw._ok_usdtbrl(20.0), 20.0)
        for bad in (0.99, 20.01, "x", None):
            with self.assertRaises(ValueError): gw._ok_usdtbrl(bad)

class TestRender(unittest.TestCase):
    def test_ts_str(self):
        w = _mk_widget(); w.last = {"usd_price": 4000.0, "brl_price": 20000.0, "ts": "ontem", "usd_src": "goldprice.dev"}; w.spot_offline = True; w._render()
    def test_usdtbrl_corr(self):
        w = _mk_widget(); w.last = {"usd_price": 4000.0, "brl_price": 20000.0, "ts": time.time(), "usdtbrl": {"rate": "x", "ts": None}}; w._render_usdtbrl()
    def test_pct_str(self):
        w = _mk_widget(); w.last = {"usd_price": 4000.0, "brl_price": 20000.0, "ts": time.time(), "usd_day_pct": "x"}; w._render()

class TestFuzz(unittest.TestCase):
    def test_fuzz_fx_1000(self):
        import random; rnd = random.Random(42)
        pool = [None, 0, -1, "x", [], {}, float("nan"), 5.0, "5.4"]
        for i in range(1000):
            fx = rnd.choice([None, {}, {"usdbrl": rnd.choice(pool), "ts": rnd.choice([time.time(), time.time()-2000, None, "x"])}])
            self.assertIsInstance(gw._fx_fresh(fx), bool)
    def test_fuzz_ok_500(self):
        import random; rnd = random.Random(99)
        pool = [None, "", "abc", 0, float("nan"), float("inf"), 3.14, "5.15", 1.0, 20.0, 99]
        for i in range(500):
            try: gw._ok_usdtbrl(rnd.choice(pool))
            except ValueError: pass
    def test_fuzz_poll_100(self):
        import itertools
        combos = list(itertools.product(["ok", None], ["ok", None], ["fresco", "velho", None], ["ok", "raise"]))
        for usd_s, brl_s, fx_s, gorg_s in combos:
            w = _mk_widget()
            usd = {"price": 4000.0, "bid": 1, "ask": 1} if usd_s == "ok" else None
            brl = {"price": 20000.0} if brl_s == "ok" else None
            fx = {"usdbrl": 5.0, "ts": time.time()} if fx_s == "fresco" else ({"usdbrl": 5.0, "ts": time.time()-9999} if fx_s == "velho" else None)
            gorg = {"price": 3990.0} if gorg_s == "ok" else "raise"
            def _g(curr):
                if gorg == "raise": raise RuntimeError("morto")
                return gorg
            with contextlib.ExitStack() as st:
                st.enter_context(patch.object(gw, "try_fetch", side_effect=[(usd, None), (brl, None)]))
                st.enter_context(patch.object(gw, "collect_china", side_effect=lambda last, _fx=fx: last.update({"fx": _fx}) or None))
                mg = st.enter_context(patch.object(gw, "fetch_goldprice_org")); mg.side_effect = _g
                st.enter_context(patch.object(gw, "_due", return_value=False))
                st.enter_context(patch.object(gw, "save_cache"))
                st.enter_context(patch.object(gw, "save_hist_log", return_value=None))
                w._poll_once_impl()  # nunca deve levantar
    def test_fuzz_to_float_500(self):
        import random; rnd = random.Random(7)
        pool = [None, "", "abc", "1,000.5", [], {}, " 5.2 ", "NaN", 0, 3.14]
        for i in range(500):
            gw._to_float(rnd.choice(pool))

if __name__ == "__main__":
    unittest.main(verbosity=2)
