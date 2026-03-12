import streamlit as st
import numpy as np
from datetime import datetime
from scipy.optimize import root_scalar
import pandas as pd

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

valor_financiado = valor_a_vista - entrada

# ==============================================
# CÁLCULO DA TAXA DE JUROS
# ==============================================
def vp(taxa, n, pmt):
    return pmt * (1 - (1 + taxa)**-n) / taxa

def funcao_taxa(taxa):
    return vp(taxa, n_parcelas, pmt) - valor_financiado

try:
    sol = root_scalar(funcao_taxa, bracket=[0.0001, 0.1], method='bisect')
    taxa_mensal = sol.root
except:
    st.error("Erro ao calcular a taxa de juros.")
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
# INTERFACE STREAMLIT
# ==============================================
st.set_page_config(page_title="Calculadora de Parcelas", layout="wide")
st.title("📊 Calculadora de Parcelas - Contrato Fiat Mobi")
st.markdown("---")

with st.sidebar:
    st.header("Dados do Contrato")
    st.write(f"**Parcelas:** {n_parcelas} x R$ {pmt:.2f}")
    st.write(f"**Data de assinatura:** {data_inicio.strftime('%d/%m/%Y')}")
    st.write("**Multa por atraso:** 10%")
    st.write("**Juros de mora:** 1% ao mês")

st.subheader("📅 Data de Referência")
data_input = st.date_input("Selecione a data para cálculo:", value=datetime(2026, 3, 12), min_value=data_inicio, format="DD/MM/YYYY")
data_hoje = datetime.combine(data_input, datetime.min.time())

# Determinar última parcela futura
venc_ultima = data_vencimento(60)
if venc_ultima <= data_hoje:
    st.warning("Todas as parcelas já venceram.")
    t_max = None
else:
    t_max = meses_entre(venc_ultima, data_hoje)

# Preparar dados
dados = []
total_nominal_vencidas = 0
total_devido_vencidas = 0
total_nominal_futuras = 0
total_antecipado_futuras = 0

for num in range(1, n_parcelas + 1):
    venc = data_vencimento(num)
    if venc <= data_hoje:
        valor_devido, multa, juros = valor_vencido(venc, data_hoje)
        acrescimo = valor_devido - pmt
        dados.append({
            "Parcela": num,
            "Vencimento": venc.strftime("%d/%m/%Y"),
            "Tipo": "VENCIDA",
            "Valor Nominal": pmt,
            "Multa (10%)": multa,
            "Juros": juros,
            "Valor Hoje": valor_devido,
            "Diferença": acrescimo
        })
        total_nominal_vencidas += pmt
        total_devido_vencidas += valor_devido
    else:
        if t_max is not None:
            valor_antecipado, com_limite = valor_presente_futuro(num, data_hoje, t_max)
            desconto = pmt - valor_antecipado
            dados.append({
                "Parcela": num,
                "Vencimento": venc.strftime("%d/%m/%Y"),
                "Tipo": "FUTURA" + ("*" if com_limite else ""),
                "Valor Nominal": pmt,
                "Multa (10%)": 0,
                "Juros": 0,
                "Valor Hoje": valor_antecipado,
                "Diferença": -desconto
            })
            total_nominal_futuras += pmt
            total_antecipado_futuras += valor_antecipado

# Exibir tabela
st.markdown("---")
st.subheader("📋 Situação das Parcelas")
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

# Resumo
st.markdown("---")
st.subheader("📈 Resumo Financeiro")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Parcelas Vencidas (Nominal)", f"R$ {total_nominal_vencidas:.2f}")
with col2:
    st.metric("Total Parcelas Futuras (Nominal)", f"R$ {total_nominal_futuras:.2f}")
with col3:
    st.metric("Total para Antecipação Hoje", f"R$ {total_antecipado_futuras:.2f}")

# Observação: removi as linhas de rodapé que você não queria
