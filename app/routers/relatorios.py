from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import extract
from datetime import datetime
from typing import Optional
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from app.database import get_db
from app import models

router = APIRouter(prefix="/relatorio", tags=["Relatórios"])

AZUL        = colors.HexColor("#1A5276")
AZUL_CLARO  = colors.HexColor("#D6EAF8")
CINZA_BG    = colors.HexColor("#F4F6F7")
CINZA_TEXT  = colors.HexColor("#2C3E50")
VERDE       = colors.HexColor("#1E8449")
VERMELHO    = colors.HexColor("#922B21")
BRANCO      = colors.white

MESES_PT  = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
             "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
MESES_ABR = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]


def fmt_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def coletar_dados(db: Session, mes: int, ano: int) -> dict:
    ags = (
        db.query(models.Agendamento)
        .filter(
            extract("month", models.Agendamento.data_hora) == mes,
            extract("year",  models.Agendamento.data_hora) == ano,
        )
        .order_by(models.Agendamento.data_hora)
        .all()
    )

    concluidos = [a for a in ags if a.status == "concluido"]
    cancelados = [a for a in ags if a.status == "cancelado"]
    agendados  = [a for a in ags if a.status == "agendado"]

    fat_pago     = sum(a.pagamento.valor for a in concluidos if a.pagamento and a.pagamento.status == "pago")
    fat_pendente = sum(a.pagamento.valor for a in concluidos if a.pagamento and a.pagamento.status == "pendente")

    contagem = {}
    for a in ags:
        contagem[a.servico.nome] = contagem.get(a.servico.nome, 0) + 1
    servico_top = max(contagem, key=contagem.get) if contagem else "—"

    formas = {}
    for a in concluidos:
        if a.pagamento and a.pagamento.forma_pagamento and a.pagamento.status == "pago":
            f = a.pagamento.forma_pagamento.upper()
            formas[f] = formas.get(f, 0) + 1

    total = len(ags)
    return {
        "ags": ags,
        "total": total,
        "concluidos": len(concluidos),
        "cancelados": len(cancelados),
        "agendados":  len(agendados),
        "fat_pago":      fat_pago,
        "fat_pendente":  fat_pendente,
        "servico_top":   servico_top,
        "formas":        formas,
        "taxa": round(len(concluidos) / total * 100, 1) if total else 0,
    }


