import streamlit as st
import numpy as np
from datetime import datetime
from scipy.optimize import root_scalar
import pandas as pd
from io import BytesIO

# ==============================================
# DADOS FIXOS DO CONTRATO
# ==============================================
entrada = 0.0
pmt = 1500.0
n_parcelas = 60
valor_a_vista = 60000.0
data_inicio = datetime(2025, 6, 2)          # data da assinatura
dia_vencimento = 1                           # DIA 01
DESCONTO_MAXIMO = 0.4                         # 40% máximo (sobre o prazo total)
MULTA = 0.10                                   # 10% sobre a parcela atrasada
JUROS_MORA_MENSAL = 0.01                       # 1% ao mês

# Prazo total da última parcela (da assinatura ao vencimento) em meses
T_total = 51.0  # 60 meses do contrato

# ==============================================
# CÁLCULO DA TAXA DE JUROS
# ==============================================
valor_financiado = valor_a_vista - entrada

def vp(taxa, n, pmt):
    return pmt * (1 - (1 + taxa)**-n) / taxa

def funcao_taxa(taxa):
    return vp(taxa, n_parcelas, pmt) - valor_financiado

try:
    sol = root_scalar(funcao_taxa, bracket=[0.0001, 0.1], method='bisect')
    taxa_mensal = sol.root
except:
    st.error("Erro ao calcular taxa de juros. Verifique os dados.")
    st.stop()

# ==============================================
# FUNÇÕES AUXILIARES
# ==============================================
def meses_entre(data_futura, data_atual):
    return (data_futura - data_atual).days / 30.0

def data_vencimento(numero_parcela):
    mes_venc = data_inicio.month + numero_parcela - 1
    ano_venc = data_inicio.year
    while mes_venc > 12:
        ano_venc += 1
        mes_venc -= 12
    return datetime(ano_venc, mes_venc, dia_vencimento)

def valor_vencido(vencimento, data_atual):
    dias_atraso = (data_atual - vencimento).days
    if dias_atraso <= 0:
        return pmt, 0.0, 0.0
    multa = pmt * MULTA
    juros = pmt * (JUROS_MORA_MENSAL / 30) * dias_atraso
    total = pmt + multa + juros
    return total, multa, juros

def valor_presente_futuro(numero_parcela, data_atual):
    venc = data_vencimento(numero_parcela)
    t = meses_entre(venc, data_atual)  # tempo restante em meses
    if t <= 0:
        return pmt, False  # já vencida (não deve ocorrer aqui)
    vp_calculado = pmt / (1 + taxa_mensal) ** t
    # Limite linear baseado no prazo total de 60 meses
    valor_minimo = pmt * (1 - DESCONTO_MAXIMO * (t / T_total))
    # Garante que o valor mínimo não seja menor que o justo (já calculado)
    if vp_calculado < valor_minimo:
        return valor_minimo, True
    else:
        return vp_calculado, False

# ==============================================
# INTERFACE STREAMLIT
# ==============================================
st.set_page_config(page_title="Calculadora de Contrato - Fiat Mobi", layout="wide")
st.title("🚗 Calculadora de Parcelas - Contrato Fiat Mobi")
st.markdown("---")

# Mensagem padrão informativa
st.info(
    f"📌 **Valores calculados na data de referência indicada abaixo.** "
    f"Os valores de parcelas futuras (antecipação) e vencidas (com acréscimos) são atualizados diariamente conforme as regras de descontos e acréscimos previstas no contrato. "
    f"Para uma nova simulação, altere a data."
)

col1, col2 = st.columns(2)
with col1:
    data_input = st.date_input(
        "📅 Data de referência",
        value=datetime(2026, 3, 12),
        min_value=data_inicio,
        format="DD/MM/YYYY"
    )
    data_hoje = datetime.combine(data_input, datetime.min.time())
with col2:
    st.metric("Taxa de juros mensal", f"{taxa_mensal:.4%}")

# Gerar dados para a tabela
dados = []
total_nominal_vencidas = 0.0
total_devido_vencidas = 0.0
total_nominal_futuras = 0.0
total_antecipado_futuras = 0.0

for num in range(1, n_parcelas + 1):
    venc = data_vencimento(num)
    if venc <= data_hoje:
        # Vencida
        valor_devido, multa, juros = valor_vencido(venc, data_hoje)
        dados.append({
            "Parcela": num,
            "Vencimento": venc.strftime("%d/%m/%Y"),
            "Tipo": "VENCIDA",
            "Valor nominal": pmt,
            "Multa (10%)": multa,
            "Juros (1% a.m.)": juros,
            "Valor hoje": valor_devido,
            "Diferença": valor_devido - pmt
        })
        total_nominal_vencidas += pmt
        total_devido_vencidas += valor_devido
    else:
        # Futura
        valor_antecipado, _ = valor_presente_futuro(num, data_hoje)
        dados.append({
            "Parcela": num,
            "Vencimento": venc.strftime("%d/%m/%Y"),
            "Tipo": "FUTURA",
            "Valor nominal": pmt,
            "Multa (10%)": 0.0,
            "Juros (1% a.m.)": 0.0,
            "Valor hoje": valor_antecipado,
            "Diferença": valor_antecipado - pmt
        })
        total_nominal_futuras += pmt
        total_antecipado_futuras += valor_antecipado

# Criar DataFrame
df = pd.DataFrame(dados)

# Exibir tabela
st.subheader("📊 Situação das Parcelas")
st.dataframe(
    df.style.format({
        "Valor nominal": "R$ {:.2f}",
        "Multa (10%)": "R$ {:.2f}",
        "Juros (1% a.m.)": "R$ {:.2f}",
        "Valor hoje": "R$ {:.2f}",
        "Diferença": "R$ {:.2f}"
    }),
    use_container_width=True,
    height=600
)

# Botão de exportação para Excel
@st.cache_data
def converter_df_para_excel(df, data_ref):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Parcelas')
        # Adicionar informação da data de referência em uma célula
        workbook = writer.book
        sheet = workbook['Parcelas']
        sheet['A1'] = f"Data de referência: {data_ref.strftime('%d/%m/%Y')}"
    processed_data = output.getvalue()
    return processed_data

if not df.empty:
    excel_data = converter_df_para_excel(df, data_hoje)
    st.download_button(
        label="📥 Exportar para Excel",
        data=excel_data,
        file_name=f"parcelas_{data_hoje.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Totais
st.markdown("---")
st.subheader("📈 Resumo")
col_res1, col_res2 = st.columns(2)
with col_res1:
    st.metric("Total vencidas (nominal)", f"R$ {total_nominal_vencidas:.2f}")
with col_res2:
    st.metric("Total a Vencer (nominal)", f"R$ {total_nominal_futuras:.2f}")

st.metric("💰 Total para antecipação hoje", f"R$ {total_antecipado_futuras:.2f}")
if total_nominal_futuras > 0:
    st.metric("Desconto total se pago na data atual com antecipação", f"R$ {total_nominal_futuras - total_antecipado_futuras:.2f}")
