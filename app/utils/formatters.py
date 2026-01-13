# app/utils/formatters.py
"""
Formatters pour les messages.

Formate les rapports pour différents canaux de communication.
"""

from typing import Dict, Any
from decimal import Decimal
import textwrap
import re


def escape_markdown(text: str) -> str:
    """
    Échappe les caractères spéciaux Markdown pour WhatsApp/Telegram.

    Protège contre la corruption du formatage si company_name ou autres
    champs contiennent des caractères Markdown (* _ ` [ ]).

    Args:
        text: Texte potentiellement dangereux

    Returns:
        Texte sécurisé

    Example:
        >>> escape_markdown("Société_ABC*2000")
        "Société\\_ABC\\*2000"
    """
    if not text:
        return text

    # Échapper les caractères spéciaux Markdown
    # * _ ` [ ] ( ) # + - . !
    special_chars = r'([*_`\[\]()#+\-.!\\])'
    return re.sub(special_chars, r'\\\1', str(text))


class WhatsAppFormatter:
    """
    Formatte les rapports pour WhatsApp et Telegram.

    - WhatsApp limite : 4096 caractères
    - Telegram : aucune limite
    - Ce formatter NE TRONQUE JAMAIS le contenu.
    - Si le message dépasse la limite WhatsApp, il sera SPLITTÉ proprement.
    """

    WHATSAPP_LIMIT = 4096

    @staticmethod
    def format_report(report_data: Dict[str, Any]) -> str:
        """
        Formate un rapport complet.

        Retourne un message formaté (non splitté - le split se fait lors de l'envoi si nécessaire).

        Args:
            report_data: Dictionnaire ou modèle Pydantic

        Returns:
            str : message formaté pour WhatsApp/Telegram
        """

        # Convertir depuis Pydantic si nécessaire
        if hasattr(report_data, "model_dump"):
            report_dict = report_data.model_dump()
        else:
            report_dict = dict(report_data)

        company_name = report_dict.get("company_name", "Entreprise")
        period_name = report_dict.get("period_name", "Période")
        period_range = report_dict.get("period_range", "")
        kpis = report_dict.get("kpis", {})
        kpis_comparison = report_dict.get("kpis_comparison", {})
        recommendations = report_dict.get("recommendations", "")

        # ⚡ SECURITY: Échapper les caractères spéciaux Markdown
        company_name = escape_markdown(company_name)
        period_name = escape_markdown(period_name)
        period_range = escape_markdown(period_range)

        # -----------------------
        # Construire le message
        # -----------------------

        lines = []

        # En-tête
        lines.append(f"📊 *Rapport {period_name} - {company_name}*")
        lines.append(f"📅 {period_range}\n")

        # KPIs
        lines.append("*📈 Indicateurs Clés*")

        # CA
        revenue = kpis.get("total_revenue", 0)
        revenue_str = WhatsAppFormatter._format_amount(revenue)
        revenue_var = kpis_comparison.get("revenue_variation")
        if revenue_var is not None:
            emoji = "📈" if revenue_var > 0 else "📉" if revenue_var < 0 else "➡️"
            lines.append(f"💰 CA: {revenue_str} XAF ({emoji} {revenue_var:+.1f}%)")
        else:
            lines.append(f"💰 CA: {revenue_str} XAF")

        # Ventes
        sales = kpis.get("total_sales", 0)
        sales_var = kpis_comparison.get("sales_variation")
        if sales_var is not None:
            emoji = "📈" if sales_var > 0 else "📉" if sales_var < 0 else "➡️"
            lines.append(f"🛒 Ventes: {sales:,} ({emoji} {sales_var:+.1f}%)")
        else:
            lines.append(f"🛒 Ventes: {sales:,}")

        # Clients
        new_customers = kpis.get("new_customers", 0)
        returning = kpis.get("returning_customers", 0)
        returning_var = kpis_comparison.get("returning_customers_variation")

        lines.append(f"👥 Nouveaux clients: {new_customers:,}")
        if returning_var is not None:
            emoji = "📈" if returning_var > 0 else "📉" if returning_var < 0 else "➡️"
            lines.append(f"🔄 Clients récurrents: {returning:,} ({emoji} {returning_var:+.0f})")
        else:
            lines.append(f"🔄 Clients récurrents: {returning:,}")

        # Stocks
        stock_alerts = kpis.get("stock_alerts_count", 0)
        if stock_alerts:
            lines.append(f"⚠️ Alertes stock: {stock_alerts}")

        # Dépenses
        expenses = kpis.get("total_expenses", 0)
        expenses_str = WhatsAppFormatter._format_amount(expenses)
        expenses_var = kpis_comparison.get("expenses_variation")
        if expenses_var is not None:
            emoji = "📈" if expenses_var > 0 else "📉" if expenses_var < 0 else "➡️"
            lines.append(f"💸 Dépenses: {expenses_str} XAF ({emoji} {expenses_var:+.1f}%)")
        else:
            lines.append(f"💸 Dépenses: {expenses_str} XAF")

        # Résultat net
        net = kpis.get("net_result", 0)
        net_str = WhatsAppFormatter._format_amount(net)
        emoji = "📈" if net > 0 else "📉"
        lines.append(f"{emoji} Résultat net: {net_str} XAF\n")

        # Recommandations
        if recommendations:
            lines.append("*💡 Recommandations*")
            lines.append(recommendations + "\n")

        # Footer
        lines.append("---")
        lines.append("L'équipe Genuka 🚀")

        full_message = "\n".join(lines)

        # Retourner le message complet (le split sera fait lors de l'envoi si nécessaire)
        return full_message

    # ---------------------------------------------------------------------
    # UTILITAIRES
    # ---------------------------------------------------------------------

    @staticmethod
    def _format_amount(amount: Any) -> str:
        if isinstance(amount, Decimal):
            amount = float(amount)
        return f"{amount:,.0f}"

    @staticmethod
    def _split_into_chunks(message: str) -> list[str]:
        """
        Découpe le message en blocs de 4096 caractères max,
        sans jamais couper un mot.
        """

        if len(message) <= WhatsAppFormatter.WHATSAPP_LIMIT:
            return [message]

        chunks = []

        wrapper = textwrap.TextWrapper(
            width=WhatsAppFormatter.WHATSAPP_LIMIT,
            break_long_words=False,
            break_on_hyphens=False
        )

        parts = wrapper.wrap(message)
        for i, part in enumerate(parts, 1):
            chunks.append(f"{part}\n\n(Part {i}/{len(parts)})")

        return chunks

    @staticmethod
    def format_error_message(company_name: str, error: str) -> str:
        # ⚡ SECURITY: Échapper les caractères spéciaux Markdown
        company_name = escape_markdown(company_name)
        error = escape_markdown(error)

        return (
            f"⚠️ *Rapport {company_name}*\n\n"
            f"Impossible de générer le rapport.\n"
            f"Erreur: {error}\n\n"
            f"L'équipe Genuka a été notifiée."
        )
