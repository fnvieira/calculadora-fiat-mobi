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

# Valor financiado real (principal)
valor_financiado = valor_a_vista - entrada

# ==============================================
# CÁLCULO DA TAXA DE JUROS IMPLÍCITA
# ==============================================
def vp(taxa, n, pmt):
    return pmt * (1 - (1 + taxa)**-n) / taxa

def funcao_taxa(taxa):
    return vp(taxa, n_parcelas, pmt) - valor_financiado

try:
    sol = root_scalar(funcao_taxa, bracket=[0.0001, 0.1], method='bisect')
    taxa_mensal = sol.root
except:
    st.error("Não foi possível calcular a taxa. Verifique os dados.")
    st.stop()

# ==============================================
# FUNÇÕES AUXILIARES
# ==============================================
def meses_entre(data_futura, data_atual):
    diferenca_dias = (data_futura - data_atual).days
    return diferenca_dias / 30.0

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
    valor_minimo = pmt * (1 - DESCONTO_MAXIMO * (t / t_max))
    if vp_calculado < valor_minimo:
        return valor_minimo, True
    else:
        return vp_calculado, False

# ==============================================
# INTERFACE STREAMLIT
# ==============================================
st.set_page_config(page_title="Calculadora de Parcelas - Fiat Mobi", layout="wide")
st.title("🚗 Calculadora de Parcelas - Contrato Fiat Mobi")
st.markdown("---")

# Exibir dados do contrato de forma resumida
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Parcelas", f"{n_parcelas} x R$ {pmt:.2f}")
with col2:
    st.metric("Taxa mensal", f"{taxa_mensal:.4%}")
with col3:
    st.metric("Taxa anual", f"{(1+taxa_mensal)**12 - 1:.4%}")
with col4:
    st.metric("Desconto máx.", f"{DESCONTO_MAXIMO:.0%}")

st.markdown("---")

# Input da data
data_input = st.date_input(
    "📅 Selecione a data de referência",
    value=datetime(2026, 3, 12),
    min_value=data_inicio.date(),
    format="DD/MM/YYYY"
)
data_hoje = datetime.combine(data_input, datetime.min.time())

# Verificar se a data é válida
if data_hoje < data_inicio:
    st.warning("A data informada é anterior à assinatura do contrato (02/06/2025). Use uma data posterior.")
    st.stop()

# Determinar t_max para limite linear
ultima_parcela = 60
venc_ultima = data_vencimento(ultima_parcela)
if venc_ultima <= data_hoje:
    st.info("Todas as parcelas já venceram. Exibindo apenas vencidas.")
    t_max = None
else:
    t_max = meses_entre(venc_ultima, data_hoje)

# Preparar lista de dados para a tabela
dados = []
total_nominal_vencidas = 0.0
total_devido_vencidas = 0.0
total_nominal_futuras = 0.0
total_antecipado_futuras = 0.0

for num in range(1, n_parcelas + 1):
    venc = data_vencimento(num)
    if venc <= data_hoje:
        # Parcela vencida
        valor_devido, multa, juros = valor_vencido(venc, data_hoje)
        acrescimo = valor_devido - pmt
        dados.append({
            "Parcela": num,
            "Vencimento": venc.strftime("%d/%m/%Y"),
            "Tipo": "VENCIDA",
            "Valor Nominal": pmt,
            "Multa (10%)": multa,
            "Juros (1% a.m.)": juros,
            "Valor Hoje": valor_devido,
            "Diferença": acrescimo
        })
        total_nominal_vencidas += pmt
        total_devido_vencidas += valor_devido
    else:
        # Parcela futura
        if t_max is not None:
            valor_antecipado, com_limite = valor_presente_futuro(num, data_hoje, t_max)
        else:
            # Não deveria acontecer, mas se t_max for None (todas vencidas), pula
            continue
        desconto = pmt - valor_antecipado
        tipo = "FUTURA" + ("*" if com_limite else "")
        dados.append({
            "Parcela": num,
            "Vencimento": venc.strftime("%d/%m/%Y"),
            "Tipo": tipo,
            "Valor Nominal": pmt,
            "Multa (10%)": 0.0,
            "Juros (1% a.m.)": 0.0,
            "Valor Hoje": valor_antecipado,
            "Diferença": -desconto  # negativo indica desconto
        })
        total_nominal_futuras += pmt
        total_antecipado_futuras += valor_antecipado

# Exibir tabela
st.markdown(f"### Situação das Parcelas em {data_hoje.strftime('%d/%m/%Y')}")
if dados:
    df = pd.DataFrame(dados)
    # Formatar colunas numéricas
    format_dict = {
        "Valor Nominal": "R$ {:.2f}",
        "Multa (10%)": "R$ {:.2f}",
        "Juros (1% a.m.)": "R$ {:.2f}",
        "Valor Hoje": "R$ {:.2f}",
        "Diferença": "R$ {:.2f}"
    }
    st.dataframe(
        df.style.format(format_dict),
        use_container_width=True,
        height=600
    )
else:
    st.write("Nenhuma parcela encontrada.")

st.markdown("---")

# Resumo
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Vencidas (Nominal)", f"R$ {total_nominal_vencidas:.2f}")
with col2:
    
with col3:
    st.metric("Total Futuras (Nominal)", f"R$ {total_nominal_futuras:.2f}")
with col4:
    st.metric("Total para Antecipação", f"R$ {total_antecipado_futuras:.2f}")
    if total_nominal_futuras > 0:
        st.caption(f"Desconto: R$ {total_nominal_futuras - total_antecipado_futuras:.2f}")

st.markdown("---")
st.caption(f"Multa: 10% | Juros de mora: 1% ao mês ")
