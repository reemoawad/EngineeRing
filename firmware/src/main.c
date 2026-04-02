/*
 * Copyright (c) 2018 Nordic Semiconductor ASA
 *
 * SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
 */

/** @file
 *  @brief Nordic UART Bridge Service (NUS) sample
 */

#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>
LOG_MODULE_REGISTER(main);

#include <zephyr/types.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <soc.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>

#include <bluetooth/services/nus.h>

#include <dk_buttons_and_leds.h>

#include <zephyr/settings/settings.h>

#include <stdio.h>
#include <string.h>

#include <zephyr/logging/log.h>

#include <zephyr/kernel.h>
#include <zephyr/drivers/spi.h>


#define WHO_AM_I       0x00 // Expecting 0XEA for reset value
#define USER_CTRL             0x03
#define LP_CONFIG             0x05
#define PWR_MGMT_1            0x06
#define PWR_MGMT_2            0x07
#define INT_PIN_CFG           0x0F
#define INT_ENABLE            0x10
#define INT_ENABLE_1          0x11
#define INT_ENABLE_2          0x12
#define INT_ENABLE_3          0x13
#define I2C_MST_STATUS        0x17
#define INT_STATUS            0x19
#define INT_STATUS_1          0x1A
#define INT_STATUS_2          0x1B
#define INT_STATUS_3          0x1C
#define DELAY_TIMEH           0x28
#define DELAY_TIMEL           0x29
#define ACCEL_XOUT_H          0x2D
#define ACCEL_XOUT_L          0x2E
#define ACCEL_YOUT_H          0x2F
#define ACCEL_YOUT_L          0x30
#define ACCEL_ZOUT_H          0x31
#define ACCEL_ZOUT_L          0x32
#define GYRO_XOUT_H           0x33
#define GYRO_XOUT_L           0x34
#define GYRO_YOUT_H           0x35
#define GYRO_YOUT_L           0x36
#define GYRO_ZOUT_H           0x37
#define GYRO_ZOUT_L           0x38
#define TEMP_OUT_H            0x39
#define TEMP_OUT_L            0x3A
#define EXT_SLV_SENS_DATA_00  0x3B
#define EXT_SLV_SENS_DATA_01  0x3C
#define EXT_SLV_SENS_DATA_02  0x3D
#define EXT_SLV_SENS_DATA_03  0x3E
#define EXT_SLV_SENS_DATA_04  0x3F
#define EXT_SLV_SENS_DATA_05  0x40
#define EXT_SLV_SENS_DATA_06  0x41
#define EXT_SLV_SENS_DATA_07  0x42
#define EXT_SLV_SENS_DATA_08  0x43
#define EXT_SLV_SENS_DATA_09  0x44
#define EXT_SLV_SENS_DATA_10  0x45
#define EXT_SLV_SENS_DATA_11  0x46
#define EXT_SLV_SENS_DATA_12  0x47
#define EXT_SLV_SENS_DATA_13  0x48
#define EXT_SLV_SENS_DATA_14  0x49
#define EXT_SLV_SENS_DATA_15  0x4A
#define EXT_SLV_SENS_DATA_16  0x4B
#define EXT_SLV_SENS_DATA_17  0x4C
#define EXT_SLV_SENS_DATA_18  0x4D
#define EXT_SLV_SENS_DATA_19  0x4E
#define EXT_SLV_SENS_DATA_20  0x4F
#define EXT_SLV_SENS_DATA_21  0x50
#define EXT_SLV_SENS_DATA_22  0x51
#define EXT_SLV_SENS_DATA_23  0x52
#define FIFO_EN_1             0x66
#define FIFO_EN_2             0x67
#define FIFO_RST              0x68
#define FIFO_MODE             0x69
#define FIFO_COUNTH           0x70
#define FIFO_COUNTL           0x71
#define FIFO_R_W              0x72
#define DATA_RDY_STATUS       0x74
#define FIFO_CFG              0x76
#define REG_BANK_SEL          0x7F

#define SELF_TEST_X_GYRO   0x02
#define SELF_TEST_Y_GYRO   0x03
#define SELF_TEST_Z_GYRO   0x04
#define SELF_TEST_X_ACCEL  0x0E
#define SELF_TEST_Y_ACCEL  0x0F
#define SELF_TEST_Z_ACCEL  0x10
#define XA_OFFSET_H     0x14
#define XA_OFFSET_L     0x15
#define YA_OFFSET_H     0x17
#define YA_OFFSET_L     0x18
#define ZA_OFFSET_H     0x1A
#define ZA_OFFSET_L     0x1B
#define TIMEBASE_CORRECTION_PLL 0x28

