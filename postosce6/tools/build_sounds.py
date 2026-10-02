#!/usr/bin/env python3
"""
2026postOSCE/音声/*.mp3 を postosce6/sounds/*.mp3 に変換する。

・形式は 44.1kHz モノラル MP3（MPEG-1 Layer III）。
  Windows の Chrome で m4a(AAC) が再生されなかったため、最も互換性の高い
  この形式に統一している。勝手に m4a や 24kHz に変えないこと。
・放送の間隔が空くとスピーカー（アンプ）が眠り、鳴り始めの数百msが欠ける
  ので、各音声の先頭に無音を足す。
・♪のついた放送は「ベル＋アナウンス」を1つのファイルに合成する
  （<name>_b.mp3）。iOS は音声を同時に鳴らせないことがあるため。

音声を差し替えたら、2026postOSCE/音声/ の該当ファイルを上書きして
このスクリプトを実行し直すこと。
    python3 postosce6/tools/build_sounds.py
"""
import os, shutil, subprocess, tempfile, wave

LEAD_SEC  = 0.4       # 先頭に足す無音（秒）
BELL_KEEP = 1.2       # ベルとして使う長さ（秒）。後半の無音を捨てる
BELL_GAP  = 0.2       # ベルとアナウンスのあいだ（秒）
SR        = 44100     # サンプルレート（MPEG-1 Layer III になる値）
KBPS      = "96k"

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


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


FF = ffmpeg()


def run(args):
    r = subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error"] + args,
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(args) + "\n" + r.stderr.decode())


def to_wav(src, dst):
    """44.1kHz モノラル 16bit の wav にそろえる"""
    run(["-i", src, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", dst])


def read_frames(path):
    with wave.open(path, "rb") as w:
        return w.readframes(w.getnframes())


def write_wav(path, data):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data)


def to_mp3(wav_path, out_path):
    run(["-i", wav_path, "-c:a", "libmp3lame", "-b:a", KBPS, "-ac", "1", out_path])


def main():
    os.makedirs(DST, exist_ok=True)
    tmp = tempfile.mkdtemp()
    try:
        bell_src = os.path.join(SRC, "bell.mp3")
        if not os.path.exists(bell_src):
            print("!! bell.mp3 がありません"); return
        bw = os.path.join(tmp, "bell.wav")
        to_wav(bell_src, bw)
        bell = read_frames(bw)[: int(SR * BELL_KEEP) * 2]      # 鳴り終わりで切る
        gap  = b"\x00" * (int(SR * BELL_GAP) * 2)
        lead = b"\x00" * (int(SR * LEAD_SEC) * 2)

        n1 = n2 = 0
        for name, src_name in FILES.items():
            src = os.path.join(SRC, src_name)
            if not os.path.exists(src):
                print(f"  !! 見つかりません: {src_name}")
                continue

            raw = os.path.join(tmp, name + ".wav")
            to_wav(src, raw)
            data = read_frames(raw)
            if name == "bell":
                data = data[: int(SR * BELL_KEEP) * 2]

            # 単独版
            pad = os.path.join(tmp, name + "_pad.wav")
            write_wav(pad, lead + data)
            to_mp3(pad, os.path.join(DST, name + ".mp3"))
            print(f"  {name:<12} {len(lead + data) / (SR * 2):6.2f}秒")
            n1 += 1

            # ベル入り版
            if name in BELL_FILES:
                bpad = os.path.join(tmp, name + "_b.wav")
                write_wav(bpad, lead + bell + gap + data)
                to_mp3(bpad, os.path.join(DST, name + "_b.mp3"))
                print(f"  {name + '_b':<12} {len(lead + bell + gap + data) / (SR * 2):6.2f}秒  ♪ベル＋")
                n2 += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n単独 {n1} 件 ＋ ベル入り {n2} 件 → {DST}")
    print(f"（{SR}Hz モノラル MP3 {KBPS} ／ 先頭 {LEAD_SEC} 秒の無音）")


if __name__ == "__main__":
    main()
