#include <stdio.h>
#include <stdbool.h>
#include "esp_camera.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_err.h"
#include "esp_idf_version.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_websocket_client.h"
#include "cJSON.h"
#include "camera_pins.h"
#include "sensor.h"
#include <string.h>

#define WIFI_SSID "nhmc"
#define WIFI_PASS "14112005"
#define SERVER_URI "ws://192.168.137.1:8080"

static const char *TAG = "ESP32CAM";
static esp_websocket_client_handle_t ws;
static EventGroupHandle_t s_wifi_event_group;

#define WIFI_CONNECTED_BIT BIT0

/* ---------------- UTILITIES ---------------- */
static bool send_ws_json(cJSON *obj)
{
    if (!obj)
    {
        ESP_LOGE(TAG, "Attempted to send null JSON object");
        return false;
    }

    if (!ws || !esp_websocket_client_is_connected(ws))
    {
        ESP_LOGW(TAG, "WebSocket not connected; dropping JSON response");
        return false;
    }

    char *payload = cJSON_PrintUnformatted(obj);
    if (!payload)
    {
        ESP_LOGE(TAG, "Failed to encode JSON payload");
        return false;
    }

    int sent = esp_websocket_client_send_text(ws, payload, strlen(payload), portMAX_DELAY);
    if (sent < 0)
    {
        ESP_LOGE(TAG, "Failed to send JSON payload over WebSocket");
        free(payload);
        return false;
    }
    free(payload);
    return true;
}

static void send_error_response(const char *message)
{
    if (!message)
    {
        message = "Unknown JSON error";
    }

    cJSON *err = cJSON_CreateObject();
    if (!err)
    {
        ESP_LOGE(TAG, "Failed to allocate JSON error response");
        return;
    }

    cJSON_AddStringToObject(err, "status", "error");
    cJSON_AddStringToObject(err, "message", message);
    send_ws_json(err);
    cJSON_Delete(err);
}

/* ---------------- WIFI INIT ---------------- */
static void wifi_event_handler(void *arg, esp_event_base_t event_base, int32_t event_id, void *event_data)
{
    if (!s_wifi_event_group)
    {
        return;
    }

    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START)
    {
        ESP_LOGI(TAG, "Wi-Fi STA start; connecting...");
        esp_wifi_connect();
    }
    else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED)
    {
        ESP_LOGW(TAG, "Wi-Fi disconnected; retrying...");
        xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
        esp_wifi_connect();
    }
    else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
    {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Wi-Fi connected, IP: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

static esp_err_t wifi_init_sta(void)
{
    s_wifi_event_group = xEventGroupCreate();
    if (!s_wifi_event_group)
    {
        ESP_LOGE(TAG, "Failed to create Wi-Fi event group");
        return ESP_ERR_NO_MEM;
    }

    esp_err_t err = esp_netif_init();
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "esp_netif_init failed: %s", esp_err_to_name(err));
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }

    err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE)
    {
        ESP_LOGE(TAG, "esp_event_loop_create_default failed: %s", esp_err_to_name(err));
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }
    else if (err == ESP_ERR_INVALID_STATE)
    {
        ESP_LOGW(TAG, "Event loop already created; continuing");
    }

    if (!esp_netif_create_default_wifi_sta())
    {
        ESP_LOGE(TAG, "Failed to create default Wi-Fi STA");
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return ESP_FAIL;
    }

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    err = esp_wifi_init(&cfg);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "esp_wifi_init failed: %s", esp_err_to_name(err));
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }
    err = esp_wifi_set_mode(WIFI_MODE_STA);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "esp_wifi_set_mode failed: %s", esp_err_to_name(err));
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    err = esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "esp_wifi_set_config failed: %s", esp_err_to_name(err));
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }
    bool wifi_handler_registered = false;
    bool ip_handler_registered = false;
    err = esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to register Wi-Fi event handler: %s", esp_err_to_name(err));
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }
    wifi_handler_registered = true;
    err = esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Failed to register IP event handler: %s", esp_err_to_name(err));
        if (wifi_handler_registered)
        {
            esp_event_handler_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler);
        }
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }
    ip_handler_registered = true;
    err = esp_wifi_start();
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "esp_wifi_start failed: %s", esp_err_to_name(err));
        if (wifi_handler_registered)
        {
            esp_event_handler_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler);
        }
        if (ip_handler_registered)
        {
            esp_event_handler_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler);
        }
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }
    ESP_LOGI(TAG, "Connecting to Wi-Fi %s", WIFI_SSID);

    err = esp_wifi_connect();
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "esp_wifi_connect failed: %s", esp_err_to_name(err));
        if (wifi_handler_registered)
        {
            esp_event_handler_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler);
        }
        if (ip_handler_registered)
        {
            esp_event_handler_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler);
        }
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return err;
    }

    EventBits_t bits = xEventGroupWaitBits(
        s_wifi_event_group,
        WIFI_CONNECTED_BIT,
        pdFALSE,
        pdFALSE,
        pdMS_TO_TICKS(10000));

    if ((bits & WIFI_CONNECTED_BIT) == 0)
    {
        ESP_LOGE(TAG, "Wi-Fi connection timeout");
        if (wifi_handler_registered)
        {
            esp_event_handler_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler);
        }
        if (ip_handler_registered)
        {
            esp_event_handler_unregister(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler);
        }
        vEventGroupDelete(s_wifi_event_group);
        s_wifi_event_group = NULL;
        return ESP_ERR_TIMEOUT;
    }

    ESP_LOGI(TAG, "Wi-Fi station initialized successfully");
    return ESP_OK;
}