#define GYRO_SMPLRT_DIV 0x00
#define GYRO_CONFIG_1   0x01
#define GYRO_CONFIG_2   0x02
#define XG_OFFS_USRH   0x03
#define XG_OFFS_USRL   0x04
#define YG_OFFS_USRH   0x05
#define YG_OFFS_USRL   0x06
#define ZG_OFFS_USRH   0x07
#define ZG_OFFS_USRL   0x08
#define ODR_ALIGN_EN   0x09
#define ACCEL_SMPLRT_DIV_1 0x10
#define ACCEL_SMPLRT_DIV_2 0x11
#define ACCEL_INTEL_CTRL   0x12
#define ACCEL_WOM_THR     0x13
#define ACCEL_CONFIG     0x14
#define ACCEL_CONFIG_2   0x15
#define FSYNC_CONFIG    0x52
#define TEMP_CONFIG     0x53
#define MOD_CTRL_USR    0x54


#define SPI1_NODE DT_NODELABEL(spi1)
static const struct device *spi1_dev = DEVICE_DT_GET(SPI1_NODE);


#define STACKSIZE CONFIG_BT_NUS_THREAD_STACK_SIZE
#define PRIORITY 7

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN	(sizeof(DEVICE_NAME) - 1)

#define RUN_STATUS_LED DK_LED1
#define RUN_LED_BLINK_INTERVAL 100



#define MY_GPIO0 DT_NODELABEL(gpio0)
#define GPIO_0_CS 27//28
const struct device *gpio0_dev = DEVICE_DT_GET(MY_GPIO0);

#define GPIO_0_BUTTON_1 23//13
#define GPIO_0_BUTTON_2 26//14
#define IMU_INT_PIN 25//4

#define LED_0 8   

static struct gpio_callback interrupt_cb;

#define SLEEP_TIME_MS   100


static struct spi_config spi_cfg ={
	.frequency = 2000000U, // 2 MHz is the fastest that works with eval board wiring.
	.operation = SPI_WORD_SET(8),
	.slave = 0,
//	.cs = &spi_cs,
};

static volatile bool imu_data_ready = false;

static void imu_int_handler(const struct device *port, struct gpio_callback *cb, uint32_t pins)
{
    imu_data_ready = true;
}

static void readRegister(uint8_t reg, uint8_t values[], uint8_t size) {
    int err;

    uint8_t tx_buffer[1];
    tx_buffer[0] = reg | 0x80; // Set MSB for read operation

    struct spi_buf tx_spi_bufs[] = {
        {
            .buf = tx_buffer,
            .len = sizeof(tx_buffer)
        }
    };

    struct spi_buf_set spi_tx_buffer_set = {
        .buffers = tx_spi_bufs,
        .count = 1
    };

    struct spi_buf rx_spi_bufs[] = {
        {
            .buf = values,
            .len = size
        }
    };

    struct spi_buf_set spi_rx_buffer_set = {
        .buffers = rx_spi_bufs,
        .count = 1
    };

    gpio_pin_set(gpio0_dev, GPIO_0_CS, 0); // Set CS low

    err = spi_write(spi1_dev, &spi_cfg, &spi_tx_buffer_set);
    if (err >= 0) {
        // SPI read
        err = spi_read(spi1_dev, &spi_cfg, &spi_rx_buffer_set);
    }

    gpio_pin_set(gpio0_dev, GPIO_0_CS, 1); // Set CS high    

    if (err < 0) {
        printk("SPI read failed %d\n", err);
    }
}

static void writeRegister(uint8_t reg, uint8_t values[], uint8_t size) {
    int err;

    // Create SPI buffer with register address
    uint8_t tx_reg[1] = { reg & 0x7F }; // Clear MSB for write

    struct spi_buf tx_spi_bufs[] = {
        { .buf = tx_reg, .len = sizeof(tx_reg) },
        { .buf = values, .len = size } // Data to write
    };

    struct spi_buf_set spi_tx_buffer_set = {
        .buffers = tx_spi_bufs,
        .count = 2
    };

    gpio_pin_set(gpio0_dev, GPIO_0_CS, 0); // CS low

    err = spi_write(spi1_dev, &spi_cfg, &spi_tx_buffer_set);

    gpio_pin_set(gpio0_dev, GPIO_0_CS, 1); // CS high

    if (err < 0) {
        printk("SPI write failed %d\n", err);
    }
}

