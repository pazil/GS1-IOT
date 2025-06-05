#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <math.h>
#include <WiFi.h>
#include <HTTPClient.h>

// =================================================================
// --- CONFIGURAÇÕES DO USUÁRIO ---
// =================================================================
// Insira as credenciais da sua rede Wi-Fi
const char* WIFI_SSID = "SEU_NOME_DE_REDE_AQUI";
const char* WIFI_PASSWORD = "SUA_SENHA_DE_REDE_AQUI";

// Endereço IP do computador executando o alert_server.py
// Exemplo: "192.168.1.10"
const char* SERVER_IP = "IP_DO_SEU_COMPUTADOR_AQUI"; 
const int SERVER_PORT = 8080; // Deve ser a mesma porta do servidor Python

// Lógica de Confirmação de Alerta
// Quantas janelas consecutivas de "tremor" são necessárias para disparar um alerta.
// Com janela de 1s, um valor de 2 significa que o tremor deve ser detectado por 2s.
const int MIN_CONSECUTIVE_WINDOWS_FOR_ALERT = 2; 
// =================================================================


// --- Configurações do Sensor MPU6050 ---
Adafruit_MPU6050 mpu;

// --- Parâmetros de Janelamento ---
const int WINDOW_SIZE = 50;
const int SAMPLING_FREQUENCY_HZ = 50;
const int DELAY_MS = 1000 / SAMPLING_FREQUENCY_HZ;

// --- Buffers de Dados ---
float accel_x_window[WINDOW_SIZE];
float accel_y_window[WINDOW_SIZE];
float accel_z_window[WINDOW_SIZE];
float svm_window[WINDOW_SIZE];
int sample_count = 0;

// --- Variáveis para Lógica de Confirmação de Tremor ---
int consecutive_tremor_windows = 0;
bool alert_active = false; // True se um alerta de tremor está ativo

// --- Parâmetros do Modelo e Scaler ---
const int NUM_FEATURES = 32;
const float scaler_means[NUM_FEATURES] = {10.21886541f, 2.28296651f, 10.20023889f, 5.22562478f, 18.98728822f, 13.76166343f, 5740.88572806f, 10.23268411f, 0.29410218f, 0.93116674f, 1.66920908f, -1.65741119f, 3.62482139f, 5.28223258f, 89.91796834f, 0.71845937f, -2.25340990f, 1.24075164f, 2.92679911f, -6.87506484f, 0.91182524f, 7.78689007f, 404.03677510f, 2.41622221f, 10.64256298f, 2.36730343f, 11.20050337f, 6.55009465f, 20.43635561f, 13.88626096f, 6234.84047149f, 10.64256298f};
const float scaler_scales[NUM_FEATURES] = {0.43848090f, 2.23345087f, 13.37981538f, 4.70485023f, 9.60728868f, 13.52942530f, 904.70063484f, 0.43511866f, 0.20652894f, 0.89562134f, 2.23530918f, 1.66032869f, 3.86593248f, 5.19538032f, 119.17124595f, 0.49746271f, 0.27582642f, 1.17785164f, 3.80559178f, 5.26900775f, 3.13734484f, 7.75847094f, 212.97004625f, 0.27281179f, 0.48182907f, 2.36566647f, 15.45066859f, 3.43805079f, 11.08204307f, 13.91323103f, 1188.02728350f, 0.48182907f};
const float model_weights[NUM_FEATURES] = {-0.17020935f, 0.40698866f, -0.42459450f, -0.40391110f, 0.18315703f, 0.27052026f, -0.40369008f, -0.20178912f, 0.92826360f, 0.78638197f, -0.29678722f, -1.30105247f, -0.34587637f, 0.15841767f, -0.25434514f, 1.32539134f, -0.85999799f, 0.90731663f, -0.27166656f, 0.17569524f, 0.98940135f, 0.28077100f, -0.00613811f, 0.43735945f, -0.03930666f, 0.31498672f, -0.47548902f, -0.76731637f, 0.02387615f, 0.20862653f, -0.33402982f, -0.03930666f};
const float model_bias = 1.67400376f;

float features[NUM_FEATURES];

// --- Funções de Extração de Features (idênticas à versão serial) ---
float calculate_mean(float arr[], int size) { if (size == 0) return 0; float sum = 0; for (int i = 0; i < size; i++) sum += arr[i]; return sum / size; }
float calculate_std(float arr[], int size, float mean) { if (size == 0) return 0; float sum_sq_diff = 0; for (int i = 0; i < size; i++) sum_sq_diff += powf(arr[i] - mean, 2); return sqrtf(sum_sq_diff / size); }
float calculate_min(float arr[], int size) { if (size == 0) return 0; float min_val = arr[0]; for (int i = 1; i < size; i++) if (arr[i] < min_val) min_val = arr[i]; return min_val; }
float calculate_max(float arr[], int size) { if (size == 0) return 0; float max_val = arr[0]; for (int i = 1; i < size; i++) if (arr[i] > max_val) max_val = arr[i]; return max_val; }
float calculate_energy(float arr[], int size) { float sum_sq = 0; for (int i = 0; i < size; i++) sum_sq += powf(arr[i], 2); return sum_sq; }
float calculate_mav(float arr[], int size) { if (size == 0) return 0; float sum_abs = 0; for (int i = 0; i < size; i++) sum_abs += fabsf(arr[i]); return sum_abs / size; }

