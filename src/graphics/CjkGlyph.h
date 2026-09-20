#pragma once
// 中文字模格的尺寸 —— 单一事实来源。
//
// 为什么要有这个头：中文字模是**点阵位图**，格子大小（像素）必须和
// 1) 生成器 gen_cjk_font.py 吐出的字模、
// 2) 给 OLEDDisplay 打的中文补丁（tools/patch_oled_cjk.py 里的 CJK_W/CJK_H/CJK_STRIDE）、
// 3) 各渲染器的**行距**（见 LINE_HEIGHT_CJK）
// 三处完全一致，否则会出现「字的下半部分被下一行盖掉」或字形错位。
// 具体数值用构建宏注入（variants/esp32c3/lora-c3/platformio.ini 的 -D CJK_W/CJK_H/CJK_STRIDE）。

#if CJK_FONT_ENABLED
#ifndef CJK_W
#define CJK_W 12 // 字宽（像素）
#endif
#ifndef CJK_H
#define CJK_H 12 // 字高（像素）
#endif
#ifndef CJK_STRIDE
#define CJK_STRIDE 24 // 每字字节数 = CJK_W * ceil(CJK_H/8)
#endif

// ★ 行距下限：中文字模格比 ASCII 小字体高 ⇒ 按行排布文本的地方，
// 行距必须取 max(原有步进, CJK_H)，否则中文会被下一行盖住下半部分
// （历史坑：字模 12 行而行距只有 FONT_HEIGHT_SMALL-3=10 ⇒ 底部约 20% 被吃掉）。
#define LINE_HEIGHT_CJK(base) (((base) > CJK_H) ? (base) : CJK_H)
#else
#define LINE_HEIGHT_CJK(base) (base)
#endif