static void calibrateGyro(void) {

    writeRegister(REG_BANK_SEL, (uint8_t[]){0x02 << 4}, 1); // Select bank 2 by putting 2 in bits [5:4]
    // Set gyro offsets
    int16_t x_gyro_offset = -288; // Offset the gyro x readings by this value as a calibration
    int16_t y_gyro_offset = -36;
    int16_t z_gyro_offset = -70;
    writeRegister(XG_OFFS_USRH, (uint8_t[]){(x_gyro_offset >> 8) & 0xFF}, 1);
    writeRegister(XG_OFFS_USRL, (uint8_t[]){x_gyro_offset & 0xFF}, 1);
    writeRegister(YG_OFFS_USRH, (uint8_t[]){(y_gyro_offset >> 8) & 0xFF}, 1);
    writeRegister(YG_OFFS_USRL, (uint8_t[]){y_gyro_offset & 0xFF}, 1);
    writeRegister(ZG_OFFS_USRH, (uint8_t[]){(z_gyro_offset >> 8) & 0xFF}, 1);
    writeRegister(ZG_OFFS_USRL, (uint8_t[]){z_gyro_offset & 0xFF}, 1);
    k_msleep(10);
}

static void imuInterruptConfig(void) {
    writeRegister(REG_BANK_SEL, (uint8_t[]){0x00 << 4}, 1); // put 0 in bits [5:4]
    k_msleep(10);
    writeRegister(INT_PIN_CFG, (uint8_t[]){0b10000000}, 1); // INT pin is active low, push-pull
    k_msleep(10);
    writeRegister(INT_ENABLE_1, (uint8_t[]){0b00000001}, 1); // Data ready interrupt enabled
	k_msleep(10);

}

static void initialCongig(void) {

    writeRegister(REG_BANK_SEL, (uint8_t[]){0x00 << 4}, 1); // put 0 in bits [5:4]
	k_msleep(10);

    writeRegister(PWR_MGMT_1, (uint8_t[]){0b00001001}, 1); // Wake up device, temp sensor off
    uint8_t rx_data[1];
    k_msleep(1000);
    writeRegister(REG_BANK_SEL, (uint8_t[]){0x02 << 4}, 1); // Select bank 2 by putting 2 in bits [5:4]
    k_msleep(10);
    readRegister(REG_BANK_SEL, rx_data, 1);
    printf("REG_BANK_SEL: 0x%02X\n", rx_data[0]);
    k_msleep(10);
    writeRegister(GYRO_CONFIG_1, (uint8_t[]){0b00111101}, 1); // 1000dps DLPF 361.4Hz cutoff
    k_msleep(10);
    readRegister(GYRO_CONFIG_1, rx_data, 1);
    printf("GYRO_CONFIG_1: 0x%02X\n", rx_data[0]);
    k_msleep(10);

    calibrateGyro();
	imuInterruptConfig();

    writeRegister(REG_BANK_SEL, (uint8_t[]){0x00 << 4}, 1); // put 0 in bits [5:4]
    k_msleep(10);

}


#define CON_STATUS_LED DK_LED2

#define KEY_PASSKEY_ACCEPT DK_BTN1_MSK
#define KEY_PASSKEY_REJECT DK_BTN2_MSK

static K_SEM_DEFINE(ble_init_ok, 0, 1);

static struct bt_conn *current_conn;
static struct bt_conn *auth_conn;

static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
	BT_DATA(BT_DATA_NAME_COMPLETE, DEVICE_NAME, DEVICE_NAME_LEN),
};

static const struct bt_data sd[] = {
	BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_NUS_VAL),
};

#ifdef CONFIG_UART_ASYNC_ADAPTER
UART_ASYNC_ADAPTER_INST_DEFINE(async_adapter);
#else
#define async_adapter NULL
#endif