void extract_features_from_window() {
    for (int i = 0; i < WINDOW_SIZE; i++) { svm_window[i] = sqrtf(powf(accel_x_window[i], 2) + powf(accel_y_window[i], 2) + powf(accel_z_window[i], 2)); }
    float* data_streams[] = {accel_x_window, accel_y_window, accel_z_window, svm_window};
    int feature_idx = 0;
    for (int stream_idx = 0; stream_idx < 4; ++stream_idx) {
        float* current_stream = data_streams[stream_idx];
        float mean_val = calculate_mean(current_stream, WINDOW_SIZE);
        features[feature_idx++] = mean_val;
        features[feature_idx++] = calculate_std(current_stream, WINDOW_SIZE, mean_val);
        features[feature_idx++] = powf(features[feature_idx - 1], 2);
        features[feature_idx++] = calculate_min(current_stream, WINDOW_SIZE);
        features[feature_idx++] = calculate_max(current_stream, WINDOW_SIZE);
        features[feature_idx++] = features[feature_idx - 1] - features[feature_idx - 2];
        features[feature_idx++] = calculate_energy(current_stream, WINDOW_SIZE);
        features[feature_idx++] = calculate_mav(current_stream, WINDOW_SIZE);
    }
}

// --- Função de Escalonamento e Predição ---
void scale_current_features() {
    for (int i = 0; i < NUM_FEATURES; i++) {
        if (scaler_scales[i] != 0) features[i] = (features[i] - scaler_means[i]) / scaler_scales[i];
        else features[i] = (features[i] - scaler_means[i]);
    }
}

int perform_prediction() {
    float raw_prediction = 0.0f;
    for (int i = 0; i < NUM_FEATURES; i++) { raw_prediction += model_weights[i] * features[i]; }
    raw_prediction += model_bias;
    float probability = 1.0f / (1.0f + expf(-raw_prediction));
    return (probability > 0.9) ? 1 : 0;
}

// --- Funções de Rede ---
void connect_to_wifi() {
    Serial.print("\nConectando a ");
    Serial.println(WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        if (++retries > 20) {
            Serial.println("\nFalha ao conectar ao Wi-Fi. Reiniciando em 10 segundos...");
            delay(10000);
            ESP.restart();
        }
    }

    Serial.println("\nWi-Fi conectado!");
    Serial.print("Endereço IP: ");
    Serial.println(WiFi.localIP());
}

void sendHttpAlert(String alertType) {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String server_url = "http://" + String(SERVER_IP) + ":" + String(SERVER_PORT) + "/alert?type=" + alertType;
        
        Serial.print("Enviando alerta para: ");
        Serial.println(server_url);

        http.begin(server_url);
        int http_code = http.GET();

        if (http_code > 0) {
            String payload = http.getString();
            Serial.print("Código de resposta HTTP: ");
            Serial.println(http_code);
            Serial.print("Resposta do servidor: ");
            Serial.println(payload);
        } else {
            Serial.print("Falha no envio do alerta, erro: ");
            Serial.println(http.errorToString(http_code).c_str());
        }
        http.end();
    } else {
        Serial.println("Wi-Fi desconectado. Não é possível enviar alerta.");
    }
}

// --- Setup ---
void setup(void) {
    Serial.begin(115200);
    while (!Serial && millis() < 2000) delay(10);

    Serial.println("\nIniciando Detector de Tremores Sísmicos (Versão Wi-Fi)");
    
    connect_to_wifi();

    if (!mpu.begin()) {
        Serial.println("Falha ao encontrar o chip MPU6050. Verifique a conexão.");
        while (1) { delay(10); }
    }
    Serial.println("MPU6050 Encontrado!");

    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.println("Sensor MPU6050 configurado.");
    Serial.println("Iniciando monitoramento...");
}

// --- Loop Principal ---
void loop() {
    sensors_event_t a, g, temp;
    static unsigned long last_sample_millis = 0;

    if (millis() - last_sample_millis >= DELAY_MS) {
        last_sample_millis = millis();
        mpu.getEvent(&a, &g, &temp);

        accel_x_window[sample_count] = a.acceleration.x;
        accel_y_window[sample_count] = a.acceleration.y;
        accel_z_window[sample_count] = a.acceleration.z;
        sample_count++;

        if (sample_count == WINDOW_SIZE) {
            extract_features_from_window();
            scale_current_features();
            int prediction = perform_prediction();

            if (prediction == 1) { // Tremor detectado nesta janela
                consecutive_tremor_windows++;
                Serial.printf("Janela de tremor detectada. Contagem consecutiva: %d\n", consecutive_tremor_windows);
                
                if (consecutive_tremor_windows >= MIN_CONSECUTIVE_WINDOWS_FOR_ALERT && !alert_active) {
                    Serial.println("ALERTA CONFIRMADO! Enviando notificação...");
                    sendHttpAlert("tremor_confirmado");
                    alert_active = true;
                }
            } else { // Não tremor detectado
                if (alert_active) {
                    Serial.println("Status: Tremor finalizado. Enviando notificação de término.");
                    sendHttpAlert("tremor_finalizado");
                }
                Serial.println("Status: Sem Tremor.");
                consecutive_tremor_windows = 0;
                alert_active = false;
            }
            sample_count = 0;
        }
    }
} 