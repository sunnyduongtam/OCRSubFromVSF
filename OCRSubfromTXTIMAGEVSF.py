import asyncio
import os
import re
import argparse
from chrome_lens_py import LensAPI

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
CONCURRENCY = 4   # tăng 5–6 nếu mạng tốt

def parse_time(t):
    h, m, s, ms = t.split("_")
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int(ms):03}"

def parse_srt_time(filename):
    m = re.match(r"(\d+_\d+_\d+_\d+)__(\d+_\d+_\d+_\d+)", filename)
    if not m:
        return None, None
    return parse_time(m.group(1)), parse_time(m.group(2))

async def ocr_one(api, sem, img_path, fname, idx, total):
    async with sem:
        try:
            res = await api.process_image(image_path=img_path)
            if isinstance(res, dict):
                text = res.get("ocr_text", "")
            else:
                text = str(res)

            text = " ".join(text.split()).strip()
            print(f"[{idx}/{total}] OCR → {fname}")
            return fname, text
        except Exception as e:
            print(f"⚠️ Lỗi OCR {fname}: {e}")
            return fname, ""

async def images_to_srt_fast(img_dir, output_srt):
    api = LensAPI()
    sem = asyncio.Semaphore(CONCURRENCY)

    files = sorted(
        f for f in os.listdir(img_dir)
        if f.lower().endswith(IMAGE_EXTS)
    )
    total = len(files)

    if total == 0:
        print("❌ Không tìm thấy ảnh phụ đề")
        return

    tasks = []
    for i, fname in enumerate(files, 1):
        img_path = os.path.join(img_dir, fname)
        tasks.append(ocr_one(api, sem, img_path, fname, i, total))

    results = await asyncio.gather(*tasks)

    index = 1
    with open(output_srt, "w", encoding="utf-8") as srt:
        for fname, text in results:
            if not text:
                continue

            start, end = parse_srt_time(fname)
            if not start:
                continue

            srt.write(f"{index}\n")
            srt.write(f"{start} --> {end}\n")
            srt.write(f"{text}\n\n")
            index += 1

    print(f"✅ Hoàn tất xuất SRT: {output_srt}")

def main():
    parser = argparse.ArgumentParser(
        description="OCR thư mục ảnh phụ đề → xuất SRT (Google Lens)"
    )
    parser.add_argument(
        "-p", "--path",
        required=True,
        help="Đường dẫn thư mục chứa ảnh phụ đề"
    )
    parser.add_argument(
        "-o", "--output",
        default="output.srt",
        help="File SRT đầu ra (mặc định: output.srt)"
    )

    args = parser.parse_args()

    asyncio.run(images_to_srt_fast(args.path, args.output))

if __name__ == "__main__":
    main()
