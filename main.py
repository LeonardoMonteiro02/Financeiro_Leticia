from datetime import datetime, timedelta
import io
import warnings
from dateutil.relativedelta import relativedelta
import pandas as pd
import psycopg2
from reportlab.lib import colors


warnings.filterwarnings("ignore", category=UserWarning)

# Importações nativas do ReportLab para construir o PDF profissional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# Configuração da página para um visual limpo e amplo
st.set_page_config(
    page_title="Gestão Financeira Compartilhada",
    page_icon="👩🏾‍❤️‍👩🏾",
    layout="wide",
)

# --- CUSTOMIZAÇÃO ESTÉTICA (Visual Elegante e Feminino) ---
st.markdown(
    """
    <style>
        /* Cor de fundo dos botões primários e detalhes */
        .stButton>button[kind="primary"] {
            background-color: #d63384 !important;
            border-color: #d63384 !important;
            color: white !important;
        }
        .stButton>button[kind="primary"]:hover {
            background-color: #f1057c !important;
            border-color: #f1057c !important;
        }
        /* Ajuste sutil nas abas */
        button[data-baseweb="tab"] p {
            font-size: 16px !important;
            font-weight: 500 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            border-bottom-color: #d63384 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] p {
            color: #d63384 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# Listas de configurações globais
LISTA_RESPONSAVEIS = ["👩🏽 Leticia", "👩🏾 Amanda", "🏡 Conjunto"]

LISTA_CATEGORIAS_ENTRADA = [
    "💰 Salário Base / Pró-labore",
    "🍔 Vale Alimentação / Refeição",
    "✨ Renda Extra / Freelance",
    "📈 Investimentos / Dividendos",
    "🎁 Bônus / Premiações",
    "🎄 13º Salário / Férias",
    "🏠 Aluguel / Sublocação",
    "📦 Venda de Bens / Desapegos",
    "💫 Presentes / Reembolsos",
    "✨ Outros",
]

LISTA_CATEGORIAS_SAIDA = [
    "🏠 Moradia (Aluguel/Condomínio)",
    "🛒 Mercado/Alimentação",
    "⚡ Contas Consumo (Luz/Água)",
    "🚗 Transporte/Combustível",
    "💊 Saúde & Farmácia",
    "🎭 Lazer & Viagens",
    "🛍️ Compras & Vestuário",
    "📉 Dívidas & Empréstimos",
    "🏦 Tarifas Bancárias",
    "✨ Outros",
]

LISTA_FORMAS_PAGAMENTO = [
    "⚡ Pix",
    "💳 Cartão de Débito",
    "💳 Crédito",
    "💵 Dinheiro",
    "🔄 Débito Automático",
    "🏦 Transferência",
]


def conectar_db():
    try:
        db_url = st.secrets["postgres"]["DATABASE_URL"]
    except KeyError:
        st.error(
            "Configuração do banco de dados não encontrada nos Secrets! Verifique"
            " se adicionou [postgres] DATABASE_URL."
        )
        st.stop()

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id SERIAL PRIMARY KEY,
            data TEXT,
            tipo TEXT,
            responsavel TEXT,
            categoria TEXT,
            descricao TEXT,
            forma_pagamento TEXT,
            valor DOUBLE PRECISION
        )
    """)
    conn.commit()
    cursor.close()
    return conn


