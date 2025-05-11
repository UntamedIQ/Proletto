from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import uuid

art_bp = Blueprint('art', __name__)

# Temporary in-memory store (swap for DB later)
art_pieces = {}

@art_bp.route('/art', methods=['POST'])
@jwt_required()
def add_art():
    user_id = get_jwt_identity()
    data = request.get_json()
    art_id = str(uuid.uuid4())
    art_pieces[art_id] = {
        "id": art_id,
        "user_id": user_id,
        "title": data["title"],
        "year": data["year"],
        "medium": data["medium"],
        "image_url": data.get("image_url"),
        "status": "available",
        "notes": data.get("notes")
    }
    return jsonify(art_pieces[art_id]), 201

@art_bp.route('/art', methods=['GET'])
@jwt_required()
def list_art():
    user_id = get_jwt_identity()
    user_art = [art for art in art_pieces.values() if art["user_id"] == user_id]
    return jsonify(user_art), 200