import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Configuração da página
st.set_page_config(page_title="Sistema de Monitoramento de Descarga",
                   page_icon="📦",
                   layout="wide")


# Inicialização de variáveis de sessão
def init_session_state():
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
    if "current_barcode" not in st.session_state:
        st.session_state.current_barcode = ""


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

        # Adicionar colunas padrão se não existirem
        if 'descricao' not in df.columns:
            df['descricao'] = 'Produto ' + df['codigo_barras'].astype(str)

        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        return None


# Gerar relatório CSV
def generate_report():
    if not st.session_state.scanned_items:
        return None, None

    # Criar DataFrame com os itens escaneados
    report_df = pd.DataFrame(st.session_state.scanned_items)

    # Adicionar informações de tempo
    total_time = (datetime.now() - st.session_state.start_time).total_seconds()
    avg_time = np.mean(
        st.session_state.scan_times) if st.session_state.scan_times else 0

    # Adicionar metadados
    metadata = {
        "data_processamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tempo_total_segundos": total_time,
        "tempo_medio_entre_itens": avg_time,
        "total_itens_processados": len(st.session_state.scanned_items),
        "total_itens_inventario": len(st.session_state.inventory_df)
    }

    # Converter para CSV
    csv = report_df.to_csv(index=False, encoding='utf-8-sig')
    return csv, metadata


# Seção de upload de arquivo
def upload_file_section():
    st.header("📤 Upload de Arquivo de Inventário")

    uploaded_file = st.file_uploader(
        "Selecione um arquivo Excel ou CSV com o inventário",
        type=['xlsx', 'xls', 'csv'])

    if uploaded_file is not None:
        inventory_df = process_uploaded_file(uploaded_file)
        if inventory_df is not None:
            st.session_state.inventory_df = inventory_df
            st.success("✅ Arquivo processado com sucesso!")

            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(inventory_df.head())
            with col2:
                st.info(
                    f"**Total de itens no inventário:** {len(inventory_df)}")
                st.info(
                    f"**Colunas disponíveis:** {', '.join(inventory_df.columns)}"
                )


# Processar código de barras
def process_barcode(barcode):
    # Verificar se o código existe no inventário
    item_match = st.session_state.inventory_df[
        st.session_state.inventory_df['codigo_barras'].astype(str) == str(
            barcode)]

    current_time = datetime.now()

    if not item_match.empty:
        item = item_match.iloc[0].to_dict()

        # Calcular tempo desde o último escaneamento
        time_since_last = current_time - st.session_state.last_scan_time

        # Adicionar informações de tempo
        item['hora_escaneamento'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        item['tempo_desde_ultimo'] = time_since_last.total_seconds()

        # Adicionar à lista de itens escaneados
        st.session_state.scanned_items.append(item)
        st.session_state.scan_times.append(time_since_last.total_seconds())
        st.session_state.last_scan_time = current_time

        st.success(f"✅ Item escaneado: {item.get('descricao', 'N/A')}")
        st.session_state.current_barcode = ""  # Limpar o campo
        return True
    else:
        st.error("❌ Código de barras não encontrado no inventário!")
        return False


# Seção de registro de descarga
def scanning_section():
    st.header("📋 Registro de Descarga")

    if st.session_state.start_time is None:
        if st.button("▶️ Iniciar Processo de Descarga", type="primary"):
            st.session_state.start_time = datetime.now()
            st.session_state.last_scan_time = st.session_state.start_time
            st.session_state.scanned_items = []
            st.session_state.scan_times = []
            st.success("✅ Processo de descarga iniciado!")
            time.sleep(0.5)
            st.rerun()
    else:
        # Mostrar informações do processo atual
        elapsed_time = datetime.now() - st.session_state.start_time
        minutes, seconds = divmod(elapsed_time.total_seconds(), 60)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ Tempo Decorrido",
                      f"{int(minutes)}min {int(seconds)}s")
        with col2:
            st.metric(
                "📦 Itens Escaneados",
                f"{len(st.session_state.scanned_items)}/{len(st.session_state.inventory_df)}"
            )
        with col3:
            if st.session_state.scan_times:
                avg_time = np.mean(st.session_state.scan_times)
                st.metric("⚡ Tempo Médio/Item", f"{avg_time:.1f}s")

        # Interface de escaneamento
        st.subheader("🔍 Escaneamento de Código de Barras")

        # Campo de entrada com foco automático
        barcode_input = st.text_input(
            "Digite o código de barras e pressione Enter:",
            value=st.session_state.current_barcode,
            key="barcode_input",
            placeholder="Digite o código aqui...",
            label_visibility="collapsed")

        if barcode_input:
            process_barcode(barcode_input)
            st.rerun()

        # Botões de ação
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("⏹️ Finalizar Descarga", type="primary"):
                finish_unloading_process()

        # Mostrar itens escaneados
        if st.session_state.scanned_items:
            st.subheader("📋 Itens Escaneados")
            scanned_df = pd.DataFrame(st.session_state.scanned_items)

            # Simplificar a visualização
            display_cols = [
                col
                for col in ['codigo_barras', 'descricao', 'hora_escaneamento']
                if col in scanned_df.columns
            ]
            if display_cols:
                st.dataframe(scanned_df[display_cols].reset_index(drop=True))


