import streamlit as st
import numpy as np
from datetime import datetime
from scipy.optimize import root_scalar
import pandas as pd

# ==============================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================
st.set_page_config(
    page_title="Calculadora de Contrato - Fiat Mobi",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Calculadora de Parcelas - Contrato Fiat Mobi")
st.markdown("---")

# ==============================================
# DADOS FIXOS DO CONTRATO
# ==============================================
entrada = 0.0
pmt = 1500.0
n_parcelas = 60
valor_a_vista = 60000.0
data_inicio = datetime(2025, 6, 2)
dia_vencimento = 1
DESCONTO_MAXIMO = 0.4
MULTA = 0.10
JUROS_MORA_MENSAL = 0.01

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
    st.error("Erro ao calcular taxa de juros.")
    st.stop()

# ==============================================
# FUNÇÕES AUXILIARES
# ==============================================
def data_vencimento(numero_parcela):
    mes_venc = data_inicio.month + numero_parcela - 1
    ano_venc = data_inicio.year
    while mes_venc > 12:
        ano_venc += 1
        mes_venc -= 12
    return datetime(ano_venc, mes_venc, dia_vencimento)

def meses_entre(data_futura, data_atual):
    return (data_futura - data_atual).days / 30.0

def valor_vencido(vencimento, data_atual):
    dias_atraso = (data_atual - vencimento).days
    if dias_atraso <= 0:
        return pmt, 0.0, 0.0
    multa = pmt * MULTA
    juros = pmt * (JUROS_MORA_MENSAL / 30) * dias_atraso
    total = pmt + multa + juros
    return total, multa, juros

def valor_presente_futuro(numero_parcela, data_atual, t_max):
    venc = data_vencimento(numero_parcela)
    t = meses_entre(venc, data_atual)
    vp_calculado = pmt / (1 + taxa_mensal) ** t
    valor_minimo = pmt * (1 - DESCONTO_MAXIMO * (t / t_max))
    if vp_calculado < valor_minimo:
        return valor_minimo, True
    return vp_calculado, False

# ==============================================
# INTERFACE DO USUÁRIO
# ==============================================
col1, col2 = st.columns(2)

with col1:
    data_input = st.date_input(
        "📅 Data de referência para cálculo",
        value=datetime(2026, 3, 12),
        min_value=data_inicio,
        format="DD/MM/YYYY"
    )
    data_hoje = datetime.combine(data_input, datetime.min.time())

with col2:
    st.metric("Taxa de juros mensal", f"{taxa_mensal:.4%}")
    st.metric("Taxa anual equivalente", f"{(1+taxa_mensal)**12 - 1:.4%}")

# ==============================================
# CÁLCULO PARA TODAS AS PARCELAS
# ==============================================
st.markdown("---")
st.subheader("📊 Situação das Parcelas")

# Prepara dados para a tabela
dados = []
total_nominal_vencidas = 0
total_devido_vencidas = 0
total_nominal_futuras = 0
total_antecipado_futuras = 0

# Determina t_max para limite linear
venc_ultima = data_vencimento(60)
if venc_ultima > data_hoje:
    t_max = meses_entre(venc_ultima, data_hoje)
else:
    t_max = None

for num in range(1, n_parcelas + 1):
    venc = data_vencimento(num)
    
    if venc <= data_hoje:
        # Parcela vencida
        valor_devido, multa, juros = valor_vencido(venc, data_hoje)
        dados.append({
            "Parcela": num,
            "Vencimento": venc.strftime("%d/%m/%Y"),
            "Tipo": "VENCIDA",
            "Valor Nominal": pmt,
            "Multa (10%)": multa,
            "Juros": juros,
            "Valor Hoje": valor_devido,
            "Diferença": valor_devido - pmt
        })
        total_nominal_vencidas += pmt
        total_devido_vencidas += valor_devido
    else:
        # Parcela futura
        if t_max:
            valor_antecipado, com_limite = valor_presente_futuro(num, data_hoje, t_max)
            dados.append({
                "Parcela": num,
                "Vencimento": venc.strftime("%d/%m/%Y"),
                "Tipo": "FUTURA" + ("*" if com_limite else ""),
                "Valor Nominal": pmt,
                "Multa (10%)": 0,
                "Juros": 0,
                "Valor Hoje": valor_antecipado,
                "Diferença": valor_antecipado - pmt
            })
            total_nominal_futuras += pmt
            total_antecipado_futuras += valor_antecipado

# Exibe tabela
df = pd.DataFrame(dados)
st.dataframe(
    df.style.format({
        "Valor Nominal": "R$ {:.2f}",
        "Multa (10%)": "R$ {:.2f}",
        "Juros": "R$ {:.2f}",
        "Valor Hoje": "R$ {:.2f}",
        "Diferença": "R$ {:.2f}"
    }),
    use_container_width=True,
    height=600
)

# ==============================================
# RESUMO
# ==============================================
st.markdown("---")
st.subheader("📈 Resumo Financeiro")

col1, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Vencidas (Nominal)", f"R$ {total_nominal_vencidas:.2f}")
with col3:
    st.metric("Total Futuras (Nominal)", f"R$ {total_nominal_futuras:.2f}")
with col4:
    st.metric("Total para Antecipação", f"R$ {total_antecipado_futuras:.2f}")

st.markdown("---")
st.caption("*Parcelas com limite de 40% de desconto aplicado")
st.caption("Multa: 10% | Juros de mora: 1% ao mês | Desconto máximo: 40% na última parcela")