static void connected(struct bt_conn *conn, uint8_t err)
{
	char addr[BT_ADDR_LE_STR_LEN];

	if (err) {
		LOG_ERR("Connection failed, err 0x%02x %s", err, bt_hci_err_to_str(err));
		return;
	}

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
	LOG_INF("Connected %s", addr);

	current_conn = bt_conn_ref(conn);

	dk_set_led_on(CON_STATUS_LED);
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
	char addr[BT_ADDR_LE_STR_LEN];

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

	LOG_INF("Disconnected: %s, reason 0x%02x %s", addr, reason, bt_hci_err_to_str(reason));

	if (auth_conn) {
		bt_conn_unref(auth_conn);
		auth_conn = NULL;
	}

	if (current_conn) {
		bt_conn_unref(current_conn);
		current_conn = NULL;
		dk_set_led_off(CON_STATUS_LED);
	}
}

#ifdef CONFIG_BT_NUS_SECURITY_ENABLED
static void security_changed(struct bt_conn *conn, bt_security_t level,
			     enum bt_security_err err)
{
	char addr[BT_ADDR_LE_STR_LEN];

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

	if (!err) {
		LOG_INF("Security changed: %s level %u", addr, level);
	} else {
		LOG_WRN("Security failed: %s level %u err %d %s", addr, level, err,
			bt_security_err_to_str(err));
	}
}
#endif

BT_CONN_CB_DEFINE(conn_callbacks) = {
	.connected    = connected,
	.disconnected = disconnected,
#ifdef CONFIG_BT_NUS_SECURITY_ENABLED
	.security_changed = security_changed,
#endif
};

#if defined(CONFIG_BT_NUS_SECURITY_ENABLED)
static void auth_passkey_display(struct bt_conn *conn, unsigned int passkey)
{
	char addr[BT_ADDR_LE_STR_LEN];

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

	LOG_INF("Passkey for %s: %06u", addr, passkey);
}

static void auth_passkey_confirm(struct bt_conn *conn, unsigned int passkey)
{
	char addr[BT_ADDR_LE_STR_LEN];

	auth_conn = bt_conn_ref(conn);

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

	LOG_INF("Passkey for %s: %06u", addr, passkey);

	if (IS_ENABLED(CONFIG_SOC_SERIES_NRF54HX) || IS_ENABLED(CONFIG_SOC_SERIES_NRF54LX)) {
		LOG_INF("Press Button 0 to confirm, Button 1 to reject.");
	} else {
		LOG_INF("Press Button 1 to confirm, Button 2 to reject.");
	}
}


static void auth_cancel(struct bt_conn *conn)
{
	char addr[BT_ADDR_LE_STR_LEN];

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

	LOG_INF("Pairing cancelled: %s", addr);
}


static void pairing_complete(struct bt_conn *conn, bool bonded)
{
	char addr[BT_ADDR_LE_STR_LEN];

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

	LOG_INF("Pairing completed: %s, bonded: %d", addr, bonded);
}


static void pairing_failed(struct bt_conn *conn, enum bt_security_err reason)
{
	char addr[BT_ADDR_LE_STR_LEN];

	bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));

	LOG_INF("Pairing failed conn: %s, reason %d %s", addr, reason,
		bt_security_err_to_str(reason));
}

static struct bt_conn_auth_cb conn_auth_callbacks = {
	.passkey_display = auth_passkey_display,
	.passkey_confirm = auth_passkey_confirm,
	.cancel = auth_cancel,
};

static struct bt_conn_auth_info_cb conn_auth_info_callbacks = {
	.pairing_complete = pairing_complete,
	.pairing_failed = pairing_failed
};
#else
static struct bt_conn_auth_cb conn_auth_callbacks;
static struct bt_conn_auth_info_cb conn_auth_info_callbacks;
#endif

static void bt_receive_cb(struct bt_conn *conn, const uint8_t *const data,
                          uint16_t len)
{
    char addr[BT_ADDR_LE_STR_LEN];
    bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
    LOG_INF("Received data from %s: %.*s", addr, len, data);
}

static struct bt_nus_cb nus_cb = {
	.received = bt_receive_cb,
};

void error(void)
{
	dk_set_leds_state(DK_ALL_LEDS_MSK, DK_NO_LEDS_MSK);

	while (true) {
		/* Spin for ever */
		k_sleep(K_MSEC(1000));
	}
}

