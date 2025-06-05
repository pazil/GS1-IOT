import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier # Opcional
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import pickle # Para salvar o scaler e o modelo

# --- Configurações ---
INPUT_FEATURES_CSV = 'dataset_with_features.csv'
MODEL_CHOICE = 'logistic' # Escolha: 'logistic', 'svm_linear', 'decision_tree'
TEST_SIZE_RATIO = 0.2   # Proporção do dataset para o conjunto de teste (ex: 0.2 para 20%)
RANDOM_STATE_SEED = 42  # Para reprodutibilidade

# Caminhos para salvar o scaler e o modelo treinado
SCALER_FILE_PATH = 'scaler.pkl'
MODEL_FILE_PATH = 'trained_model.pkl'
MODEL_PARAMS_FILE_PATH = 'model_parameters.txt' # Para salvar pesos e bias em formato de texto
# ---------------------

def print_model_parameters_for_c(model, scaler, model_type, feature_df_for_tree=None):
    """Imprime e salva os parâmetros do modelo e do scaler para fácil implementação em C/C++."""
    with open(MODEL_PARAMS_FILE_PATH, 'w') as f:
        f.write(f"// --- Parâmetros do Modelo ({model_type}) e Scaler para Implementação em C/C++ ---\n")
        f.write(f"// Gerado em: {pd.Timestamp.now()}\n")
        
        f.write("\n// Parâmetros do StandardScaler (média e escala/desvio_padrão):\n")
        f.write("// Use estes para escalar as features no ESP32 antes da predição\n")
        f.write(f"// Número de features que o scaler espera: {len(scaler.mean_)}\n")
        f.write("// Nomes das features (na ordem esperada pelo scaler/modelo):\n")
        # Assume que feature_df_for_tree.columns tem os nomes se for arvore, senao scaler.feature_names_in_ (se disponivel) ou um placeholder
        feature_names_list = []
        if hasattr(scaler, 'feature_names_in_'):
            feature_names_list = scaler.feature_names_in_
        elif feature_df_for_tree is not None:
            feature_names_list = list(feature_df_for_tree.columns)
        
        if feature_names_list:
            for i, name in enumerate(feature_names_list):
                f.write(f"// Feature {i}: {name}\n")
        else:
            f.write("// Nomes das features não disponíveis no scaler. Ordem é crucial.\n")

        f.write("const float scaler_means[] = {")
        for i, mean_val in enumerate(scaler.mean_):
            f.write(f"{mean_val:.8f}f")
            if i < len(scaler.mean_) - 1:
                f.write(", ")
        f.write("};\n")

        f.write("const float scaler_scales[] = {") # scale_ é o desvio padrão para StandardScaler
        for i, scale_val in enumerate(scaler.scale_):
            f.write(f"{scale_val:.8f}f")
            if i < len(scaler.scale_) - 1:
                f.write(", ")
        f.write("};\n")

        if model_type in ['logistic', 'svm_linear']:
            weights = model.coef_[0]
            bias = model.intercept_[0]
            f.write(f"\n// Parâmetros do Modelo ({model_type}):\n")
            f.write("// y_pred_raw = w[0]*f_scaled[0] + ... + w[n-1]*f_scaled[n-1] + bias\n")
            if model_type == 'logistic':
                 f.write("// P(y=1) = 1 / (1 + exp(-y_pred_raw)); Prever 1 se P(y=1) > 0.5\n")
            else: # svm_linear
                 f.write("// Prever 1 se y_pred_raw > 0 (ou outro limiar de decisão)\n")
            
            f.write("const float model_weights[] = {")
            for i, weight in enumerate(weights):
                f.write(f"{weight:.8f}f")
                if i < len(weights) - 1:
                    f.write(", ")
            f.write("};\n")
            f.write(f"const float model_bias = {bias:.8f}f;\n")
            
            # Imprimir no console também
            print("\n--- Parâmetros do Modelo e Scaler para Implementação em C/C++ ---")
            if feature_names_list:
                print(f"Nomes das Features (ordem): {feature_names_list}")
            print(f"Scaler Means: {scaler.mean_}")
            print(f"Scaler Scales (Std Devs): {scaler.scale_}")
            print(f"Model Weights: {weights}")
            print(f"Model Bias: {bias}")
        
        elif model_type == 'decision_tree':
            f.write("\n// Parâmetros da Árvore de Decisão:\n")
            f.write("// A exportação direta de uma árvore para C requer uma lógica de if/else.\n")
            f.write("// Use sklearn.tree.export_text(model, feature_names=...) para ver as regras.\n")
            from sklearn.tree import export_text
            # Se feature_df_for_tree foi passado e tem nomes de colunas, use-os.
            # Senão, os nomes podem não estar disponíveis para export_text de forma fácil.
            tree_feature_names = list(feature_df_for_tree.columns) if feature_df_for_tree is not None else None
            tree_rules = export_text(model, feature_names=tree_feature_names)
            f.write("\n// Regras da Árvore de Decisão (para referência):\n")
            f.write(tree_rules + "\n")
            print("\nRegras da Árvore de Decisão (para referência):")
            print(tree_rules)
        
        print(f"\nParâmetros e/ou regras do modelo salvos em texto em: {MODEL_PARAMS_FILE_PATH}")

