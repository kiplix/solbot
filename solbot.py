#!/usr/bin/env python3
"""SolBot CMD • Uji 5 mode (Easy, Medium, Hard, Exclusive, Narasi) dengan saldo DEMO, notifikasi ke Netlify.
Jalankan:  python solbot.py                  (semua mode)
           python solbot.py hard             (satu mode saja)
Reset:     python solbot.py --reset          (semua mode kembali ke START_SOL)
           python solbot.py --reset hard     (hanya mode hard)
Berhenti:  Ctrl+C
Mode yang saldonya habis/kurang untuk beli berhenti sendiri dan tidak jalan lagi sampai direset.
"""
import os
import sys
import time
import json
import signal
import threading
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
if os.name == "nt":
    os.system("")  # aktifkan warna ANSI di CMD Windows
COL = {"easy": "\033[94m", "medium": "\033[95m", "hard": "\033[93m", "exclusive": "\033[38;5;208m",
       "narasi": "\033[38;5;201m"}
LBL = {"easy": "EASY     ", "medium": "MEDIUM   ", "hard": "HARD     ", "exclusive": "EXCLUSIVE", "narasi": "NARASI   "}
ALL = "easy,medium,hard,exclusive,narasi"
G, R, C, D, X = "\033[92m", "\033[91m", "\033[96m", "\033[90m", "\033[0m"


def env():
    vals = {}
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals


def pump(mode, proc):
    for raw in iter(proc.stdout.readline, b""):
        line = raw.decode("utf-8", "replace").rstrip()
        if not line:
            continue
        col = COL[mode]
        if "[NETLIFY]" in line:
            col = C if "terkirim" in line else R
        elif "TUTUP" in line:
            col = R if "pnl -" in line else G
        elif " BUY " in line:
            col = "\033[97m"
        elif "error" in line.lower() or "Traceback" in line or "SALDO HABIS" in line or "BERHENTI" in line:
            col = R
        print(f"{col}[{LBL[mode]}] {line}{X}", flush=True)


def summary(modes):
    parts = []
    for m in modes:
        try:
            with open(os.path.join(ROOT, "modes", m, "data", "status.json")) as f:
                st = json.load(f)
            eq, start = st.get("eq") or 0, st.get("start") or 1
            ch = (eq / start - 1) * 100
            parts.append(f"{COL[m]}{m.upper()} {eq:.4f} SOL ({'+' if ch >= 0 else ''}{ch:.1f}%){X}")
        except Exception:
            parts.append(f"{COL[m]}{m.upper()} -{X}")
    print(f"\n RINGKASAN  " + "   ".join(parts) + "\n", flush=True)


def stopped(m):
    return os.path.exists(os.path.join(ROOT, "modes", m, "data", "STOPPED.json"))


def upgrade_env():
    """.env lama otomatis ditambah mode exclusive + narasi dan pengaturan auto-stop saldo habis."""
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        return
    with open(p, encoding="utf-8") as f:
        lines = f.read().splitlines()
    changed = False
    for i, line in enumerate(lines):
        if line.strip().replace(" ", "").lower() in ("modes=easy,medium,hard", "modes=easy,medium,hard,exclusive"):
            lines[i] = "MODES=" + ALL
            changed = True
    if not any(l.strip().startswith("AUTO_STOP_LOW_BALANCE") for l in lines):
        lines += ["", "# Saldo habis/kurang untuk beli (dan tidak ada posisi) -> mode berhenti total sampai direset",
                  "# Reset: python solbot.py --reset   atau   python solbot.py --reset hard",
                  "AUTO_STOP_LOW_BALANCE=true"]
        changed = True
    if changed:
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"{G}.env diperbarui: mode NARASI + auto-stop saldo habis ditambahkan{X}")


