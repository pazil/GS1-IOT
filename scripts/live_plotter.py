import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time

# --- Configurações ---
SERIAL_PORT = 'COM3'  # MUDE AQUI para a porta serial correta do seu ESP32
BAUD_RATE = 115200
MAX_DATA_POINTS = 100 # Número de pontos de dados a serem exibidos no gráfico
# --------------------

# Deques para armazenar os dados dos eixos
time_data = deque(maxlen=MAX_DATA_POINTS)
accel_x_data = deque(maxlen=MAX_DATA_POINTS)
accel_y_data = deque(maxlen=MAX_DATA_POINTS)
accel_z_data = deque(maxlen=MAX_DATA_POINTS)

# Variável para o tempo inicial
start_time = time.time()

# Cria a figura e os eixos para o plot
fig, ax = plt.subplots()
line_x, = ax.plot([], [], lw=2, label='Accel X')
line_y, = ax.plot([], [], lw=2, label='Accel Y')
line_z, = ax.plot([], [], lw=2, label='Accel Z')

def init_plot():
    """Inicializa o gráfico."""
    ax.set_xlabel('Tempo (s)')
    ax.set_ylabel('Aceleração (m/s^2)')
    ax.set_title('Leituras do Acelerômetro MPU6050 em Tempo Real')
    ax.legend(loc='upper left')
    ax.grid(True)
    ax.set_ylim(-20, 20) # Ajuste o limite Y conforme necessário (MPU6050_RANGE_8G é +/- 78 m/s^2)
                         # mas os valores típicos durante tremores podem ser menores.
                         # Comece com uma faixa menor e ajuste. +/-2g é ~ +/- 19.6 m/s^2
    # Para RANGE_8_G, os valores podem ir até +/- 8 * 9.81.
    # Vamos usar um range mais prático para visualização inicial.
    # Se os dados estiverem saindo da tela, aumente este valor.
    # Por exemplo, para +/- 2g, use ax.set_ylim(-25, 25)
    # Para +/- 8g, use ax.set_ylim(-80, 80)
    # Começando com +/- 20 para melhor visualização de variações menores.
    return line_x, line_y, line_z

def update_plot(frame, ser):
    """Atualiza os dados do gráfico. Esta função é chamada pela FuncAnimation."""
    global start_time
    try:
        if ser.in_waiting > 0:
            line_serial = ser.readline().decode('utf-8').strip()
            
            # Tenta processar apenas linhas que parecem ser dados
            # Formato esperado do ESP32: "ax,ay,az,label"
            parts = line_serial.split(',')
            if len(parts) >= 3: # Precisa de pelo menos Ax, Ay, Az
                try:
                    ax_val = float(parts[0])
                    ay_val = float(parts[1])
                    az_val = float(parts[2])
                    
                    current_time = time.time() - start_time

                    time_data.append(current_time)
                    accel_x_data.append(ax_val)
                    accel_y_data.append(ay_val)
                    accel_z_data.append(az_val)

                    # Ajusta os limites do eixo X dinamicamente
                    if time_data:
                        ax.set_xlim(time_data[0], time_data[-1] + 1) # Adiciona 1s de margem

                    line_x.set_data(time_data, accel_x_data)
                    line_y.set_data(time_data, accel_y_data)
                    line_z.set_data(time_data, accel_z_data)
                    
                    # Reajusta os limites Y se necessário (opcional, pode deixar fixo)
                    # all_data = list(accel_x_data) + list(accel_y_data) + list(accel_z_data)
                    # if all_data:
                    #    ax.set_ylim(min(all_data) - 1, max(all_data) + 1)

                except ValueError:
                    # Ignora linhas que não podem ser convertidas para float (ex: mensagens de status)
                    # print(f"Ignorando linha não numérica: {line_serial}")
                    pass
            # else:
                # print(f"ESP32 (status ou formato inesperado): {line_serial}")

    except serial.SerialException as e:
        print(f"Erro de comunicação serial: {e}")
        # Aqui você pode tentar fechar e reabrir a porta, ou simplesmente parar a animação.
        # Por simplicidade, a animação continuará tentando.
    except Exception as e:
        print(f"Erro inesperado em update_plot: {e}")
        
    return line_x, line_y, line_z

def main():
    print("--- Live Plotter para MPU6050 ---")
    print(f"Tentando conectar à porta: {SERIAL_PORT} a {BAUD_RATE} baud.")
    print(f"Certifique-se de que o ESP32 está enviando dados (Ax,Ay,Az,Label).")
    print("Você pode precisar enviar 't' ou 'n' para o ESP32 usando o Monitor Serial do Arduino IDE")
    print("ou o script 'data_collector_script.py' ANTES de rodar este plotter, e depois fechar o Monitor Serial.")
    print("Para parar o plotter, feche a janela do gráfico.")

    ser = None
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05) # Timeout pequeno para não bloquear
        print(f"Conectado a {SERIAL_PORT}.")
    except serial.SerialException as e:
        print(f"Erro ao abrir a porta serial {SERIAL_PORT}: {e}")
        print("Verifique se a porta está correta e não está sendo usada por outro programa.")
        return

    # Configura a animação
    # O intervalo (interval) é em milissegundos. 20ms = 50Hz. 
    # Ajuste conforme a taxa de envio do ESP32 e a performance desejada.
    # Se o ESP32 envia a 50Hz (delay de 20ms), um intervalo de 20-50ms aqui é razoável.
    ani = animation.FuncAnimation(fig, update_plot, fargs=(ser,), init_func=init_plot,
                                  frames=None, interval=30, blit=True, save_count=MAX_DATA_POINTS)
    
    plt.show() # Mostra o gráfico e inicia o loop de eventos do matplotlib

    # Quando a janela do matplotlib é fechada, o código abaixo é executado
    print("Plotter fechado.")
    if ser and ser.is_open:
        # Envia 's' para o ESP32 parar de enviar dados, se ele estiver usando o sketch de coleta
        print("Enviando comando 's' (parar) para o ESP32...")
        try:
            ser.write(b's\n') # Adiciona newline se o ESP32 espera por isso
        except Exception as e:
            print(f"Não foi possível enviar comando 's' ao ESP32: {e}")
        ser.close()
        print("Porta serial fechada.")

if __name__ == '__main__':
    main() 