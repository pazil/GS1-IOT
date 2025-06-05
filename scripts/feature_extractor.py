import pandas as pd
import numpy as np
import os

# --- Configurações ---
INPUT_LABELED_CSV = 'final_labeled_dataset.csv'
OUTPUT_FEATURES_CSV = 'dataset_with_features.csv'

# Parâmetros de Janelamento
# Se a taxa de amostragem é 50Hz:
# 25 amostras = 0.5 segundos
# 50 amostras = 1.0 segundo
# 75 amostras = 1.5 segundos
WINDOW_SIZE = 50  # Número de amostras em cada janela
STEP_SIZE = 25    # Deslocamento para a próxima janela (WINDOW_SIZE para não sobreposição, < WINDOW_SIZE para sobreposição)
                  # Para começar, vamos usar metade da janela para ter alguma sobreposição.
# ---------------------

def extract_features_from_window(window_df):
    """Calcula features para uma única janela de dados (um DataFrame)."""
    features = {}

    for axis in ['accel_x', 'accel_y', 'accel_z']:
        data_axis = window_df[axis]
        features[f'mean_{axis}'] = np.mean(data_axis)
        features[f'std_{axis}'] = np.std(data_axis)
        features[f'var_{axis}'] = np.var(data_axis)
        features[f'min_{axis}'] = np.min(data_axis)
        features[f'max_{axis}'] = np.max(data_axis)
        features[f'ptp_{axis}'] = np.ptp(data_axis) # Peak-to-peak (max - min)
        features[f'energy_{axis}'] = np.sum(data_axis**2)
        features[f'mav_{axis}'] = np.mean(np.abs(data_axis)) # Mean Absolute Value

    # Features da Magnitude do Vetor de Aceleração (SVM)
    svm = np.sqrt(window_df['accel_x']**2 + window_df['accel_y']**2 + window_df['accel_z']**2)
    features['mean_svm'] = np.mean(svm)
    features['std_svm'] = np.std(svm)
    features['var_svm'] = np.var(svm)
    features['min_svm'] = np.min(svm)
    features['max_svm'] = np.max(svm)
    features['ptp_svm'] = np.ptp(svm)
    features['energy_svm'] = np.sum(svm**2) # Energia da magnitude
    features['mav_svm'] = np.mean(np.abs(svm))
    
    # O rótulo para a janela será o rótulo da primeira amostra da janela,
    # já que todas as amostras na janela devem ter o mesmo rótulo (vêm de um segmento já rotulado).
    # Poderíamos verificar se todos são iguais para segurança.
    # Assume-se que a coluna 'label' existe no window_df
    if 'label' in window_df.columns:
        # Verifica se todos os rótulos na janela são iguais
        if window_df['label'].nunique() == 1:
            features['label'] = window_df['label'].iloc[0]
        else:
            # Isso não deve acontecer se os segmentos foram bem definidos
            print("Aviso: Múltiplos rótulos encontrados dentro de uma janela. Usando o primeiro.")
            features['label'] = window_df['label'].iloc[0] # Ou poderia ser por maioria, ou descartar
    else:
        print("Aviso: Coluna 'label' não encontrada na janela.")
        features['label'] = -1 # Rótulo de erro/desconhecido

    return features

def main():
    print("--- Iniciando Script de Extração de Features ---")

    try:
        df_labeled = pd.read_csv(INPUT_LABELED_CSV)
        print(f"Arquivo de dados rotulados lido: {INPUT_LABELED_CSV} ({len(df_labeled)} linhas)")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de dados rotulados não encontrado: {INPUT_LABELED_CSV}")
        print("Certifique-se de que o script 'extract_labeled_segments.py' foi executado com sucesso.")
        return
    except Exception as e:
        print(f"ERRO ao ler {INPUT_LABELED_CSV}: {e}")
        return

    if 'label' not in df_labeled.columns:
        print(f"ERRO: A coluna 'label' não foi encontrada em {INPUT_LABELED_CSV}.")
        return

    all_features_list = []
    num_original_segments = 0

    # Processa os dados agrupados por timestamp_pc para tentar identificar os segmentos originais
    # e aplicar janelamento dentro de cada segmento original para não misturar dados.
    # No entanto, `final_labeled_dataset.csv` já deve ser uma concatenação de segmentos.
    # Para simplificar, vamos iterar sobre os dados. Se os segmentos fossem muito curtos,
    # precisaríamos de uma lógica mais complexa para garantir que as janelas não cruzem
    # os limites dos segmentos originais de forma inadequada.
    # Assumindo que o `final_labeled_dataset.csv` tem os segmentos concatenados, mas ainda mantém
    # a ordem cronológica por `timestamp_pc` e os rótulos consistentes dentro dos blocos.

    # Para garantir que as janelas não cruzem os limites dos segmentos originais de forma errada,
    # vamos agrupar por mudanças no rótulo, assumindo que cada mudança de rótulo representa um novo segmento.
    # Isso é uma heurística. A maneira mais robusta seria se tivéssemos um ID de segmento.
    # Se `final_labeled_dataset.csv` é apenas a concatenação dos segmentos, e cada segmento é longo o suficiente,
    # o janelamento direto com passo pode funcionar bem.

    # Heurística para identificar segmentos baseados na mudança de rótulo
    # Cria um identificador de bloco/segmento cada vez que o rótulo muda.
    df_labeled['segment_id'] = (df_labeled['label'] != df_labeled['label'].shift()).cumsum()

    processed_windows_count = 0

    for segment_id, segment_data in df_labeled.groupby('segment_id'):
        num_original_segments += 1
        # print(f"Processando segmento original ID: {segment_id} com {len(segment_data)} linhas e rótulo {segment_data['label'].iloc[0]}")
        
        start_index = 0
        while start_index + WINDOW_SIZE <= len(segment_data):
            window = segment_data.iloc[start_index : start_index + WINDOW_SIZE]
            
            if len(window) == WINDOW_SIZE: # Garante que a janela tenha o tamanho completo
                # O rótulo já está no dataframe 'window'
                # A função extract_features_from_window vai pegar o rótulo de lá.
                window_features = extract_features_from_window(window)
                all_features_list.append(window_features)
                processed_windows_count +=1
            
            start_index += STEP_SIZE

    if not all_features_list:
        print("Nenhuma feature foi extraída. Verifique o tamanho dos seus segmentos e os parâmetros de janelamento.")
        if num_original_segments > 0:
             print(f"{num_original_segments} segmentos originais identificados, mas eram muito curtos para o WINDOW_SIZE de {WINDOW_SIZE}.")
        return

    df_features = pd.DataFrame(all_features_list)
    
    # Move a coluna 'label' para o final, se ela existir e não for a última
    if 'label' in df_features.columns and df_features.columns[-1] != 'label':
        label_column = df_features.pop('label')
        df_features['label'] = label_column

    df_features.to_csv(OUTPUT_FEATURES_CSV, index=False)
    print(f"\nDataset com features extraídas salvo em: {OUTPUT_FEATURES_CSV} ({len(df_features)} janelas processadas)")
    print(f"Número de features (colunas, incluindo label): {len(df_features.columns)}")
    print("Nomes das colunas:", list(df_features.columns))
    print("Script de extração de features concluído.")

if __name__ == '__main__':
    # Certifique-se de ter pandas e numpy instalados:
    # pip install pandas numpy
    main() 