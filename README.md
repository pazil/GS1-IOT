# Projeto Detector de Tremores Sísmicos com ESP32 e IA Embarcada

## Integrantes do Grupo

- **Paulo Carvalho Ruiz Borba** (RM554562)
- **Herbertt Di Franco Marques** (RM556640)
- **Lorena Bauer Nogueira** (RM555272)

---
## Descrição

Este projeto implementa um sistema de detecção de tremores sísmicos utilizando um microcontrolador ESP32, um sensor acelerômetro/giroscópio MPU6050 e um modelo de Machine Learning (Regressão Logística) embarcado para realizar a inferência diretamente no dispositivo (Edge Computing). Quando um tremor é detectado, o ESP32 pode operar de forma autônoma, imprimindo alertas na serial, ou conectar-se a uma rede Wi-Fi para enviar um alerta para um servidor central.

## Funcionalidades Principais

*   Leitura de dados do acelerômetro (MPU6050) pelo ESP32.
*   Taxa de amostragem configurável (definida em 50Hz).
*   Coleta de dados para criação de dataset (eventos de "tremor" e "não tremor").
*   Scripts Python para coleta, processamento de dados, extração de features e treinamento do modelo.
*   Modelo de Regressão Logística treinado para classificar os eventos.
*   Embarque dos parâmetros do modelo e do scaler no ESP32 para inferência local.
*   Duas versões de firmware para o ESP32:
    *   Detector com saída serial.
    *   Detector com saída serial e alerta via Wi-Fi para um servidor Python.
*   Servidor Python simples para receber e exibir os alertas de tremor.

## Hardware Necessário

*   ESP32 (qualquer variante com Wi-Fi para a versão com alertas de rede).
*   Sensor Acelerômetro/Giroscópio MPU6050.
*   Jumpers para conexão.
*   Cabo Micro-USB.

## Software e Bibliotecas

*   **Arduino IDE:** Para compilar e carregar o firmware no ESP32.
    *   Placa ESP32 Dev Module (ou similar) configurada na IDE.
    *   Biblioteca Arduino: `Adafruit MPU6050` (e suas dependências, como `Adafruit Unified Sensor` e `Wire`).
    *   Biblioteca Arduino: `WiFi` (para a versão com Wi-Fi).
    *   Biblioteca Arduino: `HTTPClient` (para a versão com Wi-Fi).
*   **Python 3.x:** Para os scripts de coleta, processamento e treinamento.
    *   Bibliotecas Python (instalar via `pip install <nome_da_biblioteca>`):
        *   `pyserial` (para `marker_data_collector.py`)
        *   `pandas`
        *   `numpy`
        *   `scikit-learn`
        *   `matplotlib` (para `live_plotter.py`)

## Estrutura do Projeto

A estrutura de pastas foi organizada para separar dados, firmware, scripts e parâmetros do modelo.

```
gs1/
├── alert_server.py           # Servidor Python para receber alertas Wi-Fi
├── data/                     # Dados do projeto
│   ├── processed_data/       # Arquivos CSV processados
│   │   ├── dataset_with_features.csv
│   │   └── final_labeled_dataset.csv
│   ├── raw_data/             # Arquivos CSV brutos da coleta inicial
│   │   ├── raw_sensor_log_with_markers_0.csv
│   │   └── raw_sensor_log_with_markers_1.csv
│   └── segments/             # Segmentos rotulados extraídos
│       ├── no_tremor/
│       └── tremor/
├── firmware/                 # Códigos do ESP32
│   ├── archive/              # Sketches mais antigos para referência
│   ├── esp32_seismic_detector_serial/ # Detector com saída via Serial
│   │   └── esp32_seismic_detector_serial.ino
│   └── esp32_seismic_detector_wifi/   # Detector com alerta via Wi-Fi
│       └── esp32_seismic_detector_wifi.ino
├── logistic_model_parameters/ # Parâmetros do modelo treinado
│   ├── model_parameters.txt    # Pesos e bias para o ESP32 (C++)
│   ├── scaler.pkl              # Objeto Scaler salvo (Python)
│   └── trained_model.pkl       # Modelo salvo (Python)
├── scripts/                  # Scripts Python do pipeline
│   ├── live_plotter.py
│   ├── marker_data_collector.py
│   ├── extract_labeled_segments.py
│   ├── feature_extractor.py
│   └── train_model.py
└── README.md                 # Este arquivo
```

## Passos para Configuração e Uso

