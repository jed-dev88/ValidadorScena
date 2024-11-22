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
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        time_obj = datetime.strptime(time_str, '%H:%M').time()
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
    
    df = df[~df['Sit.'].isin(['CAN', 'BOR'])]
    
    for idx, row in df.iloc[1:].iterrows():
        flight_id = row['Id.Vuelo']
        
        arrival_datetime = convert_datetime(row['Fecha'], row['ALDT'])
        block_datetime = convert_datetime(row['F.ETime'], row['AIBT'])
        
        if arrival_datetime and block_datetime:
            if not arrival_datetime <= block_datetime:
                violations['time_violations'].append(
                    f"Voo {flight_id}: Fecha+ALDT ({row['Fecha']} {row['ALDT']}) " +
                    f"não é anterior ou igual a F.ETime+AIBT ({row['F.ETime']} {row['AIBT']})")
        
        if row['Sit.'] != 'OPE':
            violations['status_violations'].append(
                f"Voo {flight_id}: Status inválido: {row['Sit.']}")
        
        if row['Est.'] != 'IBK':
            violations['station_violations'].append(
                f"Voo {flight_id}: Estação inválida: {row['Est.']}")
        
        if pd.notna(row['Registro']):
            prefix = row['Registro'][:2]
            origem = row['Org.']
            excecoes_origem = ['MVD', 'EZE', 'LIS', 'AEP','SID','MCO','FLL','TFS','RKA','LPA','ACC','MIA','LPA','RAK']
            
            if prefix in ['PT', 'PS', 'PP', 'PR', 'PU']:
                if origem not in excecoes_origem and row['Cl.'] != 'A':
                    violations['registration_violations'].append(
                        f"Voo {flight_id}: Registro {row['Registro']} (Origem: {origem}) deve ter classe A, encontrado: {row['Cl.']}")
        
        if pd.notna(row['Assoc. Sit.']) and row['Assoc. Sit.'] not in ['OPE', '']:
            violations['operation_violations'].append(
                f"Voo {flight_id}: Status associado inválido: {row['Assoc. Sit.']}")
        
        if pd.notna(row['Assoc. Est.']) and row['Assoc. Est.'] not in ['AIR', '']:
            violations['movement_violations'].append(
                f"Voo {flight_id}: Estação associada inválida: {row['Assoc. Est.']}")
        
        if pd.notna(row['Assoc. AOBT']) and pd.notna(row['Assoc. ATOT']):
            aobt_datetime = convert_datetime(row['Assoc. Data'], row['Assoc. AOBT'])
            atot_datetime = convert_datetime(row['Assoc. F.ETime'], row['Assoc. ATOT'])
            
            if aobt_datetime and atot_datetime:
                if not aobt_datetime <= atot_datetime:
                    violations['assoc_time_violations'].append(
                        f"Voo {flight_id}: Assoc. Data+AOBT ({row['Assoc. Data']} {row['Assoc. AOBT']}) " +
                        f"não é anterior ou igual a Assoc. F.ETime+ATOT ({row['Assoc. F.ETime']} {row['Assoc. ATOT']})")
    
    return df, violations

def generate_validation_report(violations, total_records):
    report = []
    report.append("Relatório de Validação\n")
    report.append(f"Total de registros processados: {total_records}\n")
    report.append(f"Total de violações encontradas: {sum(len(v) for v in violations.values())}\n\n")
    
    for violation_type, violation_list in violations.items():
        if violation_list:
            report.append(f"\n{violation_type.replace('_', ' ').title()}:\n")
            for violation in violation_list:
                report.append(f"- {violation}\n")
    
    return "".join(report)

def main():
    st.title('Validador de Operações do Scena')

    st.subheader('Verificação Inicial')
    movement_validation = st.radio(
        "Foi feita a validação de movimentação do aeroporto?",
        ('Sim', 'Não'),
        index=1
    )
    
    st.divider()
    
    if movement_validation == 'Não':
        st.warning('Atenção: É recomendado fazer a validação de movimentação do aeroporto antes de prosseguir.')
    
    st.subheader('Carregar Dados')
    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type='csv')
    
    if uploaded_file is not None:
        df, error = load_data(uploaded_file)
        
        if error:
            st.error(error)
            return
        
        df_validated, violations = validate_flights(df)
        
        st.subheader('Resumo das Validações')
        total_violations = sum(len(v) for v in violations.values())
        st.write(f"Total de registros processados: {len(df)-1}")
        st.write(f"Total de violações encontradas: {total_violations}")
        
        if total_violations > 0:
            st.subheader('Violações por Categoria')
            
            if violations['time_violations']:
                st.write("Violações de Data/Hora (Fecha+ALDT < F.ETime+AIBT):", len(violations['time_violations']))
                st.write(violations['time_violations'])
            
            if violations['status_violations']:
                st.write("Violações de Status (Sit.):", len(violations['status_violations']))
                st.write(violations['status_violations'])
            
            if violations['station_violations']:
                st.write("Violações de Estação (Est.):", len(violations['station_violations']))
                st.write(violations['station_violations'])
            
            if violations['registration_violations']:
                st.write("Violações de Registro/Classe:", len(violations['registration_violations']))
                st.write(violations['registration_violations'])
            
            if violations['movement_violations']:
                st.write("Violações de Estação Associada (Assoc. Est.):", len(violations['movement_violations']))
                st.write(violations['movement_violations'])
            
            if violations['operation_violations']:
                st.write("Violações de Status Associado (Assoc. Sit.):", len(violations['operation_violations']))
                st.write(violations['operation_violations'])
            
            if violations['assoc_time_violations']:
                st.write("Violações de Data/Hora (Assoc. Data+AOBT < Assoc. F.ETime+ATOT):", 
                        len(violations['assoc_time_violations']))
                st.write(violations['assoc_time_violations'])
        
        st.subheader('Dados Validados')
        st.dataframe(df_validated)
        
        col1, col2 = st.columns(2)
        with col1:
            csv = df_validated.to_csv(index=False, sep=';', encoding='utf-8')
            st.download_button(
                label="Baixar dados validados (CSV)",
                data=csv,
                file_name="voos_validados.csv",
                mime="text/csv"
            )
        
        with col2:
            validation_report = generate_validation_report(violations, len(df)-1)
            st.download_button(
                label="Baixar relatório de validação (TXT)",
                data=validation_report,
                file_name="relatorio_validacao.txt",
                mime="text/plain"
            )
    else:
        st.info('Por favor, carregue um arquivo CSV para iniciar a validação')

if __name__ == '__main__':
    main()
