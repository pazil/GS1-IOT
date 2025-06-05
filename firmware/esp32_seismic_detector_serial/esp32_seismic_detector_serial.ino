#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <math.h>

// Configurações do Sensor MPU6050
Adafruit_MPU6050 mpu;

// Parâmetros para coleta de dados e janelamento
const int WINDOW_SIZE = 50; // Amostras por janela (igual ao usado no Python)
const int SAMPLING_FREQUENCY_HZ = 50;
const int DELAY_MS = 1000 / SAMPLING_FREQUENCY_HZ; // Atraso para ~50Hz

// Buffers para armazenar os dados da janela
float accel_x_window[WINDOW_SIZE];
float accel_y_window[WINDOW_SIZE];
float accel_z_window[WINDOW_SIZE];
float svm_window[WINDOW_SIZE]; // Para a Magnitude do Vetor de Sinal (SVM)
int sample_count = 0;

// Parâmetros do Modelo e Scaler (copiados de model_parameters.txt)
const int NUM_FEATURES = 32;

// Nomes das features (para referência, conforme model_parameters.txt):
// 0: mean_accel_x, 1: std_accel_x, 2: var_accel_x, 3: min_accel_x, 4: max_accel_x, 5: ptp_accel_x, 6: energy_accel_x, 7: mav_accel_x
// 8-15: para accel_y
// 16-23: para accel_z
// 24-31: para svm

const float scaler_means[NUM_FEATURES] = {10.21886541f, 2.28296651f, 10.20023889f, 5.22562478f, 18.98728822f, 13.76166343f, 5740.88572806f, 10.23268411f, 0.29410218f, 0.93116674f, 1.66920908f, -1.65741119f, 3.62482139f, 5.28223258f, 89.91796834f, 0.71845937f, -2.25340990f, 1.24075164f, 2.92679911f, -6.87506484f, 0.91182524f, 7.78689007f, 404.03677510f, 2.41622221f, 10.64256298f, 2.36730343f, 11.20050337f, 6.55009465f, 20.43635561f, 13.88626096f, 6234.84047149f, 10.64256298f};
const float scaler_scales[NUM_FEATURES] = {0.43848090f, 2.23345087f, 13.37981538f, 4.70485023f, 9.60728868f, 13.52942530f, 904.70063484f, 0.43511866f, 0.20652894f, 0.89562134f, 2.23530918f, 1.66032869f, 3.86593248f, 5.19538032f, 119.17124595f, 0.49746271f, 0.27582642f, 1.17785164f, 3.80559178f, 5.26900775f, 3.13734484f, 7.75847094f, 212.97004625f, 0.27281179f, 0.48182907f, 2.36566647f, 15.45066859f, 3.43805079f, 11.08204307f, 13.91323103f, 1188.02728350f, 0.48182907f};
const float model_weights[NUM_FEATURES] = {-0.17020935f, 0.40698866f, -0.42459450f, -0.40391110f, 0.18315703f, 0.27052026f, -0.40369008f, -0.20178912f, 0.92826360f, 0.78638197f, -0.29678722f, -1.30105247f, -0.34587637f, 0.15841767f, -0.25434514f, 1.32539134f, -0.85999799f, 0.90731663f, -0.27166656f, 0.17569524f, 0.98940135f, 0.28077100f, -0.00613811f, 0.43735945f, -0.03930666f, 0.31498672f, -0.47548902f, -0.76731637f, 0.02387615f, 0.20862653f, -0.33402982f, -0.03930666f};
const float model_bias = 1.67400376f;

float features[NUM_FEATURES];

// --- Funções Auxiliares para Cálculo de Features ---
float calculate_mean(float arr[], int size) {
    if (size == 0) return 0.0f;
    float sum = 0.0f;
    for (int i = 0; i < size; i++) sum += arr[i];
    return sum / size;
}

float calculate_std(float arr[], int size, float mean) {
    if (size == 0) return 0.0f;
    float sum_sq_diff = 0.0f;
    for (int i = 0; i < size; i++) {
        sum_sq_diff += powf(arr[i] - mean, 2);
    }
    return sqrtf(sum_sq_diff / size);
}

float calculate_min(float arr[], int size) {
    if (size == 0) return 0.0f;
    float min_val = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] < min_val) min_val = arr[i];
    }
    return min_val;
}

float calculate_max(float arr[], int size) {
    if (size == 0) return 0.0f;
    float max_val = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] > max_val) max_val = arr[i];
    }
    return max_val;
}

float calculate_energy(float arr[], int size) {
    float sum_sq = 0.0f;
    for (int i = 0; i < size; i++) {
        sum_sq += powf(arr[i], 2);
    }
    return sum_sq;
}

