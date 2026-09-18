// 最小变体：只留电台 + USB CDC（砍掉屏 / GPS / 电池 / 按键之外的干扰）
// 用途：二分定位"上电重启循环"到底是哪一块引起的
#pragma once

#define HAS_SCREEN 0
#define USE_TFTDISPLAY 0
#define HAS_GPS 0

#define BUTTON_PIN 9

#define USE_SX1262
#define LORA_SCK 10
#define LORA_MISO 6
#define LORA_MOSI 7
#define LORA_CS 8

#define SX126X_CS LORA_CS
#define SX126X_DIO1 3
#define SX126X_BUSY 4
#define SX126X_RESET 5
#define SX126X_RXEN 12
#define SX126X_TXEN RADIOLIB_NC
#define SX126X_DIO3_TCXO_VOLTAGE 1.8
#define SX126X_MAX_POWER 22
