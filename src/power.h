#pragma once
#include "PowerStatus.h"
#include "concurrency/OSThread.h"
#include "configuration.h"

#ifdef ARCH_ESP32
// "legacy adc calibration driver is deprecated, please migrate to use esp_adc/adc_cali.h and esp_adc/adc_cali_scheme.h
#include <esp_adc_cal.h>
#include <soc/adc_channel.h>
#endif

#ifndef NUM_OCV_POINTS
#define NUM_OCV_POINTS 11
#endif

// Device specific curves go in variant.h
#ifndef OCV_ARRAY
// Lora_C3_v1.4 专用（2026-09-21）：首项 4190 → 4170
//   为什么：表要求 ≥4.19V 才给 100%，而锂电的 4.2V 是【充电截止】电压，
//   静置回落（relaxation）后永远达不到 → 实测两块电池【真满电静置】万用表均为 4.180V ⇒ 原表永远 96~99% ✗
//   现把 100% 阈值定在 4170mV（= 真满 4180mV 留 10mV 余量，抗 ADC 抖动）✓
//   ⚠️ 区分两件事：【校准】看同一状态下的比值（与满不满无关）；【阈值】才看真满电压
//      之前记的 4.145V 是「没充满」的状态，不能用来定阈值 ✓
//   影响范围：仅本树（C3）；S3 树是另一份副本、不受影响 ✓
//   中低段（4050 及以下）保持上游原值不动 ✓
#define OCV_ARRAY 4170, 4050, 3990, 3890, 3800, 3720, 3630, 3530, 3420, 3300, 3100
#endif

/*Note: 12V lead acid is 6 cells, most board accept only 1 cell LiIon/LiPo*/
#ifndef NUM_CELLS
#define NUM_CELLS 1
#endif

#ifdef BAT_MEASURE_ADC_UNIT
extern RTC_NOINIT_ATTR uint64_t RTC_reg_b;
#include "soc/sens_reg.h" // needed for adc pin reset
#endif

#if HAS_TELEMETRY && !MESHTASTIC_EXCLUDE_ENVIRONMENTAL_SENSOR
#include "modules/Telemetry/Sensor/nullSensor.h"
#if __has_include(<Adafruit_INA219.h>)
#include "modules/Telemetry/Sensor/INA219Sensor.h"
extern INA219Sensor ina219Sensor;
#else
extern NullSensor ina219Sensor;
#endif

#if __has_include(<INA226.h>)
#include "modules/Telemetry/Sensor/INA226Sensor.h"
extern INA226Sensor ina226Sensor;
#else
extern NullSensor ina226Sensor;
#endif

#if __has_include(<Adafruit_INA260.h>)
#include "modules/Telemetry/Sensor/INA260Sensor.h"
extern INA260Sensor ina260Sensor;
#else
extern NullSensor ina260Sensor;
#endif

#if __has_include(<INA3221.h>)
#include "modules/Telemetry/Sensor/INA3221Sensor.h"
extern INA3221Sensor ina3221Sensor;
#else
extern NullSensor ina3221Sensor;
#endif

#endif

#if HAS_TELEMETRY && !MESHTASTIC_EXCLUDE_ENVIRONMENTAL_SENSOR
#if __has_include(<Adafruit_MAX1704X.h>)
#include "modules/Telemetry/Sensor/MAX17048Sensor.h"
extern MAX17048Sensor max17048Sensor;
#else
extern NullSensor max17048Sensor;
#endif
#endif

#if HAS_TELEMETRY && !MESHTASTIC_EXCLUDE_ENVIRONMENTAL_SENSOR && HAS_RAKPROT
#include "modules/Telemetry/Sensor/RAK9154Sensor.h"
extern RAK9154Sensor rak9154Sensor;
#endif

#ifdef HAS_PMU
#include "XPowersAXP192.tpp"
#include "XPowersAXP2101.tpp"
#include "XPowersLibInterface.hpp"
extern XPowersLibInterface *PMU;
#endif

class Power : public concurrency::OSThread
{

  public:
    Observable<const meshtastic::PowerStatus *> newStatus;

    Power();

    void powerCommandsCheck();
    void readPowerStatus();
    virtual bool setup();
    virtual int32_t runOnce() override;
    void setStatusHandler(meshtastic::PowerStatus *handler) { statusHandler = handler; }
    const uint16_t OCV[11] = {OCV_ARRAY};

#ifdef ARCH_ESP32
    int beforeLightSleep(void *unused);
    int afterLightSleep(esp_sleep_wakeup_cause_t cause);
#endif

    void attachPowerInterrupts();
    void detachPowerInterrupts();

  protected:
    meshtastic::PowerStatus *statusHandler;

    /// Setup a xpowers chip axp192/axp2101, return true if found
    bool axpChipInit();
    /// Setup a simple ADC input based battery sensor
    bool analogInit();
    /// Setup cw2015 battery level sensor
    bool cw2015Init();
    /// Setup a 17048 battery level sensor
    bool max17048Init();
    /// Setup a Lipo charger
    bool lipoChargerInit();
    /// Setup a meshSolar battery sensor
    bool meshSolarInit();
    /// Setup a serial battery sensor
    bool serialBatteryInit();

  private:
    void shutdown();
    void reboot();
    // open circuit voltage lookup table
    uint8_t low_voltage_counter;
    uint32_t lastLogTime = 0;

#ifdef ARCH_ESP32
    // Get notified when lightsleep begins and ends
    CallbackObserver<Power, void *> lsObserver = CallbackObserver<Power, void *>(this, &Power::beforeLightSleep);
    CallbackObserver<Power, esp_sleep_wakeup_cause_t> lsEndObserver =
        CallbackObserver<Power, esp_sleep_wakeup_cause_t>(this, &Power::afterLightSleep);
#endif

#ifdef DEBUG_HEAP
    uint32_t lastheap;
#endif
};

void battery_adcEnable();

extern Power *power;
