"""
Token Blocklist Module

This module manages JWT token revocation and blocklisting.
It helps invalidate tokens when users log out or when tokens need
to be revoked for security reasons.
"""
from datetime import datetime

# Import db as a global variable, but initialize it later
db = None

def init_db(app_db):
    """Initialize this module with the application's database instance."""
    global db
    db = app_db


# This class will be defined when the DB is initialized
TokenBlocklist = None

def define_token_blocklist():
    """Define the TokenBlocklist model class after db is initialized."""
    global TokenBlocklist
    
    if db is None:
        raise ValueError("Database must be initialized before defining TokenBlocklist model")
    
    class _TokenBlocklist(db.Model):
        """
        TokenBlocklist model for storing revoked tokens.
        Stores the JTI (JWT ID) of revoked tokens along with revocation timestamp.
        """
        __tablename__ = 'token_blocklist'
        __table_args__ = {'extend_existing': True}
        
        id = db.Column(db.Integer, primary_key=True)
        jti = db.Column(db.String(36), nullable=False, index=True)
        type = db.Column(db.String(16), nullable=False)  # 'access' or 'refresh'
        user_id = db.Column(db.Integer, nullable=True)  # Store user ID without foreign key constraint for now
        created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
        revoked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
        expires_at = db.Column(db.DateTime, nullable=False)
        
        def __repr__(self):
            return f'<TokenBlocklist {self.jti} (revoked at {self.revoked_at})>'
    
    TokenBlocklist = _TokenBlocklist
    return TokenBlocklist


def is_token_revoked(jwt_payload):
    """
    Check if a token has been revoked.
    
    Args:
        jwt_payload (dict): The decoded JWT payload
        
    Returns:
        bool: True if the token is revoked, False otherwise
    """
    jti = jwt_payload.get('jti')
    if not jti:
        return True  # Tokens without JTI are considered revoked
        
    token_type = 'refresh' if jwt_payload.get('type') == 'refresh' else 'access'
    token = TokenBlocklist.query.filter_by(jti=jti, type=token_type).first()
    return token is not None


def add_token_to_blocklist(jwt_payload, user_id=None, token_type=None):
    """
    Add a token to the blocklist (revoke it).
    
    Args:
        jwt_payload (dict): The decoded JWT payload
        user_id (int, optional): The ID of the user who owned the token
        token_type (str, optional): The type of token ('access' or 'refresh')
        
    Returns:
        TokenBlocklist: The created blocklist entry
    """
    jti = jwt_payload.get('jti')
    user_id = user_id or jwt_payload.get('sub')
    
    # If token_type isn't specified, try to determine from payload
    if not token_type:
        token_type = 'refresh' if jwt_payload.get('type') == 'refresh' else 'access'
    
    # Calculate token expiry
    expires_at = datetime.fromtimestamp(jwt_payload.get('exp', 0))
    
    # Create blocklist entry
    token = TokenBlocklist(
        jti=jti,
        type=token_type,
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.session.add(token)
    db.session.commit()
    
    return token


def prune_blocklist():
    """
    Remove expired tokens from the blocklist.
    This should be called periodically to keep the blocklist size manageable.
    
    Returns:
        int: Number of tokens removed
    """
    now = datetime.utcnow()
    expired_tokens = TokenBlocklist.query.filter(TokenBlocklist.expires_at < now).all()
    count = len(expired_tokens)
    
    for token in expired_tokens:
        db.session.delete(token)
    
    db.session.commit()
    return count