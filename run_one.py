#!/usr/bin/env python3
"""Menjalankan SATU mode (easy/medium/hard) dengan saldo demo. Dipanggil otomatis oleh solbot.py."""
import os
import re
import sys
import json
import html
import time
import queue
import logging
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))
MODES = {"easy": ("aman", "EASY"), "medium": ("meta", "MEDIUM"), "hard": ("post", "HARD"),
         "exclusive": ("excl", "EXCLUSIVE"), "narasi": ("nara", "NARASI")}
mode = (sys.argv[1] if len(sys.argv) > 1 else "easy").lower()
if mode not in MODES:
    print("Mode harus easy, medium, hard, exclusive, atau narasi")
    sys.exit(1)
strategy, LABEL = MODES[mode]
HOME = os.path.join(ROOT, "modes", mode)
os.makedirs(os.path.join(HOME, "data"), exist_ok=True)
os.environ["SOLBOT_HOME"] = HOME  # harus sebelum import solbot
STOP_FILE = os.path.join(HOME, "data", "STOPPED.json")
if os.path.exists(STOP_FILE):
    print("Mode %s BERHENTI karena saldo habis. Reset dulu: python solbot.py --reset %s" % (LABEL, mode))
    sys.exit(99)


def env_root():
    vals = {}
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