def main():
    print(f"--- Iniciando Treinamento do Modelo ({MODEL_CHOICE}) ---")

    # 1. Carregar Dados
    try:
        df_features = pd.read_csv(INPUT_FEATURES_CSV)
        print(f"Dataset de features lido: {INPUT_FEATURES_CSV} ({len(df_features)} janelas, {len(df_features.columns)-1} features + label)")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de features não encontrado: {INPUT_FEATURES_CSV}")
        print("Certifique-se de que o script 'feature_extractor.py' foi executado com sucesso.")
        return
    except Exception as e:
        print(f"ERRO ao ler {INPUT_FEATURES_CSV}: {e}")
        return

    if 'label' not in df_features.columns:
        print(f"ERRO: A coluna 'label' não foi encontrada em {INPUT_FEATURES_CSV}.")
        return
    
    if df_features.isnull().sum().any():
        print("AVISO: Valores nulos (NaN) encontrados no dataset de features. Preenchendo com a média da coluna.")
        # Simples preenchimento com a média. Para um tratamento mais robusto, considere outras estratégias.
        for col in df_features.columns[df_features.isnull().any()].tolist():
            if col != 'label': # Não preenche a coluna de label
                df_features[col] = df_features[col].fillna(df_features[col].mean())
        if df_features.isnull().sum().any():
            print("ERRO: Ainda há NaNs após o preenchimento. Verifique os dados.")
            # Opcionalmente, remover linhas com NaN: df_features.dropna(inplace=True)
            # Ou usar um preenchedor mais sofisticado do sklearn.impute
            # Por agora, vamos parar se o preenchimento simples não funcionar.
            df_features.dropna(inplace=True) # Remove linhas com NaN restantes
            print(f"Linhas com NaNs restantes foram removidas. Novo tamanho do dataset: {len(df_features)}")
            if len(df_features) == 0:
                print("Dataset vazio após remoção de NaNs. Saindo.")
                return

    X = df_features.drop('label', axis=1)
    y = df_features['label']
    feature_names = list(X.columns)

    print(f"Número de amostras: {len(X)}")
    print(f"Distribuição das classes:\n{y.value_counts(normalize=True)}")

    # 2. Dividir em Treino e Teste
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=TEST_SIZE_RATIO, random_state=RANDOM_STATE_SEED, stratify=y)
    print(f"Dataset dividido em {len(X_train)} amostras de treino e {len(X_test)} de teste.")

    # 3. Escalonamento de Features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test) # Usa o mesmo scaler treinado no X_train
    print("Features escalonadas usando StandardScaler.")

    # Salva o scaler treinado
    with open(SCALER_FILE_PATH, 'wb') as f_scaler:
        pickle.dump(scaler, f_scaler)
    print(f"Scaler treinado salvo em: {SCALER_FILE_PATH}")

    # 4. Escolher e Treinar o Modelo
    if MODEL_CHOICE == 'logistic':
        model = LogisticRegression(solver='liblinear', random_state=RANDOM_STATE_SEED, class_weight='balanced')
    elif MODEL_CHOICE == 'svm_linear':
        model = SVC(kernel='linear', probability=True, random_state=RANDOM_STATE_SEED, class_weight='balanced')
    elif MODEL_CHOICE == 'decision_tree':
        # Para árvores, o escalonamento não é estritamente necessário, mas não prejudica.
        # class_weight='balanced' pode ajudar se as classes forem desbalanceadas.
        model = DecisionTreeClassifier(random_state=RANDOM_STATE_SEED, max_depth=5, class_weight='balanced') # max_depth pequeno para embarque
    else:
        print(f"ERRO: Escolha de modelo inválida: {MODEL_CHOICE}. Use 'logistic', 'svm_linear', ou 'decision_tree'.")
        return
    
    print(f"Treinando modelo: {MODEL_CHOICE}...")
    model.fit(X_train_scaled, y_train)
    print("Modelo treinado.")

    # Salva o modelo treinado
    with open(MODEL_FILE_PATH, 'wb') as f_model:
        pickle.dump(model, f_model)
    print(f"Modelo treinado salvo em: {MODEL_FILE_PATH}")

    # 5. Avaliação no Conjunto de Teste
    print("\n--- Avaliação no Conjunto de Teste ---")
    y_pred_test = model.predict(X_test_scaled)
    print(f"Acurácia no Teste: {accuracy_score(y_test, y_pred_test):.4f}")
    print("\nMatriz de Confusão (Teste):")
    # tn, fp, fn, tp = confusion_matrix(y_test, y_pred_test).ravel()
    # print(f"  Verdadeiros Negativos (Não Tremor OK): {tn}")
    # print(f"  Falsos Positivos (Não Tremor -> Tremor): {fp}")
    # print(f"  Falsos Negativos (Tremor -> Não Tremor): {fn}")
    # print(f"  Verdadeiros Positivos (Tremor OK): {tp}")
    conf_matrix = confusion_matrix(y_test, y_pred_test)
    print(conf_matrix)
    # Labels para a matriz de confusão (opcional, para melhor visualização com seaborn depois)
    # print(pd.DataFrame(conf_matrix, index=model.classes_ + ['Actual'], columns=model.classes_ + ['Predicted']))

    print("\nRelatório de Classificação (Teste):")
    print(classification_report(y_test, y_pred_test, target_names=['NaoTremor (0)', 'Tremor (1)']))

    # 6. Validação Cruzada (no conjunto de treino completo para uma avaliação mais robusta da generalização do modelo)
    print("\n--- Validação Cruzada (no conjunto de treino escalonado) ---")
    # Recria o scaler e escala o X completo para validação cruzada, ou usa X_train_scaled e y_train
    # Para ser mais preciso sobre o desempenho esperado em dados não vistos, 
    # a validação cruzada deve ser feita no conjunto de dados de treino ANTES de treinar o modelo final em todo o treino.
    # Aqui, estamos fazendo no X_train_scaled para avaliar o processo de modelagem.
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='accuracy') # 5 folds
    print(f"Acurácias da Validação Cruzada (5-fold): {cv_scores}")
    print(f"Acurácia Média da Validação Cruzada: {np.mean(cv_scores):.4f} (+/- {np.std(cv_scores):.4f})")

    # 7. Salvar Parâmetros do Modelo para C/C++
    # Passar X (com nomes de colunas) para export_text se for árvore de decisão
    if MODEL_CHOICE == 'decision_tree':
        # É preciso passar X com nomes de colunas para export_text
        # Se X foi modificado (ex: escalado), os nomes das features originais devem ser usados
        # Aqui, X_train (antes de escalar) tem os nomes corretos das features.
        print_model_parameters_for_c(model, scaler, MODEL_CHOICE, X_train)
    else:
        print_model_parameters_for_c(model, scaler, MODEL_CHOICE)

    print("\nScript de treinamento de modelo concluído.")

if __name__ == '__main__':
    main() 