/* ---------------- CAMERA INIT ---------------- */
static void camera_init(void)
{
    camera_config_t config = {
        .pin_pwdn = CAM_PIN_PWDN,
        .pin_reset = CAM_PIN_RESET,
        .pin_xclk = CAM_PIN_XCLK,
        .pin_sccb_sda = CAM_PIN_SIOD,
        .pin_sccb_scl = CAM_PIN_SIOC,
        .pin_d7 = CAM_PIN_D7,
        .pin_d6 = CAM_PIN_D6,
        .pin_d5 = CAM_PIN_D5,
        .pin_d4 = CAM_PIN_D4,
        .pin_d3 = CAM_PIN_D3,
        .pin_d2 = CAM_PIN_D2,
        .pin_d1 = CAM_PIN_D1,
        .pin_d0 = CAM_PIN_D0,
        .pin_vsync = CAM_PIN_VSYNC,
        .pin_href = CAM_PIN_HREF,
        .pin_pclk = CAM_PIN_PCLK,
        .xclk_freq_hz = 20000000,
        .ledc_timer = LEDC_TIMER_0,
        .ledc_channel = LEDC_CHANNEL_0,
        .pixel_format = PIXFORMAT_JPEG,
        .frame_size = FRAMESIZE_QVGA,
        .jpeg_quality = 8,
        .fb_count = 3};
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK)
        ESP_LOGE(TAG, "Camera init failed 0x%x", err);
    else
        ESP_LOGI(TAG, "Camera OK");
}

