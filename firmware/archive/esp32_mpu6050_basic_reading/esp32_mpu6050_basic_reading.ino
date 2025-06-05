#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

Adafruit_MPU6050 mpu;

void setup(void) {
  Serial.begin(115200);
  while (!Serial) {
    delay(10); // Aguarda a porta serial conectar.
  }

  // Inicializa o MPU6050
  if (!mpu.begin()) {
    Serial.println("Falha ao encontrar o chip MPU6050");
    while (1) {
      delay(10);
    }
  }
  Serial.println("MPU6050 Encontrado!");

  // Configurações opcionais (exemplos):
  // mpu.setAccelerometerRange(MPU6050_RANGE_8_G); // Configura a faixa do acelerômetro
  // mpu.setGyroRange(MPU6050_RANGE_500_DEG);    // Configura a faixa do giroscópio
  // mpu.setFilterBandwidth(MPU6050_BAND_21_HZ); // Configura o filtro passa-baixa

  Serial.println("");
  delay(100);
}

void loop() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // Imprime os dados do Acelerômetro
  Serial.print("AcelX: ");
  Serial.print(a.acceleration.x);
  Serial.print(", AcelY: ");
  Serial.print(a.acceleration.y);
  Serial.print(", AcelZ: ");
  Serial.print(a.acceleration.z);
  Serial.print(" m/s^2");

  // Imprime os dados do Giroscópio
  Serial.print(" | GiroX: ");
  Serial.print(g.gyro.x);
  Serial.print(", GiroY: ");
  Serial.print(g.gyro.y);
  Serial.print(", GiroZ: ");
  Serial.print(g.gyro.z);
  Serial.println(" rad/s");

  // Imprime a Temperatura
  // Serial.print("Temperatura: ");
  // Serial.print(temp.temperature);
  // Serial.println(" degC");

  delay(500); // Aguarda meio segundo entre as leituras
} 