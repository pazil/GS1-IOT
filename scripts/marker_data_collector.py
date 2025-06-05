import serial
import csv
import time
import datetime

# --- Configurações ---
SERIAL_PORT = 'COM3'  # MUDE AQUI para a porta serial correta do seu ESP32
BAUD_RATE = 115200
CSV_FILENAME = 'raw_sensor_log_with_markers_2.csv'
# ---------------------

# Cabeçalho do arquivo CSV
# EventMarkerFromESP32: 0 = normal, 1 = início de evento, 2 = fim de evento
CSV_HEADER = ['timestamp_pc', 'accel_x', 'accel_y', 'accel_z', 'event_marker_from_esp32']

def print_instructions():
    print("\n--- Script de Coleta de Dados com Marcadores de Evento ---")
    print(f"Escutando na porta: {SERIAL_PORT} a {BAUD_RATE} baud")
    print(f"Salvando dados em: {CSV_FILENAME}")
    print("Comandos (digite no console e pressione Enter):")
    print("  'b' - para marcar INÍCIO de um evento de interesse")
    print("  'e' - para marcar FIM de um evento de interesse")
    print("  'q' - para SAIR do script e salvar os dados")
    print("-----------------------------------------")
    print("Simule os eventos (tremores ou não tremores) e use 'b' e 'e' para delimitá-los.")
    print("A rotulagem (se é tremor ou não) será feita em uma etapa posterior.")
    print("AVISO: A coleta de dados pausa brevemente enquanto espera por seu comando.")

def run_marker_collection():
    print_instructions()
    ser = None
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05) # Timeout curto
        print(f"Conectado a {SERIAL_PORT}.")
        # Dá tempo para o ESP32 enviar msgs iniciais e para a conexão estabilizar
        time.sleep(0.5) 
        ser.reset_input_buffer() # Limpa quaisquer dados antigos no buffer de entrada
        print("Buffer de entrada da serial limpo.")

        with open(CSV_FILENAME, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(CSV_HEADER)
            print(f"Arquivo {CSV_FILENAME} aberto. Coleta iniciada.")
            print("\nDigite 'b' para INÍCIO de evento, 'e' para FIM de evento, 'q' para SAIR.")

            while True: # Loop principal para comandos e dados
                # 1. Prioridade: Verificar e processar todos os dados pendentes do ESP32
                while ser.in_waiting > 0:
                    try:
                        line_bytes = ser.readline()
                        line_str = line_bytes.decode('utf-8').strip()
                        
                        # Imprime mensagens de INFO do ESP32, mas não as processa como dados
                        if line_str.startswith("INFO:"):
                            print(f"ESP32: {line_str}")
                            continue # Pula para a próxima linha da serial
                        if not line_str: # Ignora linhas completamente vazias
                            continue

                        parts = line_str.split(',')
                        if len(parts) == 4: # Ax, Ay, Az, EventMarkerFromESP
                            try:
                                pc_timestamp = datetime.datetime.now().isoformat()
                                accel_x = float(parts[0])
                                accel_y = float(parts[1])
                                accel_z = float(parts[2])
                                marker_from_esp = int(parts[3])
                                # Salva a linha no CSV
                                csv_writer.writerow([pc_timestamp, accel_x, accel_y, accel_z, marker_from_esp])
                            except ValueError:
                                # Não imprime aviso para cada linha malformada para não poluir o console
                                # durante a coleta de alta velocidade, a menos que seja uma linha não vazia.
                                if line_str: 
                                     print(f"Aviso: Erro ao converter dados da linha: '{line_str}'")
                        else: # Linhas com formato inesperado (não INFO, não vazias, não 4 partes)
                            if line_str: # Só imprime aviso se a linha não for vazia
                               print(f"Aviso: Formato de linha inesperado: '{line_str}'")
                            
                    except UnicodeDecodeError:
                        # print("Aviso: Erro de decodificação Unicode ao ler da serial.")
                        pass # Ignorar silenciosamente
                    except Exception as read_ex:
                        print(f"Erro ao ler/processar dados da serial: {read_ex}")
                
                # 2. Verificar entrada do usuário para comandos (input() é bloqueante)
                try:
                    # Este input irá pausar a execução aqui até que o usuário pressione Enter.
                    user_input = input("Comando (b, e, q): ").strip().lower()
                    if user_input == 'b':
                        ser.write(b'b')
                        print("-> Comando 'b' (INÍCIO evento) enviado ao ESP32.")
                    elif user_input == 'e':
                        ser.write(b'e')
                        print("-> Comando 'e' (FIM evento) enviado ao ESP32.")
                    elif user_input == 'q':
                        print("Comando 'q' (SAIR) recebido. Finalizando...")
                        break # Sai do loop principal (while True)
                    elif user_input: # Se o usuário digitou algo, mas não é um comando válido
                        print(f"Comando '{user_input}' desconhecido. Use 'b', 'e', ou 'q'.")
                    # Se o usuário apenas pressionar Enter (input vazio), o loop continua e lê mais dados.
                    
                except EOFError: # Ocorre se o stream de input for fechado (ex: script redirecionado)
                    print("Fim da entrada (EOF). Saindo...")
                    break 
                
    except KeyboardInterrupt:
        print("\nColeta interrompida pelo usuário (Ctrl+C).")
    except serial.SerialException as e_ser:
        print(f"Erro de comunicação serial: {e_ser}")
    except Exception as e_gen:
        print(f"Um erro geral ocorreu: {e_gen}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Porta serial fechada.")
        print(f"Coleta de dados finalizada. Verifique o arquivo '{CSV_FILENAME}'.")

if __name__ == '__main__':
    run_marker_collection()