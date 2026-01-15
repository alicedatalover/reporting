"""
Configuration Celery Beat pour l'exécution automatique des rapports.
Définit le planning d'exécution (chaque lundi à 8h, 1er du mois, etc.).
"""

from celery.schedules import crontab


# ==================== SCHEDULE CELERY BEAT ====================

celery_schedule = {
    # Rapports hebdomadaires : Chaque lundi à 8h00 (heure Douala)
    "weekly-reports": {
        "task": "app.worker.tasks.generate_scheduled_reports",
        "schedule": crontab(
            hour=8,
            minute=0,
            day_of_week=1  # Lundi = 1 (0=dimanche, 6=samedi)
        ),
        "args": ("weekly",),
        "options": {
            "expires": 3600,  # Expire après 1h si pas exécuté
        }
    },

    # Rapports mensuels : 1er de chaque mois à 9h00
    "monthly-reports": {
        "task": "app.worker.tasks.generate_scheduled_reports",
        "schedule": crontab(
            hour=9,
            minute=0,
            day_of_month=1  # 1er du mois
        ),
        "args": ("monthly",),
        "options": {
            "expires": 7200,  # Expire après 2h
        }
    },

    # Health check : Toutes les heures (pour monitoring)
    # "health-check": {
    #     "task": "app.worker.tasks.health_check_task",
    #     "schedule": crontab(minute=0),  # Toutes les heures à minute 0
    # },
}


# ==================== NOTES SUR LE SCHEDULING ====================

"""
Formats crontab disponibles :

1. Jours de la semaine :
   day_of_week=1  # Lundi
   day_of_week="mon"  # Lundi aussi

2. Jours du mois :
   day_of_month=1  # 1er du mois
   day_of_month="1,15"  # 1er et 15 de chaque mois

3. Heures/Minutes :
   hour=8, minute=0  # 8h00
   hour="8,12,17"  # 8h, 12h, 17h
   hour="*/2"  # Toutes les 2 heures

4. Exemples avancés :
   # Tous les lundis et jeudis à 8h
   crontab(hour=8, minute=0, day_of_week="1,4")

   # Tous les jours ouvrés à 9h
   crontab(hour=9, minute=0, day_of_week="1-5")

   # Toutes les 30 minutes
   crontab(minute="*/30")

Timezone :
- Configurée dans celery_app.conf.timezone (Africa/Douala)
- Toutes les heures sont en heure locale

Vérifier le schedule :
$ celery -A app.worker.tasks beat --loglevel=info
"""


# ==================== CONFIGURATION ALTERNATIVE (si besoin) ====================

# Si vous voulez différentes heures par fréquence :
# celery_schedule_custom = {
#     "weekly-reports-morning": {
#         "task": "app.worker.tasks.generate_scheduled_reports",
#         "schedule": crontab(hour=8, minute=0, day_of_week=1),
#         "args": ("weekly",),
#     },
#     "weekly-reports-afternoon": {
#         "task": "app.worker.tasks.generate_scheduled_reports",
#         "schedule": crontab(hour=14, minute=0, day_of_week=1),
#         "args": ("weekly",),
#     },
# }
