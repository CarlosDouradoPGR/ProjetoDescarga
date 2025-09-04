import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import base64
import io
import hashlib

# Configuração da página
st.set_page_config(
    page_title="Sistema de Monitoramento de Descarga",
    page_icon="📦",
    layout="wide"
)

# Funções de autenticação
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Banco de dados de usuários (em produção, use um banco de dados real)
users = {
    "admin": make_hashes("admin123"),
    "operador": make_hashes("operador123")
}

# Inicialização de variáveis de sessão
def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "inventory_df" not in st.session_state:
        st.session_state.inventory_df = None
    if "scanned_items" not in st.session_state:
        st.session_state.scanned_items = []
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "last_scan_time" not in st.session_state:
        st.session_state.last_scan_time = None
    if "scan_times" not in st.session_state:
        st.session_state.scan_times = []

# Página de login
def login_page():
    st.title("Sistema de Monitoramento de Descarga de Cargas")
    st.subheader("Faça login para acessar o sistema")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username in users and check_hashes(password, users[username]):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("Login realizado com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# Processar arquivo enviado
def process_uploaded_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Verificar se as colunas necessárias existem
        if 'codigo_barras' not in df.columns:
            st.error("Coluna 'codigo_barras' não encontrada no arquivo.")
            return None
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        return None

# Gerar relatório CSV
def generate_report():
    if not st.session_state.scanned_items:
        return None
    
    # Criar DataFrame com os itens escaneados
    report_df = pd.DataFrame(st.session_state.scanned_items)
    
    # Adicionar informações de tempo
    total_time = (datetime.now() - st.session_state.start_time).total_seconds()
    avg_time = np.mean(st.session_state.scan_times) if st.session_state.scan_times else 0
    
    # Adicionar metadados
    metadata = {
        "usuario": st.session_state.username,
        "data_processamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tempo_total_segundos": total_time,
        "tempo_medio_entre_itens": avg_time,
        "total_itens_processados": len(st.session_state.scanned_items)
    }
    
    # Converter para CSV
    csv = report_df.to_csv(index=False, encoding='utf-8-sig')
    return csv, metadata

# Interface principal da aplicação
def main_app():
    st.title("📦 Sistema de Monitoramento de Descarga de Cargas")
    st.sidebar.title(f"Olá, {st.session_state.username}")
    
    # Menu lateral
    menu_option = st.sidebar.radio(
        "Navegação",
        ["Upload de Arquivo", "Registro de Descarga", "Relatórios", "Sair"]
    )
    
    if menu_option == "Upload de Arquivo":
        upload_file_section()
    elif menu_option == "Registro de Descarga":
        if st.session_state.inventory_df is not None:
            scanning_section()
        else:
            st.warning("Por favor, faça upload de um arquivo de inventário primeiro.")
    elif menu_option == "Relatórios":
        reports_section()
    elif menu_option == "Sair":
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()

# Seção de upload de arquivo
def upload_file_section():
    st.header("Upload de Arquivo de Inventário")
    
    uploaded_file = st.file_uploader(
        "Selecione um arquivo Excel ou CSV com o inventário",
        type=['xlsx', 'xls', 'csv']
    )
    
    if uploaded_file is not None:
        inventory_df = process_uploaded_file(uploaded_file)
        if inventory_df is not None:
            st.session_state.inventory_df = inventory_df
            st.success("Arquivo processado com sucesso!")
            st.dataframe(inventory_df.head())
            
            st.info(f"Total de itens no inventário: {len(inventory_df)}")

# Seção de registro de descarga
def scanning_section():
    st.header("Registro de Descarga")
    
    if st.session_state.start_time is None:
        if st.button("Iniciar Processo de Descarga"):
            st.session_state.start_time = datetime.now()
            st.session_state.last_scan_time = st.session_state.start_time
            st.session_state.scanned_items = []
            st.session_state.scan_times = []
            st.success("Processo de descarga iniciado!")
            st.rerun()
    else:
        # Mostrar informações do processo atual
        elapsed_time = datetime.now() - st.session_state.start_time
        st.info(f"Tempo decorrido: {elapsed_time}")
        st.info(f"Itens escaneados: {len(st.session_state.scanned_items)}/{len(st.session_state.inventory_df)}")
        
        # Interface de escaneamento
        st.subheader("Escaneamento de Código de Barras")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            barcode_input = st.text_input(
                "Digite o código de barras ou use um leitor:",
                key="barcode_input",
                placeholder="Digite o código e pressione Enter"
            )
            
            if barcode_input:
                process_barcode(barcode_input)
        
        with col2:
            if st.button("Finalizar Descarga", type="primary"):
                finish_unloading_process()
        
        # Mostrar itens escaneados
        if st.session_state.scanned_items:
            st.subheader("Itens Escaneados")
            scanned_df = pd.DataFrame(st.session_state.scanned_items)
            st.dataframe(scanned_df)

# Processar código de barras
def process_barcode(barcode):
    # Verificar se o código existe no inventário
    item_match = st.session_state.inventory_df[
        st.session_state.inventory_df['codigo_barras'] == barcode
    ]
    
    current_time = datetime.now()
    
    if not item_match.empty:
        item = item_match.iloc[0].to_dict()
        
        # Calcular tempo desde o último escaneamento
        time_since_last = current_time - st.session_state.last_scan_time
        
        # Adicionar informações de tempo
        item['hora_escaneamento'] = current_time
        item['tempo_desde_ultimo'] = time_since_last.total_seconds()
        
        # Adicionar à lista de itens escaneados
        st.session_state.scanned_items.append(item)
        st.session_state.scan_times.append(time_since_last.total_seconds())
        st.session_state.last_scan_time = current_time
        
        st.success(f"Item escaneado: {item.get('descricao', 'N/A')}")
    else:
        st.error("Código de barras não encontrado no inventário!")
    
    # Limpar o campo de entrada
    st.session_state.barcode_input = ""

# Finalizar processo de descarga
def finish_unloading_process():
    end_time = datetime.now()
    total_time = end_time - st.session_state.start_time
    
    # Criar relatório
    csv_data, metadata = generate_report()
    
    if csv_data:
        # Mostrar resumo
        st.success("Processo de descarga finalizado!")
        st.subheader("Resumo da Descarga")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tempo Total", f"{total_time.total_seconds():.2f} segundos")
        with col2:
            st.metric("Itens Processados", f"{len(st.session_state.scanned_items)}/{len(st.session_state.inventory_df)}")
        with col3:
            avg_time = np.mean(st.session_state.scan_times) if st.session_state.scan_times else 0
            st.metric("Tempo Médio por Item", f"{avg_time:.2f} segundos")
        
        # Botão para download do relatório
        st.download_button(
            label="Baixar Relatório Completo (CSV)",
            data=csv_data,
            file_name=f"relatorio_descarga_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Resetar estado
    if st.button("Iniciar Novo Processo"):
        st.session_state.start_time = None
        st.session_state.last_scan_time = None
        st.session_state.scanned_items = []
        st.session_state.scan_times = []
        st.rerun()

# Seção de relatórios
def reports_section():
    st.header("Relatórios e Estatísticas")
    
    if st.session_state.scanned_items:
        st.subheader("Estatísticas do Último Processo")
        
        scanned_df = pd.DataFrame(st.session_state.scanned_items)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Tempos entre escaneamentos (segundos):")
            times_df = pd.DataFrame({
                "Tempo entre itens (s)": st.session_state.scan_times
            })
            st.write(times_df.describe())
        
        with col2:
            if 'categoria' in scanned_df.columns:
                st.write("Itens por categoria:")
                category_counts = scanned_df['categoria'].value_counts()
                st.bar_chart(category_counts)
    else:
        st.info("Nenhum dado de descarga disponível. Execute um processo de descarga primeiro.")

# Ponto de entrada da aplicação
def main():
    init_session_state()
    
    if not st.session_state.authenticated:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