float calculate_mav(float arr[], int size) { // Mean Absolute Value
    if (size == 0) return 0.0f;
    float sum_abs = 0.0f;
    for (int i = 0; i < size; i++) {
        sum_abs += fabsf(arr[i]);
    }
    return sum_abs / size;
}

// --- Função Principal para Extração de Features ---
void extract_features_from_window() {
    // Calcular SVM para cada amostra na janela
    for (int i = 0; i < WINDOW_SIZE; i++) {
        svm_window[i] = sqrtf(powf(accel_x_window[i], 2) + powf(accel_y_window[i], 2) + powf(accel_z_window[i], 2));
    }

    float* data_streams[] = {accel_x_window, accel_y_window, accel_z_window, svm_window};
    int feature_idx = 0;

    for (int stream_idx = 0; stream_idx < 4; ++stream_idx) {
        float* current_stream = data_streams[stream_idx];
        
        float mean_val = calculate_mean(current_stream, WINDOW_SIZE);
        float std_val = calculate_std(current_stream, WINDOW_SIZE, mean_val);
        float var_val = powf(std_val, 2);
        float min_val = calculate_min(current_stream, WINDOW_SIZE);
        float max_val = calculate_max(current_stream, WINDOW_SIZE);
        float ptp_val = max_val - min_val;
        float energy_val = calculate_energy(current_stream, WINDOW_SIZE);
        float mav_val = calculate_mav(current_stream, WINDOW_SIZE);

        features[feature_idx++] = mean_val;
        features[feature_idx++] = std_val;
        features[feature_idx++] = var_val;
        features[feature_idx++] = min_val;
        features[feature_idx++] = max_val;
        features[feature_idx++] = ptp_val;
        features[feature_idx++] = energy_val;
        features[feature_idx++] = mav_val;
    }
}

// --- Função para Escalonar Features ---
void scale_current_features() {
    for (int i = 0; i < NUM_FEATURES; i++) {
        if (scaler_scales[i] == 0) {
            features[i] = (features[i] - scaler_means[i]);
        } else {
            features[i] = (features[i] - scaler_means[i]) / scaler_scales[i];
        }
    }
}

// --- Função de Predição (Regressão Logística) ---
// Retorna 1 para tremor, 0 para não tremor
int perform_prediction() {
    float raw_prediction = 0.0f;
    for (int i = 0; i < NUM_FEATURES; i++) {
        raw_prediction += model_weights[i] * features[i];
    }
    raw_prediction += model_bias;

    float probability = 1.0f / (1.0f + expf(-raw_prediction));

    // Revertendo para o limiar original de 0.9 para reduzir falsos positivos
    if (probability > 0.9) { 
        return 1; // Tremor
    } else {
        return 0; // Não Tremor
    }
}

// --- Setup ---
void setup(void) {
    Serial.begin(115200);
    while (!Serial && millis() < 2000) delay(10); // Esperar pela Serial com timeout

    Serial.println("\nIniciando Detector de Tremores Sísmicos (Versão Serial)");

    if (!mpu.begin()) {
        Serial.println("Falha ao encontrar o chip MPU6050. Verifique a conexão.");
        while (1) {
            delay(10);
        }
    }
    Serial.println("MPU6050 Encontrado!");

    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    Serial.print("Faixa do Acelerômetro configurada para: ");
    switch (mpu.getAccelerometerRange()) {
      case MPU6050_RANGE_2_G: Serial.println("+-2G"); break;
      case MPU6050_RANGE_4_G: Serial.println("+-4G"); break;
      case MPU6050_RANGE_8_G: Serial.println("+-8G"); break;
      case MPU6050_RANGE_16_G: Serial.println("+-16G"); break;
    }

    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ); 

    Serial.println("Sensor MPU6050 configurado.");
    Serial.print("Taxa de amostragem alvo: ~"); Serial.print(SAMPLING_FREQUENCY_HZ); Serial.println(" Hz");
    Serial.print("Tamanho da janela: "); Serial.print(WINDOW_SIZE); Serial.println(" amostras");
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

        if (sample_count == WINDOW_SIZE) { // Revertido para janela sem sobreposição
            // Janela está cheia, processar
            extract_features_from_window();
            scale_current_features();
            int prediction = perform_prediction();

            if (prediction == 1) {
                Serial.println("ALERTA: Tremor Detectado!");
            } else {
                Serial.println("Status: Sem Tremor.");
            }

            // Reseta a contagem para a próxima janela (sem sobreposição)
            sample_count = 0; 
        }
    }
} 