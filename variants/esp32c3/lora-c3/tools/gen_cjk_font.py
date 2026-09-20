#!/usr/bin/env python3
"""生成中文字模（GB2312 一级常用字），SSD1306/OLEDDisplay 的列优先位图格式。

格式（与 OLEDDisplay::drawInternal 一致）：
  每个字 = 宽 W 列 x 高 H 行；每列 ceil(H/8) 字节
  列内 bit0 = 最上面那行（SSD1306 纵向 8 像素字节）
  ⇒ 每字固定 W * ceil(H/8) 字节
输出：项目内 src/graphics/fonts/CJKBitmapFont.cpp（含 cjk_codes / cjk_bitmaps / cjk_count）
用法：python3 gen_cjk_font.py [输出路径]

★ 字模格尺寸必须与构建宏一致（否则行距/错位会炸）：
    CJK_W / CJK_H / CJK_STRIDE ← variants/esp32c3/lora-c3/platformio.ini
    本脚本用同样的环境变量取（默认由 CJK_CELL 推出，如 CJK_CELL=16 → W=H=16、STRIDE=32）

★ 字体（2026-09-19 定稿）：**文泉驿点阵宋体 wenquanyi_13px.pcf @14px**（点阵 CJK）
    为什么不用比例字体光栅化：小格下比例字体笔画会互相粘连（"测"只剩一根竖线）；
    尺寸演进：12x12(Fusion Pixel 10px) → 16x16(Unifont 16px) → **14x14(文泉驿点阵 14px)**（用户要求缩小到 14）
    覆盖实测（对 3776 字集）：
      wenquanyi_13px @14 : 缺 0  ← 采用（注意：这个 PCF 只能用 size=14 载入）
      Unifont 16px       : 缺 0（16x16 时代用过）
      Fusion Pixel 10px  : 缺 0（12x12 时代用过）
      Ark Pixel 10px: 缺 3153 ✗   Ark Pixel 12px: 缺 172 ✗
    字体文件：wenquanyi_13px.pcf（文泉驿点阵宋体，GPL-2.0+，来自 Debian xfonts-wqy 1.0.0~rc1-8）
      本地留档 ~/2-projects/Lora/共用/工具脚本/fonts/wenquanyi_13px.pcf
      sha256 94e7a303843a8a33d485a635c13907790e38ce403bf318a1c1b507ee6913aabe
      同源备选：wenquanyi_10pt@13 / _11pt@15 / _12pt@16（同一套字形的不同点阵尺寸）
    可用环境变量覆盖：CJK_TTF / CJK_SIZE / CJK_OX / CJK_OY / CJK_CELL
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

TTF = os.environ.get(
    "CJK_TTF", os.path.expanduser("~/2-projects/Lora/共用/工具脚本/fonts/wenquanyi_13px.pcf"))
CELL = int(os.environ.get("CJK_CELL", "14"))
W = int(os.environ.get("CJK_W", str(CELL)))
H = int(os.environ.get("CJK_H", str(CELL)))
SIZE = int(os.environ.get("CJK_SIZE", str(CELL)))  # 点阵字体按格子像素渲染才是 1:1
OX = int(os.environ.get("CJK_OX", "0"))
OY = int(os.environ.get("CJK_OY", "0"))
RASTER = (H + 7) // 8          # 每列字节数
STRIDE = W * RASTER            # 每字字节数

OUT = sys.argv[1] if len(sys.argv) > 1 else "src/graphics/fonts/CJKBitmapFont.cpp"

font = ImageFont.truetype(TTF, SIZE)

chars = []
# ★ 2026-09-19：一级（3776）→ **GB2312 全集（一、二级 + 符号区）**。
#   一级只含最常用字，二级的 3008 个字（很多是人名用字：甯珺玥喆晟昊淼…）会缺，
#   缺字时会掉进 ASCII 分支 ⇒ 3 个 UTF-8 字节被逐个当拉丁字符画出来（“é”那种乱码）。
for hi in range(0xA1, 0xF8):
    for lo in range(0xA1, 0xFF):
        try:
            ch = bytes([hi, lo]).decode('gb2312')
        except UnicodeDecodeError:
            continue
        if len(ch) == 1:
            chars.append(ch)
for ch in "，。！？、；：（）《》【】“”‘’—…·　":
    chars.append(ch)
cps = sorted({ord(c) for c in chars})


def _bmp(ch):
    img = Image.new("1", (W, H), 0)
    ImageDraw.Draw(img).text((OX, OY), ch, font=font, fill=1)
    return img.tobytes()


BLANK = bytes(W * RASTER)  # 全空白
missing = []
for cp in cps:
    if chr(cp).isspace():   # 空白字符本来就该是空白，不算缺字
        continue
    if _bmp(chr(cp)) == BLANK:
        missing.append(cp)
if missing:
    print("⚠️ 缺字 %d 个：%s" % (len(missing), "".join(chr(c) for c in missing[:60])), file=sys.stderr)
else:
    print("缺字体检：0 缺字 ✓（已排除空白字符）", file=sys.stderr)

bitmaps = bytearray()
for cp in cps:
    img = Image.new("1", (W, H), 0)
    ImageDraw.Draw(img).text((OX, OY), chr(cp), font=font, fill=1)
    px = img.load()
    for x in range(W):
        for band in range(RASTER):
            b = 0
            for k in range(8):
                y = band * 8 + k
                if y < H and px[x, y]:
                    b |= 1 << k
            bitmaps.append(b)

# "tofu"：表里没收录的字统一画这个空心方框（比掉进 ASCII 分支画出 "é" 清楚得多）
tofu = bytearray()
for x in range(W):
    for band in range(RASTER):
        b = 0
        for k in range(8):
            y = band * 8 + k
            if y < H and (x == 0 or x == W - 1 or y == 0 or y == H - 1):
                b |= 1 << k
        tofu.append(b)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    f.write("// 自动生成（tools/gen_cjk_font.py）：GB2312 一级常用字 %d 个，%dx%d，列优先位图（每字 %d 字节）\n"
            % (len(cps), W, H, STRIDE))
    f.write("// C++ 下 const 全局默认内部链接，必须用 extern 才能被库（OLEDDisplay.cpp）引用\n")
    f.write("// 字模来源：文泉驿点阵宋体 wenquanyi_13px.pcf @14px（Debian xfonts-wqy）\n")
    f.write("//   参数 SIZE=%d OX=%d OY=%d  ⇒ 1:1 无缩放，复杂字不粘连\n" % (SIZE, OX, OY))
    f.write("// ⚠ 格子尺寸必须与构建宏 CJK_W/CJK_H/CJK_STRIDE 一致（见 src/graphics/CjkGlyph.h）\n")
    f.write("#include <stdint.h>\n#include <pgmspace.h>\n\n")
    f.write('extern "C" const uint16_t cjk_count = %d;\n' % len(cps))
    f.write('extern "C" const uint16_t cjk_codes[%d] PROGMEM = {\n' % len(cps))
    for i in range(0, len(cps), 16):
        f.write("  " + ",".join("0x%04X" % c for c in cps[i:i + 16]) + ",\n")
    f.write("};\n\n")
    f.write('extern "C" const uint8_t cjk_bitmaps[%d] PROGMEM = {\n' % len(bitmaps))
    for i in range(0, len(bitmaps), 16):
        f.write("  " + ",".join("0x%02X" % b for b in bitmaps[i:i + 16]) + ",\n")
    f.write("};\n\n")
    f.write('// 缺字占位（空心方框）：表里没收录的字画这个，而不是让 UTF-8 字节掉进 ASCII 分支\n')
    f.write('extern "C" const uint8_t cjk_tofu[%d] PROGMEM = {\n' % len(tofu))
    for i in range(0, len(tofu), 16):
        f.write("  " + ",".join("0x%02X" % b for b in tofu[i:i + 16]) + ",\n")
    f.write("};\n")

print("字形 %d 个；字模 %.1f KB；码表 %.1f KB；总 %.1f KB -> %s" % (
    len(cps), len(bitmaps) / 1024, len(cps) * 2 / 1024,
    (len(bitmaps) + len(cps) * 2) / 1024, OUT), file=sys.stderr)