#ifdef CONFIG_BT_NUS_SECURITY_ENABLED
static void num_comp_reply(bool accept)
{
	if (accept) {
		bt_conn_auth_passkey_confirm(auth_conn);
		LOG_INF("Numeric Match, conn %p", (void *)auth_conn);
	} else {
		bt_conn_auth_cancel(auth_conn);
		LOG_INF("Numeric Reject, conn %p", (void *)auth_conn);
	}

	bt_conn_unref(auth_conn);
	auth_conn = NULL;
}

void button_changed(uint32_t button_state, uint32_t has_changed)
{
	uint32_t buttons = button_state & has_changed;

	if (auth_conn) {
		if (buttons & KEY_PASSKEY_ACCEPT) {
			num_comp_reply(true);
		}

		if (buttons & KEY_PASSKEY_REJECT) {
			num_comp_reply(false);
		}
	}
}
#endif /* CONFIG_BT_NUS_SECURITY_ENABLED */

int main(void)
{

	k_msleep(1000);

	int button_val_1, button_val_2;
	int16_t accel_x, accel_y, accel_z;
	int16_t gyro_x, gyro_y, gyro_z;


	int err = 0;

	gpio_pin_configure(gpio0_dev, GPIO_0_CS, GPIO_OUTPUT);
	gpio_pin_set(gpio0_dev, GPIO_0_CS, 1); // Set CS high

	if (!device_is_ready(spi1_dev)) {
		printk("SPI device not found\n");
		return 0;
	}


	int ret;


	ret = gpio_pin_configure(gpio0_dev, LED_0, GPIO_OUTPUT_ACTIVE);
	if (ret < 0) {
    printk("Failed to configure led\n");
    return 0;
	}


    ret = gpio_pin_configure(gpio0_dev, GPIO_0_BUTTON_1, GPIO_INPUT | GPIO_PULL_UP);
    if (ret < 0) {
    printk("Failed to configure button 1 pin\n");
        return 0;
    }

    ret = gpio_pin_configure(gpio0_dev, GPIO_0_BUTTON_2, GPIO_INPUT | GPIO_PULL_UP);
    if (ret < 0) {
    printk("Failed to configure button 2 pin\n");
        return 0;
    }

    ret = gpio_pin_configure(gpio0_dev, IMU_INT_PIN, GPIO_INPUT | GPIO_PULL_UP);
    if (ret < 0) {
    printk("Failed to configure IMU INT pin\n");
        return 0;
    }



    ret = gpio_pin_interrupt_configure(gpio0_dev, IMU_INT_PIN, GPIO_INT_EDGE_FALLING); 
    if (ret < 0) {
    printk("Failed to configure IMU INT interrupt\n");
    return 0;
    }

    gpio_init_callback(&interrupt_cb, imu_int_handler, BIT(IMU_INT_PIN));
    gpio_add_callback(gpio0_dev, &interrupt_cb);

	k_msleep(100); 
    initialCongig();




	if (IS_ENABLED(CONFIG_BT_NUS_SECURITY_ENABLED)) {
		err = bt_conn_auth_cb_register(&conn_auth_callbacks);
		if (err) {
			printk("Failed to register authorization callbacks.\n");
			return 0;
		}

		err = bt_conn_auth_info_cb_register(&conn_auth_info_callbacks);
		if (err) {
			printk("Failed to register authorization info callbacks.\n");
			return 0;
		}
	}

	err = bt_enable(NULL);
	if (err) {
		error();
	}

	LOG_INF("Bluetooth initialized");

	k_sem_give(&ble_init_ok);

	if (IS_ENABLED(CONFIG_SETTINGS)) {
		settings_load();
	}

	err = bt_nus_init(&nus_cb);
	if (err) {
		LOG_ERR("Failed to initialize NUS service (err: %d)", err);
		return 0;
	}

	err = bt_le_adv_start(BT_LE_ADV_CONN, ad, ARRAY_SIZE(ad), sd,
			      ARRAY_SIZE(sd));
	if (err) {
		LOG_ERR("Advertising failed to start (err %d)", err);
		return 0;
	}


	while (1) {
	
		gpio_pin_set(gpio0_dev, LED_0, 1);  
		k_msleep(3000);
		gpio_pin_set(gpio0_dev, LED_0, 0);    
		k_msleep(25);
		//printf("Toggling LED\n");
	

}
// 	while (1) {

// 		ret = gpio_pin_toggle_dt(&led);
// 		if (ret < 0) {
// 			return 0;
// 		}


//         int button_val_1 = gpio_pin_get(gpio0_dev, GPIO_0_BUTTON_1);
//         int button_val_2 = gpio_pin_get(gpio0_dev, GPIO_0_BUTTON_2);

//         if (imu_data_ready) {
            
//             imu_data_ready = false;
//             uint8_t rx_data[12];
//             readRegister(ACCEL_XOUT_H, rx_data, 12);
//             int16_t accel_x = (rx_data[0] << 8) | rx_data[1];
//             int16_t accel_y = (rx_data[2] << 8) | rx_data[3];
//             int16_t accel_z = (rx_data[4] << 8) | rx_data[5];
//             int16_t gyro_x = (rx_data[6] << 8) | rx_data[7];
//             int16_t gyro_y = (rx_data[8] << 8) | rx_data[9];
//             int16_t gyro_z = (rx_data[10] << 8) | rx_data[11];

            // printf("Buttons: %d, %d | "
            //     "Accel: X=%6d, Y=%6d, Z=%6d | "
            //     "Gyro:  X=%6d, Y=%6d, Z=%6d\n",
            //     button_val_1, button_val_2,
            //     accel_x, accel_y, accel_z,
            //     gyro_x, gyro_y, gyro_z);

//         }

//         k_msleep(100); 

// }
}



