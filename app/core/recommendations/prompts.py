# app/core/recommendations/prompts.py
"""
Templates de prompts pour Gemini.

Contient tous les prompts structurés pour générer des recommandations
pertinentes et actionnables sous forme de liste.
"""

from typing import List
from app.domain.models import KPIData, KPIComparison, InsightModel

class PromptBuilder:
    """
    Constructeur de prompts pour Gemini.
    
    Génère des prompts structurés et contextualisés pour obtenir
    des recommandations claires et actionnables.
    """
    
    @staticmethod
    def build_recommendations_prompt(
        company_name: str,
        period_name: str,
        period_range: str,
        kpis: KPIData,
        kpis_comparison: KPIComparison,
        insights: List[InsightModel]
    ) -> str:
        """
        Construit le prompt complet pour générer des recommandations.
        """
        insights_text = PromptBuilder._format_insights(insights)
        kpis_text = PromptBuilder._format_kpis_with_variations(kpis, kpis_comparison)
        situation = PromptBuilder._analyze_situation(kpis, kpis_comparison)
        
        prompt = f"""Tu es un conseiller financier expert pour les PME au Cameroun.
Analyse ces données pour l'entreprise "{company_name}" et génère 2-3 recommandations CONCRÈTES, ACTIONNABLES et sous forme de liste.

Période analysée: {period_name} ({period_range})

Situation globale: {situation}

{kpis_text}

{insights_text}

Consignes STRICTES:
- Maximum 150 mots
- Ton encourageant et professionnel
- Recommandations ACTIONNABLES avec chiffres concrets
- Priorité aux insights les plus critiques
- Pas de préambule
- Utilisez le format liste avec "-" pour chaque recommandation
- Commence directement par les recommandations

Recommandations:"""
        return prompt
    
    @staticmethod
    def _format_insights(insights: List[InsightModel]) -> str:
        if not insights:
            return "Insights critiques: Aucun insight"
        
        insights_lines = []
        for insight in insights:
            if insight.priority >= 4:
                impact = f" (Impact: {float(insight.financial_impact):,.0f} XAF)" if insight.financial_impact else ""
                insights_lines.append(f"- {insight.description}{impact}")
        return "\n".join(insights_lines)
    
    @staticmethod
    def _format_kpis_with_variations(kpis: KPIData, comparison: KPIComparison) -> str:
        def fmt_var(v: float) -> str:
            if v > 0: return f"📈 +{v:.1f}%"
            elif v < 0: return f"📉 {v:.1f}%"
            else: return "→ 0%"
        
        lines = [
            f"- CA: {float(kpis.total_revenue):,.0f} XAF ({fmt_var(comparison.revenue_variation)})",
            f"- Ventes: {kpis.total_sales} commandes ({fmt_var(comparison.sales_variation)})",
            f"- Nouveaux clients: {kpis.new_customers}",
            f"- Clients récurrents: {kpis.returning_customers} ({comparison.returning_customers_variation:+d} vs avant)",
            f"- Dépenses: {float(kpis.total_expenses):,.0f} XAF ({fmt_var(comparison.expenses_variation)})",
            f"- Résultat net: {float(kpis.net_result):,.0f} XAF"
        ]
        if kpis.stock_alerts_count > 0:
            lines.append(f"- ⚠️ Alertes stock: {kpis.stock_alerts_count}")
        return "\n".join(lines)
    
    @staticmethod
    def _analyze_situation(kpis: KPIData, comparison: KPIComparison) -> str:
        if kpis.net_result < 0: prof = "en déficit"
        elif kpis.total_revenue > 0:
            margin = float(kpis.net_result / kpis.total_revenue * 100)
            if margin > 30: prof = "très rentable"
            elif margin > 15: prof = "rentable"
            else: prof = "faiblement rentable"
        else: prof = "sans activité"
        
        if comparison.revenue_variation > 20: trend = "en forte croissance"
        elif comparison.revenue_variation > 5: trend = "en croissance"
        elif comparison.revenue_variation < -20: trend = "en forte baisse"
        elif comparison.revenue_variation < -5: trend = "en baisse"
        else: trend = "stable"
        
        return f"Entreprise {prof}, {trend}"
    
    @staticmethod
    def build_fallback_prompt(
        kpis: KPIData,
        kpis_comparison: KPIComparison,
        insights: List[InsightModel]
    ) -> str:
        """
        Prompt simplifié si Gemini échoue. Génère max 3 recommandations liste.
        """
        recs = []
        if kpis.net_result < 0:
            pct = abs(float(kpis.net_result / kpis.total_revenue * 100)) if kpis.total_revenue > 0 else 0
            recs.append(f"- Urgence: réduisez vos dépenses de {pct:.0f}% pour revenir à l'équilibre.")
        if kpis_comparison.revenue_variation < -15:
            recs.append(f"- Vos ventes ont chuté de {abs(kpis_comparison.revenue_variation):.0f}%. Lancez une promotion ciblée.")
        elif kpis_comparison.revenue_variation > 25:
            recs.append(f"- Excellente croissance de {kpis_comparison.revenue_variation:.0f}% ! Augmentez vos stocks.")
        
        total_customers = kpis.new_customers + kpis.returning_customers
        if total_customers > 0:
            retention_rate = (kpis.returning_customers / total_customers) * 100
            if retention_rate < 30:
                recs.append(f"- Seulement {retention_rate:.0f}% de clients récurrents. Créez un programme de fidélité.")
        
        for insight in insights:
            if insight.priority >= 4:
                recs.append(f"- {insight.description}")
                break
        
        if not recs: recs.append("- Continuez vos efforts actuels et surveillez vos indicateurs.")
        
        return " ".join(recs[:3])
