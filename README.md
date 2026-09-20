# Lora_C3_v1.4（ESP32-C3）自定义固件 —— 中文显示版

> 基于 **Meshtastic firmware v2.7.26** 的**个人定制分支** ✓
> 目标硬件：**Lora_C3_v1.4** 自制小板（ESP32-C3 + E22-400M22S + ST7735S 0.96" 屏）

## 这个分支做了什么

| 方向 | 内容 |
|---|---|
| **中文显示** | 接入 CJK 点阵渲染（14×14 · GB2312 全字库 7447 字 ✓）|
| **中英混排换行** | 修复"一个汉字被断成两半" ✗：原换行按**字节**循环（中文是 3 字节 UTF-8）⇒ 改为**整字符边界**断行 ✓（英文仍优先断在空格 ✓）|
| **显存/分区** | 全字库 208KB 装不下默认 app 槽 ⇒ 改用 no-ota 分区表把 app 扩到 `0x2F0000` ✓ |
| **显示修正** | 反色修正（`TFT_INVERT false` ✓）· 屏偏移修正（顶部花屏 ✗）· 字模尺寸与行距成套一致 ✓ |
| **稳定** | flash 模式必须 `dout` ✓（否则 LittleFS 挂载/格式化全失败 ✗）；降发射功率治 WiFi `AUTH_EXPIRE` ✓ |
| **开箱即用** | CN 区域 / LONG_FAST / 频点1 / 时区 CST-8 / 位置精度 32 ✓ |

## 硬件（本分支适配的板子）

- ESP32-C3 核心板 + 亿百特 **E22-400M22S**（LoRa；**必须**由 DIO3 供 1.8V 给 TCXO ✓ 否则电台不起振）
- ST7735S 0.96" **160×80** 屏（与电台**共用 SPI** 线 ✗ 需注意）
- 无 GPS（预留 5Pin 接口）· **无 I²C 器件**（无 RTC/传感器 ✓）
- 按键 BOOT(GPIO9) · 电池检测 GPIO2 · 背光 GPIO13

## 构建

```bash
cd <repo>
/home/x1000qaq/.pio-venv/bin/pio run -e lora-c3     # 或用你本机的 pio
```

产物：`.pio/build/lora-c3/firmware-lora-c3-<版本>.<git短哈希>.bin`
⚠️ 构建目录里同时有 `.factory.bin` / `littlefs-*.bin` ⇒ 取产物**按名字精确匹配**，别用 `head -1` ✗

## 烧录（★ 与本项目的 S3 线**完全不同**）

**三种方式**（预编译固件见 [Releases](https://github.com/X1000QAQ/lora-c3-firmware/releases)）：

| 场景 | 用哪个 | 偏移 |
|---|---|---|
| **常规升级** | 整片 `…factory.bin` ★ 本板从一开始就写 `0x0` | `0x0` |
| **分件写** | `bootloader.bin` → `0x0`，`partitions.bin` → `0x8000`，应用 → `0x10000` | 各自偏移 |
| **只重写分区表** | `partitions.bin` | `0x8000` |

```bash
# 常规（推荐）
python -m esptool --chip esp32c3 --port <COM> write-flash 0x0 <factory.bin>
```

⚠️ **【绝对不要】erase-flash / 全擦** —— 会清空 NVS 配置，这正是历次"黑屏"的共同原因
⚠️ 本板串口走 **C3 原生 USB-Serial/JTAG**（非 CH340）

## 许可与致谢

- 基于 **Meshtastic firmware**（**GPLv3**）✓ ⇒ 本分支同样以 **GPLv3** 发布 ✓
  （见仓库根 `LICENSE`；上游原文见 `README-upstream.md`）
- 上游项目：https://github.com/meshtastic/firmware

### 特别致谢

- 本项目适配的硬件 **Lora_C3_v1.4**（ESP32-C3 + E22-400M22S + ST7735S）由
  **arkbird**（闲鱼）**自行设计并免费分享** ✓
  —— 他也是 LoRa 爱好者，把自制的 **S3（T-Deck）** 与 **C3（本板）** 两套小板
  连同配套资料一起分享给了我 ✓
- ⚠️ arkbird 提供的**原始固件为闭源** ✗ ⇒ **未包含在本仓库** ✓
  （本仓库只包含基于 Meshtastic 开源部分 + 我自己的修改 ✓）

## 免责

个人自用与学习目的 ✓ 请遵守当地无线电法规 ✓