/* ---------------- WEBSOCKET EVENTS ---------------- */
static void on_ws_event(void *arg, esp_event_base_t base, int32_t eid, void *data)
{
    esp_websocket_event_data_t *event = (esp_websocket_event_data_t *)data;

    switch (eid)
    {
    case WEBSOCKET_EVENT_CONNECTED:
        ESP_LOGI(TAG, "WebSocket connected");
        break;
    case WEBSOCKET_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "WebSocket disconnected");
        break;
    case WEBSOCKET_EVENT_ERROR:
        if (event)
        {
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 2, 0)
            ESP_LOGE(TAG, "WebSocket transport error, type=%d, esp_tls=0x%x", event->error_handle.error_type, event->error_handle.esp_tls_last_esp_err);
#else
            ESP_LOGE(TAG, "WebSocket transport error, type=%d, esp_tls=0x%x, errno=%d", event->error_handle.error_type, event->error_handle.esp_tls_last_esp_err, event->error_handle.last_errno);
#endif
        }
        else
        {
            ESP_LOGE(TAG, "WebSocket transport error with no details");
        }
        break;
    case WEBSOCKET_EVENT_DATA:
        if (!event)
        {
            ESP_LOGW(TAG, "WebSocket data event with null payload");
            return;
        }
        if (event->op_code == WS_TRANSPORT_OPCODES_BINARY)
        {
            ESP_LOGD(TAG, "Binary data received (%d bytes) ignored", event->data_len);
            return;
        }
        char *json = strndup(event->data_ptr, event->data_len);
        if (!json)
        {
            ESP_LOGE(TAG, "Failed to allocate buffer for JSON payload");
            return;
        }
        cJSON *root = cJSON_Parse(json);
        if (!root)
        {
            ESP_LOGW(TAG, "Invalid JSON payload from WebSocket");
            send_error_response("Invalid JSON payload");
            free(json);
            return;
        }

        sensor_t *s = esp_camera_sensor_get();
        if (!s)
        {
            ESP_LOGE(TAG, "Camera sensor unavailable");
            send_error_response("Camera sensor unavailable");
            cJSON_Delete(root);
            free(json);
            return;
        }

        bool updated = false;

        const cJSON *brightness = cJSON_GetObjectItemCaseSensitive(root, "brightness");
        if (brightness)
        {
            if (!cJSON_IsNumber(brightness))
            {
                ESP_LOGW(TAG, "Invalid type for brightness field");
                send_error_response("Field 'brightness' must be numeric");
                cJSON_Delete(root);
                free(json);
                return;
            }
            s->set_brightness(s, brightness->valueint);
            ESP_LOGI(TAG, "Set brightness to %d", s->status.brightness);
            updated = true;
        }

        const cJSON *contrast = cJSON_GetObjectItemCaseSensitive(root, "contrast");
        if (contrast)
        {
            if (!cJSON_IsNumber(contrast))
            {
                ESP_LOGW(TAG, "Invalid type for contrast field");
                send_error_response("Field 'contrast' must be numeric");
                cJSON_Delete(root);
                free(json);
                return;
            }
            s->set_contrast(s, contrast->valueint);
            ESP_LOGI(TAG, "Set contrast to %d", s->status.contrast);
            updated = true;
        }

        const cJSON *saturation = cJSON_GetObjectItemCaseSensitive(root, "saturation");
        if (saturation)
        {
            if (!cJSON_IsNumber(saturation))
            {
                ESP_LOGW(TAG, "Invalid type for saturation field");
                send_error_response("Field 'saturation' must be numeric");
                cJSON_Delete(root);
                free(json);
                return;
            }
            s->set_saturation(s, saturation->valueint);
            ESP_LOGI(TAG, "Set saturation to %d", s->status.saturation);
            updated = true;
        }

        const cJSON *quality = cJSON_GetObjectItemCaseSensitive(root, "quality");
        if (quality)
        {
            if (!cJSON_IsNumber(quality))
            {
                ESP_LOGW(TAG, "Invalid type for quality field");
                send_error_response("Field 'quality' must be numeric");
                cJSON_Delete(root);
                free(json);
                return;
            }
            s->set_quality(s, quality->valueint);
            ESP_LOGI(TAG, "Set quality to %d", s->status.quality);
            updated = true;
        }

        if (!updated)
        {
            ESP_LOGW(TAG, "Received camera command without recognized fields");
            send_error_response("No supported camera fields in JSON payload");
            cJSON_Delete(root);
            free(json);
            return;
        }

        cJSON *resp = cJSON_CreateObject();
        if (!resp)
        {
            ESP_LOGE(TAG, "Failed to allocate JSON response");
            cJSON_Delete(root);
            free(json);
            return;
        }
        cJSON_AddStringToObject(resp, "status", "ok");
        cJSON_AddStringToObject(resp, "message", "Camera parameters updated");
        if (send_ws_json(resp))
        {
            ESP_LOGI(TAG, "Camera parameters updated and acknowledged");
        }
        else
        {
            ESP_LOGW(TAG, "Failed to deliver camera update acknowledgment");
        }
        cJSON_Delete(resp);
        cJSON_Delete(root);
        free(json);
        break;
    default:
        ESP_LOGD(TAG, "Unhandled WebSocket event id=%ld", eid);
        break;
    }
}

/* ---------------- MAIN ---------------- */
void app_main(void)
{
    esp_err_t nvs_ret = nvs_flash_init();
    if (nvs_ret == ESP_ERR_NVS_NO_FREE_PAGES || nvs_ret == ESP_ERR_NVS_NEW_VERSION_FOUND)
    {
        ESP_ERROR_CHECK(nvs_flash_erase());
        nvs_ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(nvs_ret);
    ESP_ERROR_CHECK(wifi_init_sta());
    camera_init();

    esp_websocket_client_config_t ws_cfg = {.uri = SERVER_URI};
    ws = esp_websocket_client_init(&ws_cfg);
    if (!ws)
    {
        ESP_LOGE(TAG, "Failed to create WebSocket client");
        return;
    }
    esp_websocket_register_events(ws, WEBSOCKET_EVENT_ANY, on_ws_event, NULL);
    esp_err_t ws_start_err = esp_websocket_client_start(ws);
    if (ws_start_err != ESP_OK)
    {
        ESP_LOGE(TAG, "WebSocket start failed: %s", esp_err_to_name(ws_start_err));
        return;
    }
    ESP_LOGI(TAG, "WebSocket client started: %s", SERVER_URI);

    while (true)
    {
        if (!esp_websocket_client_is_connected(ws))
        {
            // Hold off streaming until the websocket handshake completes.
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        camera_fb_t *fb = esp_camera_fb_get();
        if (fb)
        {
            int sent = esp_websocket_client_send_bin(ws, (const char *)fb->buf, fb->len, portMAX_DELAY);
            if (sent < 0)
            {
                ESP_LOGE(TAG, "Failed to send frame via WebSocket");
            }
            esp_camera_fb_return(fb);
        }
        else
        {
            ESP_LOGW(TAG, "Failed to get camera frame buffer");
        }

        vTaskDelay(pdMS_TO_TICKS(50)); // ~20 FPS when streaming
    }
}
