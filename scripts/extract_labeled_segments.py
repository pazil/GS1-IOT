import csv
import os
import pandas as pd # Usaremos pandas para facilitar a leitura e manipulação dos CSVs

# --- Configurações ---
INPUT_CSV_NO_TREMOR = 'raw_sensor_log_with_markers_0.csv' # Seu arquivo de NÃO TREMOR
INPUT_CSV_TREMOR = 'raw_sensor_log_with_markers_1.csv'    # Seu arquivo de TREMOR

OUTPUT_SEGMENTS_BASE_DIR = 'dataset_segments'
OUTPUT_NO_TREMOR_DIR = os.path.join(OUTPUT_SEGMENTS_BASE_DIR, 'no_tremor')
OUTPUT_TREMOR_DIR = os.path.join(OUTPUT_SEGMENTS_BASE_DIR, 'tremor')

FINAL_LABELED_CSV = 'final_labeled_dataset.csv'

# Marcadores definidos no script ESP32 e Python de coleta
MARKER_START_EVENT = 1
MARKER_END_EVENT = 2
# ---------------------

def ensure_dir(directory):
    """Cria o diretório se ele não existir."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Diretório criado: {directory}")

def process_input_csv(input_filename, label, output_dir_segments):
    """
    Processa um arquivo CSV de entrada, extrai segmentos baseados nos marcadores,
    salva segmentos individualmente e retorna uma lista de dataframes dos segmentos.
    """
    print(f"\nProcessando arquivo: {input_filename} com rótulo: {label}")
    all_segments_data = [] # Lista para armazenar dataframes de cada segmento deste arquivo
    segment_counter = 0

    try:
        df = pd.read_csv(input_filename)
    except FileNotFoundError:
        print(f"ERRO: Arquivo não encontrado: {input_filename}")
        return all_segments_data # Retorna lista vazia
    except pd.errors.EmptyDataError:
        print(f"AVISO: Arquivo está vazio: {input_filename}")
        return all_segments_data
    except Exception as e:
        print(f"ERRO ao ler {input_filename}: {e}")
        return all_segments_data

    # Verifica se a coluna de marcadores existe
    if 'event_marker_from_esp32' not in df.columns:
        print(f"ERRO: Coluna 'event_marker_from_esp32' não encontrada em {input_filename}.")
        return all_segments_data

    in_event_segment = False
    current_segment_start_index = -1

    for index, row in df.iterrows():
        marker = row['event_marker_from_esp32']

        if marker == MARKER_START_EVENT:
            if in_event_segment:
                print(f"Aviso em {input_filename} [linha {index+2}]: Marcador de INÍCIO encontrado dentro de um segmento já iniciado. Ignorando marcador de início anterior.")
            current_segment_start_index = index
            in_event_segment = True
            # print(f"DEBUG: Início de segmento encontrado na linha {index} do CSV (índice pandas {index})")
        
        elif marker == MARKER_END_EVENT:
            if in_event_segment:
                segment_df = df.iloc[current_segment_start_index : index + 1].copy() # Inclui a linha do marcador de fim
                # print(f"DEBUG: Fim de segmento encontrado na linha {index} do CSV. Segmento de {current_segment_start_index} a {index}")
                
                if not segment_df.empty:
                    segment_counter += 1
                    # Selecionar apenas as colunas desejadas para os arquivos de segmento individuais
                    segment_to_save = segment_df[['timestamp_pc', 'accel_x', 'accel_y', 'accel_z']].copy()
                    
                    segment_filename = os.path.join(output_dir_segments, f'segment_label_{label}_{segment_counter:03d}.csv')
                    segment_to_save.to_csv(segment_filename, index=False)
                    print(f"  Segmento {segment_counter} salvo em: {segment_filename} ({len(segment_to_save)} linhas)")
                    
                    # Para o dataset final, adicionamos a coluna de rótulo
                    segment_df['label'] = label
                    all_segments_data.append(segment_df[['timestamp_pc', 'accel_x', 'accel_y', 'accel_z', 'label']])
                else:
                    print(f"Aviso em {input_filename} [linha {index+2}]: Segmento vazio encontrado e ignorado.")
                
                in_event_segment = False
                current_segment_start_index = -1
            else:
                print(f"Aviso em {input_filename} [linha {index+2}]: Marcador de FIM encontrado sem um INÍCIO de segmento correspondente. Ignorando.")
    
    if in_event_segment:
        print(f"Aviso em {input_filename}: O arquivo terminou, mas um segmento estava em andamento (marcador de INÍCIO sem FIM). Segmento final não foi salvo.")

    print(f"Total de {segment_counter} segmentos extraídos de {input_filename}.")
    return all_segments_data

def main():
    print("--- Iniciando Script de Extração e Rotulagem de Segmentos ---")

    # Garante que os diretórios de saída existam
    ensure_dir(OUTPUT_SEGMENTS_BASE_DIR)
    ensure_dir(OUTPUT_NO_TREMOR_DIR)
    ensure_dir(OUTPUT_TREMOR_DIR)

    # Processa o arquivo de não tremor
    no_tremor_segments = process_input_csv(INPUT_CSV_NO_TREMOR, 0, OUTPUT_NO_TREMOR_DIR)
    
    # Processa o arquivo de tremor
    tremor_segments = process_input_csv(INPUT_CSV_TREMOR, 1, OUTPUT_TREMOR_DIR)

    # Combina todos os segmentos em um único DataFrame para o CSV final
    all_labeled_data = []
    if no_tremor_segments:
        all_labeled_data.extend(no_tremor_segments)
    if tremor_segments:
        all_labeled_data.extend(tremor_segments)

    if not all_labeled_data:
        print("\nNenhum segmento foi extraído de nenhum dos arquivos. O CSV final não será criado.")
        print("Verifique seus arquivos de entrada e os marcadores.")
        return

    final_df = pd.concat(all_labeled_data, ignore_index=True)
    
    # Ordena pelo timestamp original do PC para manter a ordem cronológica, se desejado (opcional)
    # final_df = final_df.sort_values(by='timestamp_pc').reset_index(drop=True)
    
    # Salva o dataset final consolidado e rotulado
    final_df.to_csv(FINAL_LABELED_CSV, index=False)
    print(f"\nDataset final consolidado e rotulado salvo em: {FINAL_LABELED_CSV} ({len(final_df)} linhas totais)")
    print("Colunas no dataset final:", list(final_df.columns))
    print("Script concluído.")

if __name__ == '__main__':
    # Antes de rodar, certifique-se de ter o pandas instalado: pip install pandas
    main() 