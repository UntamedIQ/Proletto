"""
Backward compatibility module for subscription models

This file ensures existing code that imports from models_subscription.py 
continues to work by re-exporting classes from db_models.py.
"""

# Re-export subscription-related models from db_models
from db_models import (
    Subscription, 
    Payment,
    db
)