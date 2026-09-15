"""Conversational product copy; no model-controlled status or actions."""
import re

ACK = "⏳ Evidência recebida! Analisando a tela e estruturando a tarefa..."
RETRY = "🔄 A IA está pensando mais um pouco... Tentando novamente."


def one_line(text, limit=180):
    return re.sub(r"\s+", " ", text).strip()[:limit]


def success_message(ticket, report=None):
    title = one_line(report.title) if report else "Relato registrado"
    if report and report.analysis_status == "pending":
        return (f"✅ {ticket.identifier} criado: {title}\n"
                "Ticket criado, mas a IA está fora do ar para detalhar a descrição no momento.\n"
                f"Label: ai-pending\n{ticket.url}")
    priority = {"nenhuma": "Não definida", "baixa": "Baixa", "media": "Média", "alta": "Alta", "urgente": "Urgente"}
    return (f"✅ {ticket.identifier} criado: {title}\n"
            f"Prioridade sugerida: {priority[report.suggested_priority] if report else 'Não definida'}\n{ticket.url}")