void ble_write_thread(void)
{
    /* Wait for BLE to initialize */
    k_sem_take(&ble_init_ok, K_FOREVER);

    while (1) {

		char msg[128];  


		int button_val_1 = gpio_pin_get(gpio0_dev, GPIO_0_BUTTON_1);
        int button_val_2 = gpio_pin_get(gpio0_dev, GPIO_0_BUTTON_2);

        if (imu_data_ready) {
            //k_msleep(1); 
            imu_data_ready = false;
            uint8_t rx_data[12];
            readRegister(ACCEL_XOUT_H, rx_data, 12);
            int16_t accel_x = (rx_data[0] << 8) | rx_data[1];
            int16_t accel_y = (rx_data[2] << 8) | rx_data[3];
            int16_t accel_z = (rx_data[4] << 8) | rx_data[5];
            int16_t gyro_x = (rx_data[6] << 8) | rx_data[7];
            int16_t gyro_y = (rx_data[8] << 8) | rx_data[9];
            int16_t gyro_z = (rx_data[10] << 8) | rx_data[11];
			
			// int len = snprintk(msg, sizeof(msg), "Buttons: %d, %d | "
            //     "Accel: X=%6d, Y=%6d, Z=%6d | "
            //     "Gyro:  X=%6d, Y=%6d, Z=%6d\n",
            //     button_val_1, button_val_2,
            //     accel_x, accel_y, accel_z,
            //     gyro_x, gyro_y, gyro_z);

			uint8_t ble_buf[14]; // 2 buttons + 6 bytes accel + 6 bytes gyro

			ble_buf[0] = button_val_1 ? 1 : 0;
			ble_buf[1] = button_val_2 ? 1 : 0;

			// Accelerometer (big endian)
			ble_buf[2] = (accel_x >> 8) & 0xFF;
			ble_buf[3] = accel_x & 0xFF;
			ble_buf[4] = (accel_y >> 8) & 0xFF;
			ble_buf[5] = accel_y & 0xFF;
			ble_buf[6] = (accel_z >> 8) & 0xFF;
			ble_buf[7] = accel_z & 0xFF;

			// Gyroscope (big endian)
			ble_buf[8]  = (gyro_x >> 8) & 0xFF;
			ble_buf[9]  = gyro_x & 0xFF;
			ble_buf[10] = (gyro_y >> 8) & 0xFF;
			ble_buf[11] = gyro_y & 0xFF;
			ble_buf[12] = (gyro_z >> 8) & 0xFF;
			ble_buf[13] = gyro_z & 0xFF;

			if (current_conn) {
				if (bt_nus_send(current_conn, ble_buf, sizeof(ble_buf))) {
					LOG_WRN("Failed to send raw data over BLE");
				}
			}

            //k_msleep(100); // Delay between messages

        }		

		//k_msleep(10);

    }
}


K_THREAD_DEFINE(ble_write_thread_id, STACKSIZE, ble_write_thread, NULL, NULL,
		NULL, PRIORITY, 0, 0);

		