E = env_root()
settings = {
    "STRATEGY": strategy,
    "ENABLE_TRADING": True,
    "DEMO_MODE": True,              # selalu saldo demo, tidak ada transaksi asli
    "ENABLE_LIHAT": False,
    "ENABLE_DOMPET": False,
    "PAPER_START_SOL": E.get("START_SOL", "1"),
    "TRADE_HOURS_ENABLED": E.get("TRADE_HOURS_ENABLED", "false"),
    "TRADE_START": E.get("TRADE_START", "20:00"),
    "TRADE_END": E.get("TRADE_END", "03:00"),
    "TELEGRAM_BOT_TOKEN": E.get("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": E.get("TELEGRAM_CHAT_ID", ""),
    "TELEGRAM_ADMIN_ID": "",        # perintah Telegram dimatikan supaya 3 bot tidak berebut
    "TIMEZONE_OFFSET_HOURS": E.get("TIMEZONE_OFFSET_HOURS", "7"),
    "AUTO_STOP_LOW_BAL": E.get("AUTO_STOP_LOW_BALANCE", "true"),
}
for k in ("RPC_URL", "HELIUS_API_KEY", "TRIG_GMGN", "TRIG_METEORA"):
    if E.get(k):
        settings[k] = E[k]
with open(os.path.join(HOME, "settings.json"), "w") as f:
    json.dump(settings, f, indent=1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S", stream=sys.stdout)
logging.getLogger("urllib3").setLevel(logging.WARNING)
log = logging.getLogger("solbot")

import requests  # noqa: E402
from solbot import engine  # noqa: E402
from solbot.telegram import Telegram  # noqa: E402

NURL = (E.get("NETLIFY_URL") or "").rstrip("/")
NKEY = E.get("NETLIFY_KEY", "")
Q = queue.Queue()
S = requests.Session()


def post(path, body):
    if not NURL:
        return False
    for i in range(3):
        try:
            r = S.post(NURL + path, json=body, headers={"x-key": NKEY}, timeout=15)
            if r.status_code < 300:
                return True
            log.warning("[NETLIFY] gagal %s: HTTP %s", path, r.status_code)
            if r.status_code in (401, 403):
                return False
        except Exception as e:
            log.warning("[NETLIFY] gagal kirim: %s", type(e).__name__)
        time.sleep(3 * (i + 1))
    return False


def kind_of(t):
    u = t.upper()
    if "SINYAL" in u:
        return "sinyal"
    if "STOP LOSS" in u:
        return "sl"
    if any(k in u for k in ("TP1", "TRAIL", "TAKE PROFIT", "KELUAR", "WAKTU", "PANIC", "JUAL")):
        return "jual"
    if "BELI" in u:
        return "beli"
    return "info"


def clean(text):
    t = re.sub(r"<[^>]+>", "", text)
    t = html.unescape(t)
    t = re.sub(r"^\[[A-Z ]+\]\s*", "", t.strip())
    return [l.strip() for l in t.splitlines() if l.strip() and not set(l.strip()) <= set("─-")]


def worker():
    while True:
        ev = Q.get()
        if post("/api/events", ev):
            log.info("[NETLIFY] terkirim \u2713 (%s)", ev["title"][:50])


_orig_send = Telegram.send


def send(self, text, chat=None, buttons=None):
    try:
        lines = clean(text)
        if lines:
            url = ""
            for row in buttons or []:
                for b in row:
                    if b.get("url") and not url:
                        url = b["url"]
            pnl = None
            k = kind_of(lines[0])
            m = k in ("jual", "sl") and re.search(r"([+-]\d+(?:[.,]\d+)?)%", " ".join(lines[:3]))
            if m:
                pnl = float(m.group(1).replace(",", "."))
            Q.put({"mode": mode, "kind": k, "title": lines[0][:120],
                   "body": "\n".join(lines[1:8])[:600], "url": url, "pnl": pnl, "ts": int(time.time() * 1000)})
    except Exception as e:
        log.warning("[NETLIFY] format gagal: %s", e)
    if self.token and (chat or self.chat):
        return _orig_send(self, text, chat, buttons)


Telegram.send = send


def status_loop():
    while True:
        gap = 300 if not status_once() else 60  # ada posisi: tiap 60 detik, tanpa posisi: 5 menit
        time.sleep(gap)


def status_once(stopped=False):
    """Kirim status ke Netlify. Returns True jika ada posisi terbuka."""
    p = os.path.join(HOME, "data", "status.json")
    if True:
        try:
            with open(p) as f:
                st = json.load(f)
            with open(os.path.join(HOME, "data", "state_paper.json")) as f:
                sp = json.load(f)
            st["positions"] = sp.get("positions") or []
            tr = (sp.get("history") or {}).get("trades") or []
            wins = sum(1 for t in tr if (t.get("pnl_sol") or 0) > 0)
            pos, open_val = [], 0.0
            for x in st.get("positions") or []:
                entry = x.get("entry") or 0
                px = x.get("last_px") or entry
                remain = (x.get("cost_sol") or 0) * (x.get("frac") or 1)
                val = remain * (px / entry) if entry else remain
                open_val += val
                pos.append({"symbol": x.get("symbol"), "entry": entry, "px": px, "peak": x.get("peak") or entry,
                            "sl": x.get("sl"), "tp": x.get("tp1"), "cost": x.get("cost_sol"), "value": round(val, 6),
                            "pnl": round((px / entry - 1) * 100, 2) if entry else 0, "opened": x.get("opened"),
                            "last": x.get("last"), "url": x.get("url") or "", "half": x.get("half", False)})
            closed = sum((t.get("pnl_sol") or 0) for t in tr)
            start = sp.get("paper_start_sol") or st.get("start") or 1
            free = start + closed - sum((x.get("cost_sol") or 0) for x in st["positions"]) + \
                sum((x.get("received_sol") or 0) for x in st["positions"])
            eq = free + open_val
            post("/api/status", {"mode": mode, "eq": round(eq, 6), "start": start, "closed_pnl": closed,
                                 "positions": len(pos), "pos": pos, "trades": len(tr), "wins": wins,
                                 "window": st.get("window"), "paused": st.get("paused"),
                                 "stopped": bool(stopped or st.get("stopped")), "ts": int(time.time() * 1000)})
            return bool(pos)
        except Exception:
            return False


if __name__ == "__main__":
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=status_loop, daemon=True).start()
    if not NURL:
        log.info("NETLIFY_URL kosong: notifikasi Netlify mati, bot tetap jalan.")
    bot = engine.Bot()
    import signal
    try:
        bot.run()
    except SystemExit as e:
        if e.code == 99:  # saldo habis: kirim notifikasi terakhir lalu berhenti total
            t0 = time.time()
            while not Q.empty() and time.time() - t0 < 20:
                time.sleep(1)
            status_once(stopped=True)
            print("Mode %s BERHENTI: saldo habis/kurang untuk beli. Reset: python solbot.py --reset %s" % (LABEL, mode))
        raise
    except KeyboardInterrupt:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            bot.save()
        except Exception:
            pass
        print("Mode %s dihentikan, data tersimpan." % LABEL)
