#!/usr/bin/env python3
"""给 libdeps 里的 OLEDDisplay 打中文渲染补丁（幂等 v5：尺寸走构建宏 + 偏移走指针 + 缺字画方框）。

背景：OLEDDisplay::drawStringInternal() 只用 fontTableLookupFunction(byte)->uint8_t
做字形索引（≤256 字形），中文是 3 字节 UTF-8 + 几千字形，机制上渲染不了。
本补丁：3 字节 UTF-8 解码 + 在 cjk_codes[] 二分查找 + 用 drawInternal() 直接画字模。

版本变化：
  v3  字模格尺寸不再写死 12x12，改用构建宏 CJK_W/CJK_H/CJK_STRIDE（见 src/graphics/CjkGlyph.h）
  v4  修"认错字"：drawInternal 的 offset 形参是 uint16_t，3776 字 × STRIDE 会溢出截断
      ⇒ 改成指针运算 `cjk_bitmaps + (uint32_t)idx * CJK_STRIDE`、offset 传 0
  v5  修"中文显示成 é 这类拉丁乱码"：**表里没有这个字**时原样掉进下面的 ASCII 分支，
      3 个 UTF-8 字节被逐个当拉丁字符画出来 ⇒ 现在改画空心方框（cjk_tofu），宽度仍算一个字宽

已存在旧版补丁时会**原地升级**（helper 块 + 调用点）。
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

HELPERS = """// ==== CJK patch (patch_oled_cjk.py v5) ====
#if CJK_FONT_ENABLED
#include <stdint.h>
#include <pgmspace.h>
// 字模格尺寸：由构建宏注入（必须与 gen_cjk_font.py 生成的字模一致），默认 12x12
#ifndef CJK_W
#define CJK_W 12
#endif
#ifndef CJK_H
#define CJK_H 12
#endif
#ifndef CJK_STRIDE
#define CJK_STRIDE (CJK_W * ((CJK_H + 7) / 8))
#endif
extern "C" {
extern const uint16_t cjk_count;
extern const uint16_t cjk_codes[];
extern const uint8_t cjk_bitmaps[];
extern const uint8_t cjk_tofu[]; // 未收录字的占位方框
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

MARK_START = "// ==== CJK patch"
MARK_END = "// ==== end CJK patch ====\n"

NEW_DRAW = """      int16_t cjkIdx = cjkFind(cp);
      if (cjkIdx >= 0) {
        // ★ 偏移走指针：drawInternal 的 offset 形参是 uint16_t，字模表远超 65535，
        //   用整数偏移会被截断取错字形（历史上就是这么错的）。
        drawInternal(xPos, yPos, CJK_W, CJK_H, cjk_bitmaps + (uint32_t)cjkIdx * CJK_STRIDE, 0, CJK_STRIDE);
      } else {
        // ★ 表里没有这个字：画空心方框（tofu）。绝不能让它掉进下面的 ASCII 分支 ——
        //   那样 3 个 UTF-8 字节会被逐个当拉丁字符画出来（显示成 é 之类的乱码）。
        drawInternal(xPos, yPos, CJK_W, CJK_H, cjk_tofu, 0, CJK_STRIDE);
      }
      cursorX += CJK_W;
      j += 2;
      continue;
"""

OLD_DRAW_V4 = """      int16_t cjkIdx = cjkFind(cp);
      if (cjkIdx >= 0) {
        drawInternal(xPos, yPos, CJK_W, CJK_H, cjk_bitmaps + (uint32_t)cjkIdx * CJK_STRIDE, 0, CJK_STRIDE);
        cursorX += CJK_W;
        j += 2;
        continue;
      }
"""

OLD_DRAW_V3 = """      int16_t cjkIdx = cjkFind(cp);
      if (cjkIdx >= 0) {
        drawInternal(xPos, yPos, CJK_W, CJK_H, cjk_bitmaps, (uint16_t)(cjkIdx * CJK_STRIDE), CJK_STRIDE);
        cursorX += CJK_W;
        j += 2;
        continue;
      }
"""

NEW_WIDTH = """      // 找到与否都按一个字宽计（未收录的字会画成 tofu 方框，占位宽度一致）
      stringWidth += CJK_W;
      i += 2;
      continue;
"""

OLD_WIDTH_V4 = """      if (cjkFind(cp) >= 0) {
        stringWidth += CJK_W;
        i += 2;
        continue;
      }
"""

if MARK_START in src:
    start = src.index(MARK_START)
    end = src.index(MARK_END) + len(MARK_END)
    old_block = src[start:end]
    need_draw = OLD_DRAW_V4 in src or OLD_DRAW_V3 in src
    need_width = OLD_WIDTH_V4 in src
    if "patch_oled_cjk.py v5" in old_block and not need_draw and not need_width:
        print("已是 v5，跳过：%s" % path)
        sys.exit(0)
    src = src[:start] + HELPERS + src[end:]
    if OLD_DRAW_V4 in src:
        src = src.replace(OLD_DRAW_V4, NEW_DRAW, 1)
    elif OLD_DRAW_V3 in src:
        src = src.replace(OLD_DRAW_V3, NEW_DRAW, 1)
    if OLD_WIDTH_V4 in src:
        src = src.replace(OLD_WIDTH_V4, NEW_WIDTH, 1)
    open(path, "w", encoding="utf-8", errors="surrogateescape").write(src)
    print("补丁已就地升级到 v5：%s" % path)
    sys.exit(0)

# --- 首次打补丁 ---
m = re.search(r'^#include [^\n]*\n', src, re.M)
assert m, "没有 #include，补丁无法定位"
pos = m.end()
src = src[:pos] + HELPERS + src[pos:]

anchor = "    uint8_t code;\n    if (utf8) {\n      code = (this->fontTableLookupFunction)(text[j]);"
assert src.count(anchor) == 1, "drawStringInternal 锚点不唯一（%d）" % src.count(anchor)
insert = """#if CJK_FONT_ENABLED
    if (utf8 && ((uint8_t)text[j] & 0xF0) == 0xE0 && (j + 2) < textLength) {
      uint32_t cp = (((uint32_t)((uint8_t)text[j] & 0x0F)) << 12) |
                    (((uint32_t)((uint8_t)text[j + 1] & 0x3F)) << 6) |
                    ((uint32_t)((uint8_t)text[j + 2] & 0x3F));
""" + NEW_DRAW + """    }
#endif
"""
src = src.replace(anchor, insert + anchor, 1)

anchor2 = "  for (uint16_t i = 0; i < length; i++) {\n    char c = text[i];"
assert src.count(anchor2) == 1, "getStringWidth 锚点不唯一（%d）" % src.count(anchor2)
insert2 = """  for (uint16_t i = 0; i < length; i++) {
#if CJK_FONT_ENABLED
    if (utf8 && ((uint8_t)text[i] & 0xF0) == 0xE0 && (i + 2) < length) {
      uint32_t cp = (((uint32_t)((uint8_t)text[i] & 0x0F)) << 12) |
                    (((uint32_t)((uint8_t)text[i + 1] & 0x3F)) << 6) |
                    ((uint32_t)((uint8_t)text[i + 2] & 0x3F));
      (void)cp;
""" + NEW_WIDTH + """    }
#endif
    char c = text[i];"""
src = src.replace(anchor2, insert2, 1)

open(path, "w", encoding="utf-8", errors="surrogateescape").write(src)
print("补丁已应用(v5)：%s" % path)
