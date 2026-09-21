// ============================================================================
//  Lora_C3_v1.4（meshcn 社区 DIY 板）—— 按用户要求：**基于现成变体魔改**，不从零写
// ----------------------------------------------------------------------------
//  底座（电台/结构）：variants/esp32c3/heltec_esp32c3（Heltec HT-CT62）
//      —— 它的电台引脚与我们这块板**完全一致**：SCK 10 / MISO 6 / MOSI 7 / CS 8 / DIO1 3 / BUSY 4 / RESET 5
//  屏参数模板：variants/nrf52840/heltec_mesh_node_t096（同为 0.96" ST7735）
//      —— TFT_WIDTH 80 / TFT_HEIGHT 160 / OFFSET_X 24 / OFFSET_Y 0 / TFT_INVERT false
//  相对底座的**三处魔改**：
//      ① 本板 RF 开关是 GPIO 控制的 RXEN(GPIO12)，不是 DIO2 → 去掉 SX126X_DIO2_AS_RF_SWITCH
//      ② 本板没有 LED（底座把 GPIO2 当 LED 用）→ 去掉 LED_POWER，GPIO2 让给电池 ADC
//      ③ 串口走 C3 原生 USB（非 CH340）→ 需 ARDUINO_USB_CDC_ON_BOOT（在 platformio.ini 里）
//  引脚取证：厂商 2.6.9 固件启动日志 + 固件反汇编（见 ~/2-projects/Lora/gerber_extract/GPIO_mapping_report.md §7）
// ============================================================================
#pragma once

// ---------------------------------------------------------------- 按键
#define BUTTON_PIN 9 // BOOT 键当用户键（实测可切界面）

// ---------------------------------------------------------------- 屏幕 ST7735S 0.96" 160x80
#define HAS_SCREEN 1
#define USE_TFTDISPLAY 1 // 必需！否则 TFTDisplay.cpp 不参与编译 → 链接报 undefined reference
#define SCREEN_ROTATE
#define SCREEN_TRANSITION_FRAMERATE 3 // fps（2026-09-19：照抄上游 t096/t1 同款 80x160 面板；
                                        // 缺这两条会导致 UI 按错误坐标空间排版 → 全挤左上角+重叠）
#define DISPLAY_FORCE_SMALL_FONTS // 80px 宽的板子用小字体（照抄 t096）
#define ST7735S 1
#define ST7735_CS 1
#define ST7735_RS 0     // DC
#define ST7735_SDA 7    // MOSI（与电台共用同一对 SPI 线）
#define ST7735_SCK 10   // 与电台共用
#define ST7735_RESET -1 // 板上直接接 3V3，没有复位脚
#define ST7735_MISO 6   // 2026-09-18 21:3x 修复：与电台共用 SPI2 时必须给出 MISO(=IO6)，
                         // 否则屏先初始化会把 MISO 置 -1，电台读不到芯片应答 → SX126x init result -2  // ST7735 无 MISO
#define ST7735_BUSY -1
#define TFT_BL 13
#define TFT_BACKLIGHT_ON HIGH
#define ST7735_SPI_HOST SPI2_HOST // C3 只有 SPI2（=FSPI），与电台同一 host
#define SPI_FREQUENCY 40000000
#define SPI_READ_FREQUENCY 16000000
#define TFT_WIDTH 80        // ← 0.96" 原生竖屏 80x160（比我之前猜的 160x80 靠谱）
#define TFT_HEIGHT 160
#define TFT_OFFSET_X 26   // 标准 80x160 横屏（rowstart=26）
#define TFT_OFFSET_Y 1    // 标准值（colstart=1）
#define TFT_INVERT false // ★2026-09-19 10:0x 反色修复：true 时黑底被反成白底（用户实测「背景是白色的」）。
                          // 对照依据：同款 0.96" ST7735 上游模板 variants/nrf52840/heltec_mesh_node_t096 用 false；
                          // 注意 true/false 都能点亮，所以之前误判成「true 颜色正常」（黑屏真因是全擦清空 NVS）。

