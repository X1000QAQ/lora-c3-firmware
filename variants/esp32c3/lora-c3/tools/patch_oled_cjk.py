#!/usr/bin/env python3
"""给 libdeps 里的 OLEDDisplay 打中文渲染补丁（幂等，v2：不用宏，全部内联）。

背景：OLEDDisplay::drawStringInternal() 只用 fontTableLookupFunction(byte)->uint8_t
做字形索引（≤256 字形），中文是 3 字节 UTF-8 + 几千字形，机制上渲染不了。
本补丁：3 字节 UTF-8 解码 + 在 cjk_codes[] 二分查找 + 用 drawInternal() 直接画字模。

用法：python3 patch_oled_cjk.py [OLEDDisplay.cpp 路径 | 项目根]
"""
import sys, glob, os, re

arg = sys.argv[1] if len(sys.argv) > 1 else "."
if arg.endswith("OLEDDisplay.cpp"):
    cands = [arg]
else:
    cands = glob.glob(os.path.join(arg, ".pio/libdeps/lora-c3/*OLED*SSD1306*/src/OLEDDisplay.cpp"))
    if not cands:
        cands = glob.glob(os.path.join(arg, ".pio/libdeps/*/*OLED*SSD1306*/src/OLEDDisplay.cpp"))
if not cands:
    sys.exit("找不到 OLEDDisplay.cpp（先跑一次 pio run 让 libdeps 落地）")
path = cands[0]
src = open(path, encoding="utf-8", errors="surrogateescape").read()
if "// ==== CJK patch" in src:
    print("已打过补丁，跳过：%s" % path)
    sys.exit(0)

HELPERS = """// ==== CJK patch (patch_oled_cjk.py) ====
#if CJK_FONT_ENABLED
#include <stdint.h>
#include <pgmspace.h>
#define CJK_W 12
#define CJK_H 12
#define CJK_STRIDE 24
extern "C" {
extern const uint16_t cjk_count;
extern const uint16_t cjk_codes[];
extern const uint8_t cjk_bitmaps[];
}
static inline int16_t cjkFind(uint32_t cp)
{
  int16_t lo = 0;
  int16_t hi = (int16_t)cjk_count - 1;
  while (lo <= hi) {
    int16_t mid = (int16_t)((lo + hi) >> 1);
    uint16_t v = pgm_read_word(&cjk_codes[mid]);
    if (v == cp)
      return mid;
    if (v < cp)
      lo = (int16_t)(mid + 1);
    else
      hi = (int16_t)(mid - 1);
  }
  return -1;
}
#endif
// ==== end CJK patch ====
"""

# 1) helper 插到最后一个“顶部区块”的 #include 之后（第一个 #if 之前的位置最稳：插在第一个 #include 之后）
m = re.search(r'^#include [^\n]*\n', src, re.M)
assert m, "没有 #include，补丁无法定位"
pos = m.end()
src = src[:pos] + HELPERS + src[pos:]

# 2) drawStringInternal
anchor = "    uint8_t code;\n    if (utf8) {\n      code = (this->fontTableLookupFunction)(text[j]);"
assert src.count(anchor) == 1, "drawStringInternal 锚点不唯一（%d）" % src.count(anchor)
insert = """#if CJK_FONT_ENABLED
    if (utf8 && ((uint8_t)text[j] & 0xF0) == 0xE0 && (j + 2) < textLength) {
      uint32_t cp = (((uint32_t)((uint8_t)text[j] & 0x0F)) << 12) |
                    (((uint32_t)((uint8_t)text[j + 1] & 0x3F)) << 6) |
                    ((uint32_t)((uint8_t)text[j + 2] & 0x3F));
      int16_t cjkIdx = cjkFind(cp);
      if (cjkIdx >= 0) {
        drawInternal(xPos, yPos, CJK_W, CJK_H, cjk_bitmaps, (uint16_t)(cjkIdx * CJK_STRIDE), CJK_STRIDE);
        cursorX += CJK_W;
        j += 2;
        continue;
      }
    }
#endif
"""
src = src.replace(anchor, insert + anchor, 1)

# 3) getStringWidth
anchor2 = "  for (uint16_t i = 0; i < length; i++) {\n    char c = text[i];"
assert src.count(anchor2) == 1, "getStringWidth 锚点不唯一（%d）" % src.count(anchor2)
insert2 = """  for (uint16_t i = 0; i < length; i++) {
#if CJK_FONT_ENABLED
    if (utf8 && ((uint8_t)text[i] & 0xF0) == 0xE0 && (i + 2) < length) {
      uint32_t cp = (((uint32_t)((uint8_t)text[i] & 0x0F)) << 12) |
                    (((uint32_t)((uint8_t)text[i + 1] & 0x3F)) << 6) |
                    ((uint32_t)((uint8_t)text[i + 2] & 0x3F));
      if (cjkFind(cp) >= 0) {
        stringWidth += CJK_W;
        i += 2;
        continue;
      }
    }
#endif
    char c = text[i];"""
src = src.replace(anchor2, insert2, 1)

open(path, "w", encoding="utf-8", errors="surrogateescape").write(src)
print("补丁已应用(v2)：%s" % path)
