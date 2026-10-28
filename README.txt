SolBot CMD - Uji 5 Mode (Easy, Medium, Hard, Exclusive, Narasi) dengan saldo DEMO
================================================================
1. Install Python 3.10+ (centang "Add Python to PATH").
2. Ekstrak zip ini, lalu klik dua kali start_windows.bat
   (atau buka CMD di folder ini: pip install -r requirements.txt lalu python solbot.py)
3. Buka di Chrome HP: https://solbot-notif-isla.netlify.app/#k=A-bSo1BUpHIeiTeA1FQIxA
   Tekan "Aktifkan notifikasi di HP ini" lalu "Izinkan".

Mode:
- EASY   = setingan awal (dulu Aman)
- MEDIUM = MC kecil ikut tema trending (dulu Meta)
- HARD   = scalping 0,1 SOL, trailing +10%/5%, TP 1000%, SL 10% (dulu Postingan)
- EXCLUSIVE = Hard + anti-dump: umur koin min 30 menit, tolak kalau ada candle 1 menit turun >=30%
              atau turun >=50% dari puncak dalam 60 menit terakhir
- NARASI = pemburu koin meme dexpaid/boost yang memimpin narasinya.
            Skor: narasi ramai +20, pemimpin volume +25, dexpaid paling awal +20 (dexpaid saja +8), boost +5,
            volume 5m naik +15, akun X +10, lulus bonding < 1 jam +10. Tiruan -30, sudah naik >1000%/1j -15,
            sniper/bundler tinggi -25. Beli kalau skor >= 60 dan lolos RugCheck (top10 <=30%, dev <=5%, holder >=150).
            TP/SL: SL -20% | TP1 +50% jual 50%, SL sisa pindah ke entry | trailing 20% dari puncak setelah +50%
                   | TP penuh +300% | batas tahan 3 jam | 0,1 SOL per beli, maks 3 posisi | rugi harian maks 30%.
Tiap mode punya saldo demo 1 SOL sendiri, data di folder modes/<mode>/.

Perintah lain:
  python solbot.py hard          jalankan satu mode saja
  python solbot.py exclusive     jalankan mode Exclusive saja
  python solbot.py narasi        jalankan mode Narasi saja
  Ctrl+C                         berhenti
SALDO HABIS (semua mode, AUTO_STOP_LOW_BALANCE=true):
  Jika saldo mode tidak cukup untuk beli dan tidak ada posisi terbuka, mode itu BERHENTI TOTAL,
  kirim notifikasi, dan tidak dijalankan lagi (juga saat solbot.py dibuka ulang) sampai direset.
  Mode lain tetap jalan. Posisi terbuka tetap dijaga sampai terjual dulu.
Reset saldo ke START_SOL (1 SOL):
  python solbot.py --reset           semua mode + riwayat Netlify
  python solbot.py --reset hard      hanya mode hard (mode lain tidak tersentuh)
PC harus tetap menyala dan terhubung internet selama tes.
