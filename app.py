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
data_inicio = datetime(2025, 6, 2)          # data da assinatura
dia_vencimento = 1                           # DIA 01
DESCONTO_MAXIMO = 0.4                         # 40% máximo na última parcela
MULTA = 0.10                                   # 10% sobre a parcela atrasada
JUROS_MORA_MENSAL = 0.01                       # 1% ao mês

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

def valor_presente_futuro(numero_parcela, data_atual, t_max):
    venc = data_vencimento(numero_parcela)
    t = meses_entre(venc, data_atual)
    vp_calculado = pmt / (1 + taxa_mensal) ** t
    # Valor mínimo linear: de 100% (t=0) até (1-DESCONTO_MAXIMO)*100% (t=t_max)
    valor_minimo = pmt * (1 - DESCONTO_MAXIMO * (t / t_max))
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

col1, col2 = st.columns(2)
with col1:
    data_input = st.date_input(
        "📅 Data de referência",
        value=datetime(2026, 3, 12),
        min_value=data_inicio,
        format="DD/MM/YYYY"
    )
    data_hoje = datetime.combine(data_input, datetime.min.time())
#with col2:
   # st.metric("Taxa de juros mensal", f"{taxa_mensal:.4%}")

# Determinar última parcela futura
venc_ultima = data_vencimento(60)
if venc_ultima <= data_hoje:
    st.warning("Não há parcelas futuras. Todas já venceram.")
    t_max = None
else:
    t_max = meses_entre(venc_ultima, data_hoje)

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
        if t_max:
            valor_antecipado, _ = valor_presente_futuro(num, data_hoje, t_max)
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

# Exibir tabela
st.subheader("📊 Situação das Parcelas")
df = pd.DataFrame(dados)
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

# Totais (apenas o que você quer exibir)
st.markdown("---")
st.subheader("📈 Resumo")
col_res1, col_res2 = st.columns(2)
with col_res1:
    st.metric("Total vencidas (nominal)", f"R$ {total_nominal_vencidas:.2f}")
with col_res2:
    st.metric("Total futuras (nominal)", f"R$ {total_nominal_futuras:.2f}")

st.metric("💰 Total para antecipação hoje", f"R$ {total_antecipado_futuras:.2f}")
if total_nominal_futuras > 0:
    st.metric("Desconto total em futuras", f"R$ {total_nominal_futuras - total_antecipado_futuras:.2f}")
