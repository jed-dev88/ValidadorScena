import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
import io

def load_data(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, 
                        sep=';', 
                        encoding='utf-8')
        return df, None
    except Exception as e:
        return None, f"Erro ao carregar arquivo: {str(e)}"

def convert_datetime(date_str, time_str):
    if pd.isna(date_str) or pd.isna(time_str):
        return None
    try:
        # Converte a data do formato DD/MM/YYYY
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        # Converte a hora do formato HH:MM
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        # Combina data e hora
        return datetime.combine(date_obj.date(), time_obj)
    except Exception as e:
        print(f"Erro na conversão: {date_str} {time_str} - {str(e)}")
        return None

def validate_flights(df):
    violations = {
        'status_violations': [],
        'time_violations': [],
        'station_violations': [],
        'registration_violations': [],
        'movement_violations': [],
        'operation_violations': [],
        'assoc_time_violations': []
    }
    
    # Remove linhas CAN e BOR
    df = df[~df['Sit.'].isin(['CAN', 'BOR'])]
    
    # Valida cada linha, começando da segunda linha (índice 1)
    for idx, row in df.iloc[1:].iterrows():
        flight_id = row['Id.Vuelo']  # Identificador do voo
        
        # Validação 3: Fecha+ALDT < F.ETime+AIBT
        arrival_datetime = convert_datetime(row['Fecha'], row['ALDT'])
        block_datetime = convert_datetime(row['F.ETime'], row['AIBT'])
        
        if arrival_datetime and block_datetime:
            if not arrival_datetime <= block_datetime:
                violations['time_violations'].append(
                    f"Voo {flight_id}: Fecha+ALDT ({row['Fecha']} {row['ALDT']}) " +
                    f"não é anterior ou igual a F.ETime+AIBT ({row['F.ETime']} {row['AIBT']})")
        
        # Validação de status (deve ser OPE)
        if row['Sit.'] != 'OPE':
            violations['status_violations'].append(
                f"Voo {flight_id}: Status inválido: {row['Sit.']}")
        
        # Validação de estação (deve ser IBK)
        if row['Est.'] != 'IBK':
            violations['station_violations'].append(
                f"Voo {flight_id}: Estação inválida: {row['Est.']}")
        
        # Validação de registro com exceções para origens específicas
        if pd.notna(row['Registro']):
            prefix = row['Registro'][:2]
            origem = row['Org.']
            excecoes_origem = ['MVD', 'EZE', 'LIS', 'AEP','SID','MCO','FLL','TFS','RKA','LPA','ACC','MIA','LPA']
            
            if prefix in ['PT', 'PS', 'PP', 'PR', 'PU']:
                if origem not in excecoes_origem and row['Cl.'] != 'A':
                    violations['registration_violations'].append(
                        f"Voo {flight_id}: Registro {row['Registro']} (Origem: {origem}) deve ter classe A, encontrado: {row['Cl.']}")
        
        # Validação de movimento (Assoc. Sit. deve ser OPE ou vazio)
        if pd.notna(row['Assoc. Sit.']) and row['Assoc. Sit.'] not in ['OPE', '']:
            violations['operation_violations'].append(
                f"Voo {flight_id}: Status associado inválido: {row['Assoc. Sit.']}")
        
        # Validação de operação (Assoc. Est. deve ser AIR ou vazio)
        if pd.notna(row['Assoc. Est.']) and row['Assoc. Est.'] not in ['AIR', '']:
            violations['movement_violations'].append(
                f"Voo {flight_id}: Estação associada inválida: {row['Assoc. Est.']}")
        
        # Validação 9: Assoc. Data + Assoc. F.ETime + Assoc. AOBT < Assoc. ATOT
        if pd.notna(row['Assoc. AOBT']) and pd.notna(row['Assoc. ATOT']):
            aobt_datetime = convert_datetime(row['Assoc. Data'], row['Assoc. AOBT'])
            atot_datetime = convert_datetime(row['Assoc. F.ETime'], row['Assoc. ATOT'])
            
            if aobt_datetime and atot_datetime:
                if not aobt_datetime <= atot_datetime:
                    violations['assoc_time_violations'].append(
                        f"Voo {flight_id}: Assoc. Data+AOBT ({row['Assoc. Data']} {row['Assoc. AOBT']}) " +
                        f"não é anterior ou igual a Assoc. F.ETime+ATOT ({row['Assoc. F.ETime']} {row['Assoc. ATOT']})")
    
    return df, violations

def main():
    st.title('Validador de Operações do Scena')
    
    # Upload de arquivo
    st.subheader('Carregar Dados')
    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type='csv')
    
    if uploaded_file is not None:
        # Carrega e valida dados
        df, error = load_data(uploaded_file)
        
        if error:
            st.error(error)
            return
        
        # Adiciona checkboxes para validações adicionais
        col1, col2 = st.columns(2)
        with col1:
            show_movement = st.checkbox('Mostrar Validações de Movimentação', value=True)
        with col2:
            show_corrections = st.checkbox('Mostrar Detalhes das Violações', value=True)
        
        # Processa e valida dados
        df_validated, violations = validate_flights(df)
        
        # Exibe estatísticas resumidas
        st.subheader('Resumo das Validações')
        total_violations = sum(len(v) for v in violations.values())
        st.write(f"Total de registros processados: {len(df)-1}")
        st.write(f"Total de violações encontradas: {total_violations}")
        
        # Exibe violações por categoria
        if total_violations > 0:
            st.subheader('Violações por Categoria')
            
            # Violações básicas
            if violations['time_violations']:
                st.write("Violações de Data/Hora (Fecha+ALDT < F.ETime+AIBT):", len(violations['time_violations']))
                if show_corrections:
                    st.write(violations['time_violations'])
            
            if violations['status_violations']:
                st.write("Violações de Status (Sit.):", len(violations['status_violations']))
                if show_corrections:
                    st.write(violations['status_violations'])
            
            if violations['station_violations']:
                st.write("Violações de Estação (Est.):", len(violations['station_violations']))
                if show_corrections:
                    st.write(violations['station_violations'])
            
            if violations['registration_violations']:
                st.write("Violações de Registro/Classe:", len(violations['registration_violations']))
                if show_corrections:
                    st.write(violations['registration_violations'])
            
            # Validações adicionais baseadas nos checkboxes
            if show_movement:
                if violations['movement_violations']:
                    st.write("Violações de Estação Associada (Assoc. Est.):", len(violations['movement_violations']))
                    if show_corrections:
                        st.write(violations['movement_violations'])
                
                if violations['operation_violations']:
                    st.write("Violações de Status Associado (Assoc. Sit.):", len(violations['operation_violations']))
                    if show_corrections:
                        st.write(violations['operation_violations'])
                
                if violations['assoc_time_violations']:
                    st.write("Violações de Data/Hora (Assoc. Data+AOBT < Assoc. F.ETime+ATOT):", 
                            len(violations['assoc_time_violations']))
                    if show_corrections:
                        st.write(violations['assoc_time_violations'])
        
        # Exibe dataframe validado
        st.subheader('Dados Validados')
        st.dataframe(df_validated)
        
        # Adiciona botão de download para os dados validados
        csv = df_validated.to_csv(index=False, sep=';', encoding='utf-8')
        st.download_button(
            label="Baixar dados validados como CSV",
            data=csv,
            file_name="voos_validados.csv",
            mime="text/csv"
        )
    else:
        st.info('Por favor, carregue um arquivo CSV para iniciar a validação')

if __name__ == '__main__':
    main()
