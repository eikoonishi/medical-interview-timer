#!/usr/bin/env python3
"""
2026postOSCE/音声/*.mp3 を postosce6/sounds/*.m4a に変換する。

放送の間隔が空くとスピーカー（アンプ）がスリープし、鳴り始めの数百msが
欠けてしまうため、各音声の先頭に無音を足してから m4a に変換する。

音声を差し替えたら、2026postOSCE/音声/ の該当ファイルを上書きして
このスクリプトを実行し直すこと。
    python3 postosce6/tools/build_sounds.py
"""
import os, shutil, struct, subprocess, sys, tempfile, wave

LEAD_SEC = 0.4          # 先頭に足す無音の長さ（秒）

ROOT  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC   = os.path.join(ROOT, "2026postOSCE", "音声")
DST   = os.path.join(ROOT, "postosce6", "sounds")

FILES = {
    "bell":      "bell.mp3",
    "check1":    "音声確認_1.mp3",  "check2": "音声確認_2.mp3",
    "check3":    "音声確認_3.mp3",  "check4": "音声確認_4.mp3",
    "check5":    "音声確認_5.mp3",  "check6": "音声確認_6.mp3",
    "check7":    "音声確認_7.mp3",  "check8": "音声確認_8.mp3",
    "pre1":      "開始前_1.mp3",    "pre2":   "開始前_2.mp3",  "pre3": "開始前_3.mp3",
    "min1":      "1分前.mp3",       "min3":   "3分前.mp3",
    "enter":     "入室.mp3",        "start":  "開始.mp3",
    "min6":      "6分経過.mp3",     "min12":  "12分経過.mp3",
    "end":       "終了.mp3",        "end_break": "終了+休憩.mp3",
    "am_end":    "前半終了.mp3",    "all_end":   "全体終了.mp3",
}

def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(cmd) + "\n" + r.stderr.decode())

def main():
    os.makedirs(DST, exist_ok=True)
    tmp = tempfile.mkdtemp()
    ok = 0
    try:
        for name, src_name in FILES.items():
            src = os.path.join(SRC, src_name)
            if not os.path.exists(src):
                print(f"  !! 見つかりません: {src_name}")
                continue

            raw = os.path.join(tmp, name + ".wav")
            pad = os.path.join(tmp, name + "_pad.wav")
            out = os.path.join(DST, name + ".m4a")

            run(["afconvert", "-f", "WAVE", "-d", "LEI16", src, raw])

            with wave.open(raw, "rb") as w:
                ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
                data = w.readframes(n)
            silence = b"\x00" * (int(sr * LEAD_SEC) * ch * sw)
            with wave.open(pad, "wb") as w:
                w.setnchannels(ch); w.setsampwidth(sw); w.setframerate(sr)
                w.writeframes(silence + data)

            run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "96000" if ch > 1 else "64000", pad, out])
            print(f"  {name:<10} {src_name:<16} {ch}ch {sr}Hz  {(n/sr):5.2f}秒 → {(n/sr)+LEAD_SEC:5.2f}秒")
            ok += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{ok} 件を {DST} に出力しました（先頭に {LEAD_SEC} 秒の無音を追加）")

if __name__ == "__main__":
    main()
