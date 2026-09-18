#!/usr/bin/env python3
"""生成中文字模（GB2312 一级常用字），SSD1306/OLEDDisplay 的列优先位图格式。

格式（与 OLEDDisplay::drawInternal 一致）：
  每个字 = 宽 12 列 x 高 12 行；每列 2 字节（ceil(12/8)）
  列内 bit0 = 最上面那行（SSD1306 纵向 8 像素字节）
  ⇒ 每字固定 24 字节
输出：项目内 src/graphics/fonts/CJKBitmapFont.cpp（含 cjk_codes / cjk_bitmaps / cjk_count）
用法：python3 gen_cjk_font.py [输出路径]
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

TTF = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SIZE = 10
W = H = 12
RASTER = (H + 7) // 8          # 2
STRIDE = W * RASTER            # 24

OUT = sys.argv[1] if len(sys.argv) > 1 else "src/graphics/fonts/CJKBitmapFont.cpp"

font = ImageFont.truetype(TTF, SIZE)

chars = []
for hi in range(0xB0, 0xD8):
    for lo in range(0xA1, 0xFF):
        try:
            ch = bytes([hi, lo]).decode('gb2312')
        except UnicodeDecodeError:
            continue
        if len(ch) == 1 and '\u4e00' <= ch <= '\u9fff':
            chars.append(ch)
for ch in "，。！？、；：（）《》【】“”‘’—…·　":
    chars.append(ch)
cps = sorted({ord(c) for c in chars})

bitmaps = bytearray()
for cp in cps:
    img = Image.new("1", (W, H), 0)
    ImageDraw.Draw(img).text((0, -2), chr(cp), font=font, fill=1)
    px = img.load()
    for x in range(W):
        for band in range(RASTER):
            b = 0
            for k in range(8):
                y = band * 8 + k
                if y < H and px[x, y]:
                    b |= 1 << k
            bitmaps.append(b)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    f.write("// 自动生成（tools/gen_cjk_font.py）：GB2312 一级常用字 %d 个，%dx%d，列优先位图（每字 %d 字节）\n"
            % (len(cps), W, H, STRIDE))
    f.write("// C++ 下 const 全局默认内部链接，必须用 extern 才能被库（OLEDDisplay.cpp）引用\n")
    f.write("// 数据来自 Noto Sans CJK（本机 /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc）\n")
    f.write("#include <stdint.h>\n#include <pgmspace.h>\n\n")
    f.write('extern "C" const uint16_t cjk_count = %d;\n' % len(cps))
    f.write('extern "C" const uint16_t cjk_codes[%d] PROGMEM = {\n' % len(cps))
    for i in range(0, len(cps), 16):
        f.write("  " + ",".join("0x%04X" % c for c in cps[i:i + 16]) + ",\n")
    f.write("};\n\n")
    f.write('extern "C" const uint8_t cjk_bitmaps[%d] PROGMEM = {\n' % len(bitmaps))
    for i in range(0, len(bitmaps), 16):
        f.write("  " + ",".join("0x%02X" % b for b in bitmaps[i:i + 16]) + ",\n")
    f.write("};\n")

print("字形 %d 个；字模 %.1f KB；码表 %.1f KB；总 %.1f KB -> %s" % (
    len(cps), len(bitmaps) / 1024, len(cps) * 2 / 1024,
    (len(bitmaps) + len(cps) * 2) / 1024, OUT), file=sys.stderr)