# Finalizar processo de descarga
def finish_unloading_process():
    end_time = datetime.now()
    total_time = end_time - st.session_state.start_time

    # Criar relatório
    csv_data, metadata = generate_report()

    st.success("✅ Processo de descarga finalizado!")
    st.balloons()

    # Mostrar resumo
    st.subheader("📊 Resumo da Descarga")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🕒 Tempo Total", f"{total_time.total_seconds():.1f}s")
    with col2:
        st.metric(
            "📦 Itens Processados",
            f"{len(st.session_state.scanned_items)}/{len(st.session_state.inventory_df)}"
        )
    with col3:
        efficiency = (len(st.session_state.scanned_items) /
                      len(st.session_state.inventory_df)) * 100
        st.metric("📈 Eficiência", f"{efficiency:.1f}%")
    with col4:
        avg_time = np.mean(
            st.session_state.scan_times) if st.session_state.scan_times else 0
        st.metric("⚡ Tempo Médio", f"{avg_time:.1f}s")

    # Botão para download do relatório
    if csv_data:
        st.download_button(
            label="📥 Baixar Relatório Completo (CSV)",
            data=csv_data,
            file_name=
            f"relatorio_descarga_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            type="primary")

    # Botão para novo processo
    if st.button("🔄 Iniciar Novo Processo"):
        st.session_state.start_time = None
        st.session_state.last_scan_time = None
        st.session_state.scanned_items = []
        st.session_state.scan_times = []
        st.session_state.current_barcode = ""
        st.rerun()


# Seção de relatórios
def reports_section():
    st.header("📈 Relatórios e Estatísticas")

    if st.session_state.scanned_items:
        st.subheader("📊 Estatísticas do Último Processo")

        scanned_df = pd.DataFrame(st.session_state.scanned_items)

        col1, col2 = st.columns(2)

        with col1:
            st.write("**⏱️ Tempos entre escaneamentos (segundos):**")
            times_df = pd.DataFrame(
                {"Tempo entre itens (s)": st.session_state.scan_times})
            st.write(times_df.describe())

            # Gráfico de distribuição de tempo
            if len(st.session_state.scan_times) > 1:
                st.line_chart(times_df)

        with col2:
            if 'categoria' in scanned_df.columns:
                st.write("**📦 Itens por categoria:**")
                category_counts = scanned_df['categoria'].value_counts()
                st.bar_chart(category_counts)

            # Informações gerais
            st.write("**📋 Informações do Processo:**")
            total_time = (datetime.now() -
                          st.session_state.start_time).total_seconds()
            st.info(f"Tempo total: {total_time:.1f} segundos")
            st.info(
                f"Itens processados: {len(st.session_state.scanned_items)}")
            st.info(
                f"Tempo médio por item: {np.mean(st.session_state.scan_times):.1f}s"
            )
    else:
        st.info(
            "ℹ️ Nenhum dado de descarga disponível. Execute um processo de descarga primeiro."
        )


# Interface principal da aplicação
def main_app():
    st.title("📦 Sistema de Monitoramento de Descarga de Cargas")

    # Menu de navegação
    menu_option = st.sidebar.radio("Navegação", [
        "Upload de Arquivo", "Registro de Descarga", "Relatórios",
        "Reiniciar Sistema"
    ])

    if menu_option == "Upload de Arquivo":
        upload_file_section()
    elif menu_option == "Registro de Descarga":
        if st.session_state.inventory_df is not None:
            scanning_section()
        else:
            st.warning(
                "⚠️ Por favor, faça upload de um arquivo de inventário primeiro."
            )
    elif menu_option == "Relatórios":
        reports_section()
    elif menu_option == "Reiniciar Sistema":
        if st.button("🔄 Reiniciar Todo o Sistema", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# Ponto de entrada da aplicação
def main():
    init_session_state()
    main_app()


if __name__ == "__main__":
    main()
