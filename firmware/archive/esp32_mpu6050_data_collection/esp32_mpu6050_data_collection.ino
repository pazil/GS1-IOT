#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

Adafruit_MPU6050 mpu;

// Marcadores de Evento. Estes serão enviados UMA VEZ quando o comando correspondente for recebido.
volatile int eventMarker = 0; // 0 = Nenhum, 1 = Início de Evento, 2 = Fim de Evento
volatile bool sendMarkerFlag = false;

void setup(void) {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  if (!mpu.begin()) {
    Serial.println("Falha ao encontrar o chip MPU6050");
    while (1) {
      delay(10);
    }
  }
  Serial.println("MPU6050 Encontrado!");

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  Serial.println("\nESP32 Pronto para Coleta de Dados com Marcadores.");
  Serial.println("Aguardando comandos ('b'=begin event, 'e'=end event) via Serial...");
  Serial.println("Formato da saída de dados: Ax,Ay,Az,EventMarker (0=normal, 1=inicio, 2=fim)");
  Serial.println("----------------------------------------------------");
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    switch (command) {
      case 'b': // Comando para INÍCIO de evento
        eventMarker = 1;
        sendMarkerFlag = true;
        Serial.println("INFO: Marcador INÍCIO de evento recebido.");
        break;
      case 'e': // Comando para FIM de evento
        eventMarker = 2;
        sendMarkerFlag = true;
        Serial.println("INFO: Marcador FIM de evento recebido.");
        break;
      // O comando 's' (stop) será gerenciado pelo script Python, 
      // que simplesmente parará de ler da serial ou fechará a porta.
    }
  }

  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  Serial.print(a.acceleration.x, 6);
  Serial.print(",");
  Serial.print(a.acceleration.y, 6);
  Serial.print(",");
  Serial.print(a.acceleration.z, 6);
  Serial.print(",");

  if (sendMarkerFlag) {
    Serial.println(eventMarker);
    sendMarkerFlag = false; // Reseta o flag para que o marcador seja enviado apenas uma vez
    eventMarker = 0;      // Volta para o marcador padrão (0) para as próximas linhas normais
  } else {
    Serial.println("0"); // Marcador padrão para dados normais
  }
  
  delay(20); // Taxa de amostragem de 50Hz
} 