def main():
    upgrade_env()
    E = env()
    picked = [a.lower() for a in sys.argv[1:] if a.lower() in COL]
    if "--reset" in sys.argv:
        import shutil
        if picked:  # reset sebagian: hanya mode yang disebut
            for m in picked:
                shutil.rmtree(os.path.join(ROOT, "modes", m), ignore_errors=True)
            print(f"{G}Saldo demo {', '.join(m.upper() for m in picked)} direset ke {E.get('START_SOL', '1')} SOL.{X}")
            picked = []
        else:
            shutil.rmtree(os.path.join(ROOT, "modes"), ignore_errors=True)
            try:
                import requests
                requests.post(E.get("NETLIFY_URL", "").rstrip("/") + "/api/clear", headers={"x-key": E.get("NETLIFY_KEY", "")}, timeout=15)
            except Exception:
                pass
            print(f"{G}Semua saldo demo direset ke {E.get('START_SOL', '1')} SOL, riwayat Netlify dibersihkan.{X}")
    modes = picked or \
        [m.strip().lower() for m in E.get("MODES", ALL).split(",") if m.strip().lower() in COL]
    off = [m for m in modes if stopped(m)]
    for m in off:
        print(f"{R}[{LBL[m]}] BERHENTI: saldo habis. Reset dulu: python solbot.py --reset {m}{X}")
    modes = [m for m in modes if m not in off]
    if not modes:
        print(f"{R}Semua mode berhenti karena saldo habis. Jalankan: python solbot.py --reset{X}")
        return
    print(f"{G}SolBot CMD • DEMO {E.get('START_SOL', '1')} SOL per mode • {', '.join(m.upper() for m in modes)}{X}")
    print(f"{D}Notifikasi: {E.get('NETLIFY_URL') or 'Netlify mati (NETLIFY_URL kosong)'}{X}")
    print(f"{D}Jam beli: {'24 jam' if E.get('TRADE_HOURS_ENABLED', 'false').lower() != 'true' else E.get('TRADE_START', '20:00') + '-' + E.get('TRADE_END', '03:00') + ' WIB'} • Ctrl+C untuk berhenti{X}")
    print(D + "-" * 70 + X)
    procs = {}
    for i, m in enumerate(modes):
        if i:
            time.sleep(15)  # jeda supaya tidak kena batas API gratis bersamaan
        p = subprocess.Popen([sys.executable, "-u", os.path.join(ROOT, "run_one.py"), m], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        procs[m] = p
        threading.Thread(target=pump, args=(m, p), daemon=True).start()
    last = time.time()
    try:
        while True:
            time.sleep(5)
            for m, p in list(procs.items()):
                if p.poll() is not None and p.returncode == 99:
                    del procs[m]
                    print(f"{R}[{LBL[m]}] ⛔ BERHENTI TOTAL: saldo habis/kurang untuk beli. "
                          f"Tidak dijalankan lagi sampai direset: python solbot.py --reset {m}{X}", flush=True)
                    if not procs:
                        print(f"{R}Semua mode sudah berhenti karena saldo habis.{X}")
                        summary(modes)
                        return
                    continue
                if p.poll() is not None:
                    print(f"{R}[{LBL[m]}] berhenti (kode {p.returncode}), dinyalakan ulang dalam 20 detik{X}")
                    time.sleep(20)
                    np = subprocess.Popen([sys.executable, "-u", os.path.join(ROOT, "run_one.py"), m], cwd=ROOT,
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))
                    procs[m] = np
                    threading.Thread(target=pump, args=(m, np), daemon=True).start()
            if time.time() - last > 600:
                summary(modes)
                last = time.time()
    except KeyboardInterrupt:
        print(f"\n{D}Menghentikan bot...{X}")
        for p in procs.values():
            try:
                if os.name == "nt":
                    p.terminate()
                else:
                    p.send_signal(signal.SIGINT)
            except Exception:
                pass
        time.sleep(3)
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        summary(modes)
        print("Bot dihentikan.")


if __name__ == "__main__":
    main()
