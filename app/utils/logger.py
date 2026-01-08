# app/utils/logger.py
"""
Configuration du logging structuré pour l'application.

Supporte les formats JSON (production) et texte (développement).
"""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict
from pythonjsonlogger import jsonlogger

from app.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Formatter JSON personnalisé avec champs supplémentaires"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Ajoute des champs personnalisés au log JSON"""
        super().add_fields(log_record, record, message_dict)
        
        # Timestamp ISO 8601
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat() + 'Z'
        
        # Environnement
        log_record['environment'] = settings.ENVIRONMENT
        
        # Niveau de log
        log_record['level'] = record.levelname
        
        # Module source
        log_record['module'] = record.module
        
        # Fonction source
        log_record['function'] = record.funcName
        
        # Ligne source
        log_record['line'] = record.lineno


def setup_logging() -> logging.Logger:
    """
    Configure le système de logging de l'application.
    
    Returns:
        Logger racine configuré
    """
    
    # Logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Supprimer les handlers existants
    root_logger.handlers.clear()
    
    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Format selon configuration
    if settings.LOG_FORMAT == "json":
        formatter = CustomJsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Réduire le bruit des librairies tierces
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtient un logger pour un module spécifique.
    
    Args:
        name: Nom du module (généralement __name__)
    
    Returns:
        Logger configuré
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Hello", extra={"user_id": "123"})
    """
    return logging.getLogger(name)


# Utilitaires pour logging contextuel
class LogContext:
    """Context manager pour ajouter du contexte aux logs"""
    
    def __init__(self, logger: logging.Logger, **context: Any):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


# Initialiser le logging au démarrage du module
setup_logging()