def salvar_no_db(data, tipo, responsavel, categoria, descricao, forma, valor):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO transacoes (data, tipo, responsavel, categoria, descricao, forma_pagamento, valor)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """,
        (data, tipo, responsavel, categoria, descricao, forma, valor),
    )
    conn.commit()
    cursor.close()
    conn.close()


def carregar_dados():
    db_url = st.secrets["postgres"]["DATABASE_URL"]
    try:
        df = pd.read_sql_query(
            "SELECT id, data, tipo, responsavel, categoria, descricao,"
            " forma_pagamento, valor FROM transacoes",
            db_url,
        )
    except Exception:
        conn = conectar_db()
        df = pd.read_sql_query(
            "SELECT id, data, tipo, responsavel, categoria, descricao,"
            " forma_pagamento, valor FROM transacoes",
            conn,
        )
        conn.close()

    if not df.empty:
        df.columns = [
            "ID",
            "Data",
            "Tipo",
            "Responsável",
            "Categoria",
            "Descrição",
            "Forma de Pagamento",
            "Valor",
        ]
    return df


def atualizar_linha_completa_db(
    id_registro, data, responsavel, categoria, descricao, forma, valor
):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE transacoes 
        SET data = %s, responsavel = %s, categoria = %s, descricao = %s, forma_pagamento = %s, valor = %s
        WHERE id = %s
    """,
        (data, responsavel, categoria, descricao, forma, valor, id_registro),
    )
    conn.commit()
    cursor.close()
    conn.close()


def deletar_linha_db(id_registro):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transacoes WHERE id = %s", (id_registro,))
    conn.commit()
    cursor.close()
    conn.close()


def deletar_tudo():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE transacoes RESTART IDENTITY;")
    conn.commit()
    cursor.close()
    conn.close()


def exportar_pdf_real(df, t_in, t_out, saldo, d_inicio, d_fim, filtro_resp):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    story = []

    styles = getSampleStyleSheet()
    style_titulo = ParagraphStyle(
        "TituloDoc",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#4a0e2e"),
        spaceAfter=4,
    )
    style_sub = ParagraphStyle(
        "SubTituloDoc",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#8a5a75"),
        spaceAfter=15,
    )
    style_body = ParagraphStyle(
        "CorpoTabela",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    style_header_tab = ParagraphStyle(
        "HeaderTabela",
        parent=styles["Normal"],
        fontSize=9,
        bold=True,
        textColor=colors.white,
    )

    story.append(
        Paragraph(
            "RELATÓRIO DE GESTÃO FINANCEIRA COMPARTILHADA", style_titulo
        )
    )
    hoje = datetime.now().strftime("%d/%m/%Y às %H:%M")
    story.append(
        Paragraph(
            f"Filtro: {filtro_resp} | Período: {d_inicio.strftime('%d/%m/%Y')}"
            f" até {d_fim.strftime('%d/%m/%Y')} — Gerado em {hoje}",
            style_sub,
        )
    )

    linha_div = Table([[""]], colWidths=[515], rowHeights=[2])
    linha_div.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d63384"))
        ])
    )
    story.append(linha_div)
    story.append(Spacer(1, 15))

    dados_resumo = [
        [
            Paragraph("<b>(+) Total de Receitas:</b>", style_body),
            Paragraph(
                f"R$ {t_in:.2f}",
                ParagraphStyle(
                    "R1",
                    parent=style_body,
                    textColor=colors.HexColor("#15803d"),
                    alignment=2,
                ),
            ),
        ],
        [
            Paragraph("<b>(-) Total de Despesas:</b>", style_body),
            Paragraph(
                f"R$ {t_out:.2f}",
                ParagraphStyle(
                    "R2",
                    parent=style_body,
                    textColor=colors.HexColor("#b91c1c"),
                    alignment=2,
                ),
            ),
        ],
        [
            Paragraph(
                "<b>(=) SALDO LÍQUIDO DO PERÍODO:</b>",
                ParagraphStyle("R3", parent=style_body, fontSize=11),
            ),
            Paragraph(
                f"R$ {saldo:.2f}",
                ParagraphStyle(
                    "R4", parent=style_body, fontSize=12, bold=True, alignment=2
                ),
            ),
        ],
    ]
    tab_resumo = Table(dados_resumo, colWidths=[350, 165])
    tab_resumo.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff5f8")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#fbcfe8")),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#f9a8d4")),
            ("LINEBELOW", (0, 1), (-1, 1), 0.5, colors.HexColor("#f9a8d4")),
        ])
    )
    story.append(tab_resumo)
    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            "<b>Extrato Detalhado de Movimentações</b>",
            ParagraphStyle(
                "SubT",
                parent=styles["Normal"],
                fontSize=12,
                spaceAfter=8,
                textColor=colors.HexColor("#4a0e2e"),
            ),
        )
    )

    colunas = [
        Paragraph("Data", style_header_tab),
        Paragraph("Quem", style_header_tab),
        Paragraph("Categoria", style_header_tab),
        Paragraph("Descrição", style_header_tab),
        Paragraph("Meio", style_header_tab),
        Paragraph("Valor", style_header_tab),
    ]
    dados_tabela = [colunas]

    for _, r in df.iterrows():
        cor_valor = (
            colors.HexColor("#15803d")
            if "Entrada" in r["Tipo"]
            else colors.HexColor("#b91c1c")
        )
        sinal = "+" if "Entrada" in r["Tipo"] else "-"
        desc_texto = r["Descrição"] if r["Descrição"] else "-"

        dados_tabela.append([
            Paragraph(r["Data"], style_body),
            Paragraph(r["Responsável"], style_body),
            Paragraph(r["Categoria"], style_body),
            Paragraph(desc_texto, style_body),
            Paragraph(r["Forma de Pagamento"], style_body),
            Paragraph(
                f"<b>{sinal} R$ {r['Valor']:.2f}</b>",
                ParagraphStyle("V1", parent=style_body, textColor=cor_valor),
            ),
        ])

    tab_extrato = Table(dados_tabela, colWidths=[60, 65, 95, 145, 75, 75])
    estilo_extrato = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d63384")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    for i in range(1, len(dados_tabela)):
        if i % 2 == 0:
            estilo_extrato.append((
                "BACKGROUND",
                (0, i),
                (-1, i),
                colors.HexColor("#fff5f8"),
            ))
        estilo_extrato.append((
            "LINEBELOW",
            (0, i),
            (-1, i),
            0.5,
            colors.HexColor("#fbcfe8"),
        ))

    tab_extrato.setStyle(TableStyle(estilo_extrato))
    story.append(tab_extrato)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# Inicializa banco de dados