def gerar_pdf(d: dict, mes: int, ano: int) -> bytes:
    """Gera o PDF em memória e retorna os bytes."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    def st(name, **kw):
        return ParagraphStyle(name, **kw)

    S_TITULO = st("titulo", fontSize=20, textColor=AZUL,      alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4)
    S_SUB    = st("sub",    fontSize=13, textColor=CINZA_TEXT, alignment=TA_CENTER, fontName="Helvetica",     spaceAfter=2)
    S_GERADO = st("gerado", fontSize=9,  textColor=colors.grey,alignment=TA_CENTER, spaceAfter=16)
    S_SECAO  = st("secao",  fontSize=11, textColor=AZUL,       fontName="Helvetica-Bold", spaceAfter=10, spaceBefore=4)
    S_RODAPE = st("rodape", fontSize=10, textColor=CINZA_TEXT, alignment=TA_CENTER)

    story.append(Paragraph("SISTEMA DE AGENDAMENTO", S_TITULO))
    story.append(Paragraph(f"Relatório Mensal — {MESES_PT[mes-1]} {ano}", S_SUB))
    story.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", S_GERADO))
    story.append(HRFlowable(width="100%", thickness=2, color=AZUL, spaceAfter=18))

    story.append(Paragraph("RESUMO DO MÊS", S_SECAO))

    def make_card(valor_str, label, cor_num=AZUL):
        s_num = st(f"cn_{label}", fontSize=26, textColor=cor_num,
                   fontName="Helvetica-Bold", alignment=TA_CENTER, leading=32)
        s_lbl = st(f"cl_{label}", fontSize=8, textColor=CINZA_TEXT,
                   alignment=TA_CENTER, leading=12)
        t = Table(
            [[Paragraph(valor_str, s_num)],
             [Paragraph(label, s_lbl)]],
            colWidths=[4.1*cm],
        )
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), CINZA_BG),
            ("BOX",           (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
            ("RIGHTPADDING",  (0,0), (-1,-1), 4),
        ]))
        return t

    cards_row = [[
        make_card(str(d["total"]),      "Total de Agendamentos"),
        make_card(str(d["concluidos"]), "Concluídos",  VERDE),
        make_card(str(d["cancelados"]), "Cancelados",  VERMELHO),
        make_card(f"{d['taxa']}%",      "Taxa de Conclusão"),
    ]]
    tabela_cards = Table(cards_row, colWidths=[4.1*cm]*4, hAlign="CENTER")
    tabela_cards.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
    ]))
    story.append(tabela_cards)
    story.append(Spacer(1, 20))

    story.append(Paragraph("FATURAMENTO", S_SECAO))
    total_fat = d["fat_pago"] + d["fat_pendente"]
    linhas_fat = [
        ["", "Valor"],
        ["Recebido (pago)",      fmt_brl(d["fat_pago"])],
        ["A receber (pendente)", fmt_brl(d["fat_pendente"])],
        ["TOTAL PREVISTO",       fmt_brl(total_fat)],
    ]
    t_fat = Table(linhas_fat, colWidths=[12*cm, 5*cm])
    t_fat.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), AZUL),
        ("TEXTCOLOR",     (0,0), (-1,0), BRANCO),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("ALIGN",         (1,0), (1,-1), "RIGHT"),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [BRANCO, CINZA_BG]),
        ("BACKGROUND",    (0,-1),(-1,-1), AZUL_CLARO),
        ("FONTNAME",      (0,-1),(-1,-1), "Helvetica-Bold"),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("INNERGRID",     (0,0), (-1,-1), 0.4, colors.lightgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    story.append(t_fat)
    story.append(Spacer(1, 20))

    if d["formas"]:
        story.append(Paragraph("FORMAS DE PAGAMENTO RECEBIDAS", S_SECAO))
        linhas_fp = [["Forma de Pagamento", "Quantidade"]]
        for forma, qtd in d["formas"].items():
            linhas_fp.append([forma, str(qtd)])
        t_fp = Table(linhas_fp, colWidths=[12*cm, 5*cm])
        t_fp.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), AZUL),
            ("TEXTCOLOR",     (0,0), (-1,0), BRANCO),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 10),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [BRANCO, CINZA_BG]),
            ("ALIGN",         (1,0), (1,-1), "CENTER"),
            ("BOX",           (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("INNERGRID",     (0,0), (-1,-1), 0.4, colors.lightgrey),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ]))
        story.append(t_fp)
        story.append(Spacer(1, 20))

    story.append(Paragraph("TODOS OS AGENDAMENTOS DO MÊS", S_SECAO))

    if not d["ags"]:
        story.append(Paragraph(
            "Nenhum agendamento registrado neste período.",
            st("vazio", fontSize=10, textColor=colors.grey)
        ))
    else:
        STATUS_COR = {"concluido": VERDE, "cancelado": VERMELHO, "agendado": AZUL}
        STATUS_PT  = {"concluido": "CONCLUÍDO", "cancelado": "CANCELADO", "agendado": "AGENDADO"}

        linhas_ag = [["#", "Data / Hora", "Cliente", "Serviço", "Valor", "Status"]]
        for ag in d["ags"]:
            linhas_ag.append([
                str(ag.id),
                ag.data_hora.strftime("%d/%m  %H:%M"),
                ag.cliente.nome[:24],
                ag.servico.nome[:26],
                fmt_brl(ag.servico.preco),
                STATUS_PT.get(ag.status, ag.status.upper()),
            ])

        t_ag = Table(linhas_ag, colWidths=[0.8*cm, 2.6*cm, 4*cm, 4*cm, 2.3*cm, 2.8*cm])
        style_ag = TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), AZUL),
            ("TEXTCOLOR",     (0,0), (-1,0), BRANCO),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 8.5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [BRANCO, CINZA_BG]),
            ("ALIGN",         (0,0), (0,-1), "CENTER"),
            ("ALIGN",         (4,0), (4,-1), "RIGHT"),
            ("ALIGN",         (5,0), (5,-1), "CENTER"),
            ("BOX",           (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ])
        for i, ag in enumerate(d["ags"], start=1):
            cor = STATUS_COR.get(ag.status, CINZA_TEXT)
            style_ag.add("TEXTCOLOR", (5, i), (5, i), cor)
            style_ag.add("FONTNAME",  (5, i), (5, i), "Helvetica-Bold")

        t_ag.setStyle(style_ag)
        story.append(t_ag)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceAfter=10))
    story.append(Paragraph(
        f"Serviço mais agendado no mês: <b>{d['servico_top']}</b>",
        S_RODAPE
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


@router.get("/")
def gerar_relatorio(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    db: Session = Depends(get_db)
):
    agora = datetime.now()
    mes   = mes or agora.month
    ano   = ano or agora.year

    if not (1 <= mes <= 12):
        raise HTTPException(status_code=400, detail="Mês inválido. Use 1 a 12.")
    if ano < 2000 or ano > agora.year + 1:
        raise HTTPException(status_code=400, detail="Ano inválido.")

    dados = coletar_dados(db, mes, ano)
    pdf_bytes = gerar_pdf(dados, mes, ano)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=relatorio_{MESES_ABR[mes-1]}_{ano}.pdf"}
    )