**AVISO IMPORTANTE:** Para compilar os sketches na Arduino IDE, abra o arquivo `.ino` desejado diretamente. A IDE gerenciará a pasta do projeto. Certifique-se de que cada sketch `.ino` principal está isolado em seu próprio diretório, como na estrutura acima, para evitar conflitos de compilação.

**1. Configuração do Hardware:**
   - Conecte o MPU6050 ao ESP32 via I2C:
     - MPU6050 VCC -> ESP32 3.3V
     - MPU6050 GND -> ESP32 GND
     - MPU6050 SCL -> ESP32 GPIO22
     - MPU6050 SDA -> ESP32 GPIO21

**2. Coleta de Dados (Se for gerar um novo dataset):**
   a. **ESP32:** Carregue o sketch `firmware/archive/esp32_mpu6050_data_collection/esp32_mpu6050_data_collection.ino` no ESP32 (este sketch foi usado na fase de coleta original; pode precisar de ajustes se for reutilizado).
   b. **Python:** Execute o script `scripts/marker_data_collector.py`.
      - Siga as instruções no console para marcar eventos de tremor ('b' para iniciar, 'e' para finalizar) e não tremor.
      - Os dados serão salvos em arquivos como `raw_sensor_log_with_markers_X.csv`.
   c. Mova os arquivos CSV gerados para a pasta `data/raw_data/` (ex: `raw_sensor_log_with_markers_0.csv` para não tremor, `raw_sensor_log_with_markers_1.csv` para tremor).

**3. Processamento dos Dados e Extração de Features:**
   a. Execute o script `scripts/extract_labeled_segments.py`.
      - Ele lerá os arquivos de `data/raw_data/`.
      - Salvará segmentos individuais em `data/segments/` (nas subpastas `tremor` e `no_tremor`).
      - Criará `data/processed_data/final_labeled_dataset.csv`.
   b. Execute o script `scripts/feature_extractor.py`.
      - Ele lerá `data/processed_data/final_labeled_dataset.csv`.
      - Calculará as features e salvará em `data/processed_data/dataset_with_features.csv`.

**4. Treinamento do Modelo:**
   a. Certifique-se de que `dataset_with_features.csv` está no diretório `data/processed_data/`.
   b. Navegue até a pasta `scripts/` e execute o script `train_model.py`.
      ```sh
      cd scripts
      python train_model.py
      ```
   c. O script lerá o dataset, treinará o modelo e o scaler, e salvará os três arquivos de saída (`model_parameters.txt`, `scaler.pkl`, `trained_model.pkl`) na pasta `logistic_model_parameters/`.

**5. Firmware do Detector no ESP32:**

   *   **Opção A: Detector com Saída Serial**
       1.  Abra o sketch `firmware/esp32_seismic_detector_serial/esp32_seismic_detector_serial.ino` na Arduino IDE.
       2.  Compile e carregue no ESP32.
       3.  Abra o Monitor Serial (115200 bps) para ver os alertas.

   *   **Opção B: Detector com Alerta Wi-Fi**
       1.  Abra o sketch `firmware/esp32_seismic_detector_wifi/esp32_seismic_detector_wifi.ino` na Arduino IDE.
       2.  **Configure suas credenciais de Wi-Fi e o IP do servidor no topo do arquivo:**
           ```cpp
           const char* WIFI_SSID = "SEU_NOME_DE_REDE_AQUI";
           const char* WIFI_PASSWORD = "SUA_SENHA_DE_REDE_AQUI";
           const char* SERVER_IP = "IP_DO_SEU_COMPUTADOR_AQUI"; // Ex: "192.168.1.10"
           const int SERVER_PORT = 8080; // Deve coincidir com o servidor Python
           ```
       3.  Compile e carregue no ESP32.
       4.  Abra o Monitor Serial (115200 bps) para ver o status da conexão Wi-Fi e os alertas locais.

**6. Servidor de Alertas Python (para a Opção B do firmware):**
   a. No seu computador, abra um terminal ou prompt de comando.
   b. Navegue até a pasta raiz do projeto (`gs1/`).
   c. Execute o servidor: `python alert_server.py`
   d. O servidor começará a escutar na porta `8080` (ou a porta configurada).
   e. Quando o ESP32 detectar um tremor, ele enviará um alerta HTTP, e o servidor Python exibirá a mensagem no console.
   f. Certifique-se de que seu firewall permite conexões na porta especificada.

---

*Este README foi gerado com a assistência de uma IA.* 