conectar_db()

# --- HEADER DO SISTEMA ---
st.markdown(
    "<h1 style='text-align: center; color: #d63384;'>👩🏾‍❤️‍👩🏾 Central de Finanças"
    " Compartilhada</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #8a5a75;'>Planejamento financeiro"
    " inteligente, relatórios individuais e insights de gastos para o"
    " casal</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# --- DEFINIÇÃO DAS ABAS ---
tab_entrada, tab_saida, tab_geral, tab_estatisticas = st.tabs([
    "📥 Lançar Receitas",
    "📤 Lançar Despesas",
    "📊 Painel Geral & Filtros",
    "💡 Estatísticas & Previsões Inteligentes",
])

# --- ABA DE ENTRADAS ---
with tab_entrada:
    st.subheader("📥 Registro de Receitas (Individuais ou Conjuntas)")
    with st.form("form_entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input(
                "🗓️ Data do Recebimento", datetime.now(), key="date_in"
            )
            responsavel = st.selectbox(
                "👤 Quem recebeu?", LISTA_RESPONSAVEIS, key="resp_in"
            )
        with col2:
            categoria = st.selectbox(
                "📂 Origem do Recurso", LISTA_CATEGORIAS_ENTRADA, key="cat_in"
            )
            valor = st.number_input(
                "💵 Valor Recebido (R$)", min_value=0.0, step=0.01, key="val_in"
            )

        forma = st.selectbox(
            "💳 Meio de Recebimento",
            ["⚡ Pix", "🏦 Transferência", "💵 Dinheiro"],
            key="form_in",
        )
        descricao = st.text_area(
            "✍️ Notas Adicionais / Detalhes",
            placeholder="Ex: Salário da Empresa X",
            key="desc_in",
        )
        submit_in = st.form_submit_button(
            "Gravar Entrada ✅", use_container_width=True, type="primary"
        )

        if submit_in:
            if valor > 0:
                salvar_no_db(
                    data.strftime("%d/%m/%Y"),
                    "📥 Entrada",
                    responsavel,
                    categoria,
                    descricao,
                    forma,
                    valor,
                )
                st.success("Receita adicionada com sucesso!")
                st.balloons()
            else:
                st.warning("Por favor, digite um valor maior que R$ 0,00.")

# --- ABA DE SAÍDAS ---
with tab_saida:
    st.subheader("📤 Registro de Despesas")
    with st.form("form_saida", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input(
                "🗓️ Data do Pagamento", datetime.now(), key="date_out"
            )
            responsavel = st.selectbox(
                "👤 De quem é essa despesa?",
                LISTA_RESPONSAVEIS,
                key="resp_out",
            )
        with col2:
            categoria = st.selectbox(
                "📂 Categoria da Despesa", LISTA_CATEGORIAS_SAIDA, key="cat_out"
            )
            valor = st.number_input(
                "💵 Valor Pago (R$)", min_value=0.0, step=0.01, key="val_out"
            )

        forma = st.selectbox(
            "💳 Meio de Pagamento", LISTA_FORMAS_PAGAMENTO, key="form_out"
        )
        descricao = st.text_area(
            "✍️ Notas Adicionais / Detalhes",
            placeholder="Ex: Conta de luz do mês",
            key="desc_out",
        )
        submit_out = st.form_submit_button(
            "Gravar Despesa ❌", use_container_width=True, type="primary"
        )

        if submit_out:
            if valor > 0:
                salvar_no_db(
                    data.strftime("%d/%m/%Y"),
                    "📤 Saída",
                    responsavel,
                    categoria,
                    descricao,
                    forma,
                    valor,
                )
                st.toast("Despesa arquivada!", icon="📉")
                st.error("Despesa registrada.")
            else:
                st.warning("Por favor, digite um valor maior que R$ 0,00.")

# --- ABA DE VISÃO GERAL E FILTROS ---
with tab_geral:
    df_bruto = carregar_dados()

    if not df_bruto.empty:
        df_bruto["Data_Obj"] = pd.to_datetime(
            df_bruto["Data"], format="%d/%m/%Y"
        )

        st.subheader("🔍 Filtros de Visualização")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            data_inicio = st.date_input(
                "📅 Data Inicial:", datetime.now() - timedelta(days=30)
            )
        with col_f2:
            data_fim = st.date_input("📅 Data Final:", datetime.now())
        with col_f3:
            filtro_responsavel = st.selectbox(
                "👤 Filtrar por Responsável:", ["Todos"] + LISTA_RESPONSAVEIS
            )

        df = df_bruto[
            (df_bruto["Data_Obj"] >= pd.Timestamp(data_inicio))
            & (df_bruto["Data_Obj"] <= pd.Timestamp(data_fim))
        ].copy()

        if filtro_responsavel != "Todos":
            df = df[df["Responsável"] == filtro_responsavel]

        df.drop(columns=["Data_Obj"], inplace=True)

        t_in = df[df["Tipo"].str.contains("Entrada")]["Valor"].sum()
        t_out = df[df["Tipo"].str.contains("Saída")]["Valor"].sum()
        saldo = t_in - t_out

        st.markdown("---")
        st.subheader(f"📊 Resumo Financeiro ({filtro_responsavel})")

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Total Entradas",
            f"R$ {t_in:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", "."),
        )
        c2.metric(
            "Total Saídas",
            f"R$ {t_out:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", "."),
        )
        c3.metric(
            "Saldo Líquido",
            f"R$ {saldo:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", "."),
            delta=f"R$ {saldo:,.2f}",
            delta_color="normal" if saldo >= 0 else "inverse",
        )

        st.markdown("---")

        col_tabela, col_modificacao = st.columns([2, 1])

        with col_tabela:
            st.subheader("📋 Lançamentos Encontrados")
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)

                pdf_data = exportar_pdf_real(
                    df,
                    t_in,
                    t_out,
                    saldo,
                    data_inicio,
                    data_fim,
                    filtro_responsavel,
                )
                nome_arquivo = (
                    f"Relatorio_Financas_{data_inicio.strftime('%d%m%Y')}_a_{data_fim.strftime('%d%m%Y')}.pdf"
                )

                st.download_button(
                    label="📥 BAIXAR RELATÓRIO DO PERÍODO EM PDF",
                    data=pdf_data,
                    file_name=nome_arquivo,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            else:
                st.warning(
                    "Nenhum lançamento encontrado para os filtros"
                    " selecionados."
                )

            with st.expander("🚨 Zona de Perigo"):
                if st.button(
                    "🗑️ Apagar Todo o Histórico", use_container_width=True
                ):
                    deletar_tudo()
                    st.rerun()

        with col_modificacao:
            with st.container(border=True):
                st.subheader("🛠️ Ajuste ou Exclusão")
                if not df.empty:
                    opcoes_itens = [
                        f"ID: {r['ID']} | {r['Responsável']} - {r['Categoria']}"
                        f" - R$ {r['Valor']:.2f}"
                        for _, r in df.iterrows()
                    ]
                    item_selecionado_texto = st.selectbox(
                        "🔍 Escolha o Lançamento:", opcoes_itens
                    )

                    if item_selecionado_texto:
                        id_selecionado = int(
                            item_selecionado_texto.split(" | ")[0].replace(
                                "ID: ", ""
                            )
                        )
                        dados_atuais = df.loc[df["ID"] == id_selecionado].iloc[
                            0
                        ]
                        data_atual_dt = datetime.strptime(
                            dados_atuais["Data"], "%d/%m/%Y"
                        )

                        st.markdown("---")
                        st.write(f"✏️ **Editando ID {id_selecionado}:**")

                        nova_data = st.date_input(
                            "Corrigir Data:",
                            value=data_atual_dt,
                            key=f"data_{id_selecionado}",
                        )
                        novo_resp = st.selectbox(
                            "Corrigir Responsável:",
                            LISTA_RESPONSAVEIS,
                            index=LISTA_RESPONSAVEIS.index(
                                dados_atuais["Responsável"]
                            ),
                            key=f"resp_{id_selecionado}",
                        )

                        lista_cat_dinamica = (
                            LISTA_CATEGORIAS_ENTRADA
                            if "Entrada" in dados_atuais["Tipo"]
                            else LISTA_CATEGORIAS_SAIDA
                        )
                        idx_cat = (
                            lista_cat_dinamica.index(dados_atuais["Categoria"])
                            if dados_atuais["Categoria"] in lista_cat_dinamica
                            else 0
                        )
                        nova_categoria = st.selectbox(
                            "Corrigir Categoria:",
                            lista_cat_dinamica,
                            index=idx_cat,
                            key=f"cat_{id_selecionado}",
                        )

                        novo_valor = st.number_input(
                            "Corrigir Valor:",
                            min_value=0.0,
                            value=float(dados_atuais["Valor"]),
                            step=0.01,
                            key=f"valor_{id_selecionado}",
                        )
                        nova_desc = st.text_area(
                            "Corrigir Descrição:",
                            value=str(dados_atuais["Descrição"]),
                            key=f"desc_{id_selecionado}",
                        )
                        nova_forma = st.selectbox(
                            "Corrigir Meio:",
                            LISTA_FORMAS_PAGAMENTO,
                            index=LISTA_FORMAS_PAGAMENTO.index(
                                dados_atuais["Forma de Pagamento"]
                            )
                            if dados_atuais["Forma de Pagamento"]
                            in LISTA_FORMAS_PAGAMENTO
                            else 0,
                            key=f"forma_{id_selecionado}",
                        )

                        c_btn1, c_btn2 = st.columns(2)
                        with c_btn1:
                            if st.button(
                                "💾 Salvar",
                                use_container_width=True,
                                type="primary",
                                key=f"btn_salvar_{id_selecionado}",
                            ):
                                atualizar_linha_completa_db(
                                    id_selecionado,
                                    nova_data.strftime("%d/%m/%Y"),
                                    novo_resp,
                                    nova_categoria,
                                    nova_desc,
                                    nova_forma,
                                    novo_valor,
                                )
                                st.rerun()
                        with c_btn2:
                            if st.button(
                                "❌ Excluir",
                                use_container_width=True,
                                key=f"btn_deletar_{id_selecionado}",
                            ):
                                deletar_linha_db(id_selecionado)
                                st.rerun()
                else:
                    st.caption("Nenhum item disponível para edição.")

# --- ABA DE ESTATÍSTICAS & INSIGHTS ---
with tab_estatisticas:
    st.subheader("💡 Inteligência Financeira e Estatísticas")
    df_estat = carregar_dados()

    if not df_estat.empty:
        df_estat["Data_Obj"] = pd.to_datetime(
            df_estat["Data"], format="%d/%m/%Y"
        )
        df_estat["Mês/Ano"] = df_estat["Data_Obj"].dt.strftime("%m/%Y")

        entradas_totais = df_estat[df_estat["Tipo"].str.contains("Entrada")]
        despesas_totais = df_estat[df_estat["Tipo"].str.contains("Saída")]

        st.markdown("### 📊 Divisão Individual de Contribuições e Gastos")

        lista_meses_disponiveis = sorted(
            list(df_estat["Mês/Ano"].unique()),
            key=lambda x: datetime.strptime(x, "%m/%Y"),
            reverse=True,
        )
        opcoes_filtro_mes = ["Todo o Histórico"] + lista_meses_disponiveis

        mes_selecionado = st.selectbox(
            "📆 Selecione o mês para detalhar as contas individuais:",
            opcoes_filtro_mes,
        )

        if mes_selecionado == "Todo o Histórico":
            df_estat_filtrado_mes = df_estat.copy()
        else:
            df_estat_filtrado_mes = df_estat[
                df_estat["Mês/Ano"] == mes_selecionado
            ].copy()

        entradas_mes = df_estat_filtrado_mes[
            df_estat_filtrado_mes["Tipo"].str.contains("Entrada")
        ]
        despesas_mes = df_estat_filtrado_mes[
            df_estat_filtrado_mes["Tipo"].str.contains("Saída")
        ]

        in_leticia = entradas_mes[
            entradas_mes["Responsável"].str.contains("Leticia")
        ]["Valor"].sum()
        in_amanda = entradas_mes[
            entradas_mes["Responsável"].str.contains("Amanda")
        ]["Valor"].sum()
        in_conjunto = entradas_mes[
            entradas_mes["Responsável"].str.contains("Conjunto")
        ]["Valor"].sum()

        out_leticia = despesas_mes[
            despesas_mes["Responsável"].str.contains("Leticia")
        ]["Valor"].sum()
        out_amanda = despesas_mes[
            despesas_mes["Responsável"].str.contains("Amanda")
        ]["Valor"].sum()
        out_conjunto = despesas_mes[
            despesas_mes["Responsável"].str.contains("Conjunto")
        ]["Valor"].sum()

        col_let, col_ama, col_conj = st.columns(3)

        with col_let:
            with st.container(border=True):
                st.markdown("#### 👩🏽 Leticia")
                st.markdown(
                    "**Contribuiu com:** R$"
                    f" {in_leticia:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                st.markdown(
                    "**Gastou individualmente:** R$"
                    f" {out_leticia:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

        with col_ama:
            with st.container(border=True):
                st.markdown("#### 👩🏾 Amanda")
                st.markdown(
                    "**Contribuiu com:** R$"
                    f" {in_amanda:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                st.markdown(
                    "**Gastou individualmente:** R$"
                    f" {out_amanda:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

        with col_conj:
            with st.container(border=True):
                st.markdown("#### 🏡 Conta / Custos Conjuntos")
                st.markdown(
                    "**Receitas em parceria:** R$"
                    f" {in_conjunto:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                st.markdown(
                    "**Despesas da Casa/Mútuas:** R$"
                    f" {out_conjunto:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

        st.markdown("---")

        st.markdown("### 🎯 Metas & Recomendações Semanais")

        valor_sugerido_guardar = entradas_totais["Valor"].sum() * 0.20

        saldo_atual_geral = (
            entradas_totais["Valor"].sum() - despesas_totais["Valor"].sum()
        )
        hoje = datetime.now()
        dias_restantes_mes = 32 - hoje.day if hoje.day > 28 else 30 - hoje.day
        gasto_diario_permitido = (
            (saldo_atual_geral / dias_restantes_mes)
            if saldo_atual_geral > 0 and dias_restantes_mes > 0
            else 0
        )

        col_rec1, col_rec2 = st.columns(2)
        with col_rec1:
            st.info(
                "**💰 Meta de Economia Atendida:** Sugerimos guardar **R$"
                f" {valor_sugerido_guardar:,.2f}** (20% de toda a renda"
                " histórica de vocês) para investimentos ou reserva de"
                " emergência."
            )
        with col_rec2:
            if gasto_diario_permitido > 0:
                st.success(
                    "**📅 Limite de Gasto Diário Ideal:** Para fechar o mês"
                    " atual no positivo, o casal pode gastar, no máximo, **R$"
                    f" {gasto_diario_permitido:,.2f} por dia**."
                )
            else:
                st.write(
                    "⚠️ **Atenção:** No momento, o saldo acumulado está zerado"
                    " ou negativo. Evitem gastos supérfluos."
                )

        st.markdown("---")

        st.markdown(
            "### 📈 Evolução Histórica de Gastos e Divisão de Categorias"
        )

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.write("**Evolução de Gastos Mensais (R$)**")
            if not despesas_totais.empty:
                gastos_por_mes = despesas_totais.groupby("Mês/Ano")[
                    "Valor"
                ].sum()
                st.line_chart(gastos_por_mes)
            else:
                st.caption("Sem despesas registradas para exibir o histórico.")

        with col_g2:
            st.write("**Distribuição de Gastos por Categoria (%)**")
            if not despesas_totais.empty:
                gastos_por_cat = despesas_totais.groupby("Categoria")[
                    "Valor"
                ].sum()
                st.bar_chart(gastos_por_cat)
            else:
                st.caption("Sem despesas registradas.")

        st.markdown("---")

        st.markdown("### 🔮 Projeção para o Próximo Mês")

        media_receita = (
            entradas_totais.groupby("Mês/Ano")["Valor"].sum().mean()
            if not entradas_totais.empty
            else 0
        )
        media_despesa = (
            despesas_totais.groupby("Mês/Ano")["Valor"].sum().mean()
            if not despesas_totais.empty
            else 0
        )
        previsao_saldo = media_receita - media_despesa

        st.write(
            "Com base na média histórica das suas movimentações mensais, a"
            " previsão para o **próximo mês** é:"
        )
        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.metric("Previsão de Renda", f"R$ {media_receita:,.2f}")
        col_p2.metric("Previsão de Custos", f"R$ {media_despesa:,.2f}")
        col_p3.metric(
            "Resultado Esperado",
            f"R$ {previsao_saldo:,.2f}",
            delta=f"R$ {previsao_saldo:,.2f}",
        )

    else:
        st.warning(
            "Adicione os primeiros lançamentos para liberar as estatísticas e"
            " inteligência do sistema."
        )