// ---------------------------------------------------------------- 电台 E22-400M22S (SX1268)
// 2026-09-18 08:12 单变量测试：本板模块是 E22-400M22S(SX1268 内核)，RadioLib 会校验型号
// ★ 2026-09-18 09:55 修复电台 init -2 / critical error 3 —— 最终方案（取证报告 方案B）
//   症状：串口报 'SX126X_DIO3_TCXO_VOLTAGE not defined, not using DIO3 as TCXO reference voltage'
//         → 'SX126x init result -2' → 'critical error 3' → 进不了系统
//   根因：只定义 USE_SX1268 时，RadioInterface.cpp 的 SX1268 分支其 TCXO 路径
//         额外要求 TCXO_OPTIONAL（见 RadioInterface.cpp L379 的 #if defined(TCXO_OPTIONAL)）。
//         我们没定义 ⇒ 只编出「无 TCXO 直连」一条路 ⇒ 本模块必需的 DIO3 1.8V TCXO 从未启用
//         ⇒ 晶振不起振 ⇒ 读不回 0x0320 版本串 ⇒ findChip 10 次全失败 ⇒ -2
//   修复：platformio.ini 加 -D TCXO_OPTIONAL=1，使 L379 分支编译进去。
//   ⚠️ 不要改用 USE_SX1262：RadioLib 的 SX1262 类期望版本串 "SX1261"
//      (SX1262.h:16 RADIOLIB_SX1262_CHIP_TYPE)，而本模块返回 "SX1268"，型号校验必失败。
//      保留 SX1268 类才能通过 findChip 的 strncmp(verStr, version, 6) 比对。
//   时序确认：SX126x::begin() 里 findChip() 在前、setTCXO() 在后(L1442→L1452)。
//   详见 04-诊断记录/2026-09-18-C3-电台CHIP_NOT_FOUND-根因取证.md
#define USE_SX1268
#define LORA_SCK 10
#define LORA_MISO 6
#define LORA_MOSI 7
#define LORA_CS 8
#define LORA_DIO0 RADIOLIB_NC
#define LORA_RESET 5
#define LORA_DIO1 3
#define LORA_DIO2 RADIOLIB_NC
#define LORA_BUSY 4
#define SX126X_CS LORA_CS
#define SX126X_DIO1 LORA_DIO1
#define SX126X_BUSY LORA_BUSY
#define SX126X_RESET LORA_RESET
// 2026-09-18 08:07 按【厂商固件反汇编】证据修正（GPIO_mapping_report.md §7.3）：
//   厂商配置 = NSS=IO8 · BUSY=IO4 · DIO1=IO3 · NRST=IO5 · RXEN=IO12 · TXEN=无（且不用 DIO2 做 RF 开关）
//   ⇒ 恢复为 RXEN=12 / TXEN=NC、不定义 DIO2_AS_RF_SWITCH（上一轮改成 DIO2 是错的）
#define SX126X_RXEN 12
#define SX126X_TXEN RADIOLIB_NC
#define SX126X_DIO3_TCXO_VOLTAGE 1.8

// ---------------------------------------------------------------- 电池
// 2×100K 分压中点 → GPIO2
// 2026-09-19 更正：这两个分压电阻【已焊】⇒ 电量读数真实可信（原注释"没焊、读数无意义"已失效）
//   实测依据：4187 mV ÷ 2.0 = 2093 mV，与 4.19V 电池经 2×100K 分压的一半完全自洽；
//             用户确认电阻已焊，且当前无假报充电现象
#define BATTERY_PIN 2
#define ADC_CHANNEL ADC1_GPIO2_CHANNEL
// 2026-09-21 校准：2.0 → 2.017
//   依据：同一状态下的【万用表 4.145V vs 屏幕 4.11V】⇒ 比值 1.00852 ⇒ 2.0 × 1.00852 = 2.017
//   ⚠️ 比值与“满不满”无关（只补偿分压电阻 1% 容差 / ADC 刻度），所以那一次并非满电也能用 ✓
//   真满电静置 = 4.180V（两块电池万用表实测）—— 那是【阈值】的依据，见 src/power.h 的 OCV_ARRAY
//   注意：仍可用运行时偏好覆盖（power.adc_multiplier_override，见 Power.cpp:320）
#define ADC_MULTIPLIER 2.017

// ---------------------------------------------------------------- GPS（选配 ATGM336H，5P 排针 VCC/GND/TX/RX/PPS）
// 引脚：暂定 RX=21（ESP 收 ← 模块 TX）/ TX=20（ESP 发 → 模块 RX）
//   依据：① 厂商固件里 GPS RX 字段的默认值是 21 ② 板上丝印疑似 “TX21/RX20”
//   PPS 是孤立焊盘、没接到 ESP（Gerber 已证）
// ⚠️ 未实锤：若日志显示 GPS 没数据/没卫星，说明这对引脚（或 RX/TX 方向）要换
// 对齐商家固件：GPS 功能照开（模块没插时它会报 “No GNSS Module”，跟原厂一样）
// ★ 2026-09-21：用户已焊好 5P 母座，要实测 GPS ⇒ 打开 HAS_GPS 并给出引脚
//   注意：ESP32 平台默认本身就是 HAS_GPS=1（src/platform/esp32/architecture.h:22），
//   之前是本变体显式写 0 + #undef 引脚 ⇒ GPS 驱动虽被编译（GPS.cpp.o 生成）
//   但无人引用、链接时被 GC 裁掉 ⇒ 旧固件里 PCA/PMTK/GNSS/L76K 等字符串 0 命中
#define HAS_GPS 1
#define GPS_RX_PIN 21   // ESP 的 RX ← 模块的 TX（板侧丝印 “TX” 那一脚）
#define GPS_TX_PIN 20   // ESP 的 TX → 模块的 RX
// 不定义 GPS_DEFAULT_NOT_PRESENT ⇒ 默认 gps_mode 落到 ENABLED（NodeDB.cpp:677-686）
// 波特率用默认 9600（ATGM336H 默认，探测第一档就中）
