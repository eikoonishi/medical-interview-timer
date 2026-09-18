#!/usr/bin/env python3
"""
2026postOSCE/音声/*.mp3 を postosce6/sounds/*.m4a に変換する。

・放送の間隔が空くとスピーカー（アンプ）が眠り、鳴り始めの数百msが
  欠けるので、各音声の先頭に無音を足す。
・♪のついた放送は「ベル＋アナウンス」を1つのファイルに合成する
  （<name>_b.m4a）。iOS は音声を同時に鳴らせないことがあり、別々に
  鳴らすとアナウンスが出ないことがあるため。

音声を差し替えたら、2026postOSCE/音声/ の該当ファイルを上書きして
このスクリプトを実行し直すこと。
    python3 postosce6/tools/build_sounds.py
"""
import os, shutil, struct, subprocess, sys, tempfile, wave

LEAD_SEC  = 0.4       # 先頭に足す無音の長さ（秒）
BELL_KEEP = 1.2       # ベルとして使う長さ（秒）。後半の無音を捨てる
BELL_GAP  = 0.2       # ベルとアナウンスのあいだ（秒）

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC  = os.path.join(ROOT, "2026postOSCE", "音声")
DST  = os.path.join(ROOT, "postosce6", "sounds")

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

# ♪がついている放送（Excelのベル列）＝ベル入り版もつくる
BELL_FILES = ["check2", "check3", "check7", "enter", "start",
              "end", "end_break", "am_end", "all_end"]

SR = 24000            # アナウンスのサンプルレート（mono）


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(map(str, cmd)) + "\n" + r.stderr.decode())


def read_wav(path):
    with wave.open(path, "rb") as w:
        return w.getnchannels(), w.getsampwidth(), w.getframerate(), w.readframes(w.getnframes())


def write_wav(path, ch, sw, sr, data):
    with wave.open(path, "wb") as w:
        w.setnchannels(ch); w.setsampwidth(sw); w.setframerate(sr)
        w.writeframes(data)


def encode(wav_path, out_path, ch):
    run(["afconvert", "-f", "m4af", "-d", "aac",
         "-b", "96000" if ch > 1 else "64000", wav_path, out_path])


def main():
    os.makedirs(DST, exist_ok=True)
    tmp = tempfile.mkdtemp()
    try:
        # ベルをアナウンスと同じ形式（24kHz mono）に落として用意する
        bell_src = os.path.join(SRC, "bell.mp3")
        if not os.path.exists(bell_src):
            print("!! bell.mp3 がありません"); return
        bell24 = os.path.join(tmp, "bell24.wav")
        run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{SR}", "-c", "1", bell_src, bell24])
        _, sw, _, bell_data = read_wav(bell24)
        bell_data = bell_data[: int(SR * BELL_KEEP) * sw]          # 鳴り終わりで切る
        gap = b"\x00" * (int(SR * BELL_GAP) * sw)
        lead24 = b"\x00" * (int(SR * LEAD_SEC) * sw)

        n_plain = n_bell = 0
        for name, src_name in FILES.items():
            src = os.path.join(SRC, src_name)
            if not os.path.exists(src):
                print(f"  !! 見つかりません: {src_name}")
                continue

            raw = os.path.join(tmp, name + ".wav")
            run(["afconvert", "-f", "WAVE", "-d", "LEI16", src, raw])
            ch, sw_i, sr_i, data = read_wav(raw)

            # 単独版（先頭に無音を足すだけ。ベルはここで長さを切る）
            body = data[: int(sr_i * BELL_KEEP) * ch * sw_i] if name == "bell" else data
            pad = os.path.join(tmp, name + "_pad.wav")
            write_wav(pad, ch, sw_i, sr_i, b"\x00" * (int(sr_i * LEAD_SEC) * ch * sw_i) + body)
            encode(pad, os.path.join(DST, name + ".m4a"), ch)
            dur = len(body) / (sr_i * ch * sw_i) + LEAD_SEC
            print(f"  {name:<12} {src_name:<16} {dur:5.2f}秒")
            n_plain += 1

            # ベル入り版
            if name in BELL_FILES:
                if sr_i != SR or ch != 1:
                    v = os.path.join(tmp, name + "_24.wav")
                    run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{SR}", "-c", "1", src, v])
                    _, _, _, voice = read_wav(v)
                else:
                    voice = data
                bpad = os.path.join(tmp, name + "_b.wav")
                write_wav(bpad, 1, sw, SR, lead24 + bell_data + gap + voice)
                encode(bpad, os.path.join(DST, name + "_b.m4a"), 1)
                bdur = (len(bell_data) + len(gap) + len(voice)) / (SR * sw) + LEAD_SEC
                print(f"  {name+'_b':<12} {'♪ベル＋' + src_name:<16} {bdur:5.2f}秒")
                n_bell += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n単独 {n_plain} 件 ＋ ベル入り {n_bell} 件 を {DST} に出力しました")
    print(f"（先頭 {LEAD_SEC} 秒の無音／ベル {BELL_KEEP} 秒＋間 {BELL_GAP} 秒）")


if __name__ == "__main__":
    main()
