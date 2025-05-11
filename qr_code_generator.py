"""
QR Code Generator Utility

This module provides functions for generating QR codes for various features
including referral links, art pieces, and marketing materials.
"""
import os
import requests
import logging
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

def generate_qr_code(data, size=200, format="png", save_path=None):
    """
    Generate a QR code using the qrserver.com API
    
    Args:
        data (str): The data to encode in the QR code (URL, text, etc.)
        size (int): Size of the QR code in pixels (square)
        format (str): Image format - png, svg, eps, etc.
        save_path (str, optional): If provided, save the QR code to this path
        
    Returns:
        bytes or str: QR code image data if save_path is None, otherwise the save path
    """
    base_url = "https://api.qrserver.com/v1/create-qr-code/"
    params = {
        "data": data,
        "size": f"{size}x{size}",
        "format": format
    }
    
    try:
        response = requests.get(base_url, params=params, stream=True)
        response.raise_for_status()
        
        if save_path:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return save_path
        else:
            return response.content
    
    except Exception as e:
        logger.error(f"QR code generation failed: {str(e)}")
        return None

def generate_referral_qr_code(referral_code, base_url, size=200, save_path=None):
    """
    Generate a QR code specifically for a referral link
    
    Args:
        referral_code (str): The user's referral code
        base_url (str): Base URL of the application
        size (int): Size of the QR code in pixels
        save_path (str, optional): If provided, save the QR code to this path
        
    Returns:
        bytes or str: QR code image data if save_path is None, otherwise the save path
    """
    # Construct the full referral URL
    referral_url = f"{base_url}/register?ref={referral_code}"
    return generate_qr_code(referral_url, size, "png", save_path)

def generate_art_qr_code(art_id, base_url, size=200, save_path=None):
    """
    Generate a QR code linking to an art piece
    
    Args:
        art_id (str): The art piece ID
        base_url (str): Base URL of the application
        size (int): Size of the QR code in pixels
        save_path (str, optional): If provided, save the QR code to this path
        
    Returns:
        bytes or str: QR code image data if save_path is None, otherwise the save path
    """
    # Construct the art URL
    art_url = f"{base_url}/art/{art_id}"
    return generate_qr_code(art_url, size, "png", save_path)

def generate_marketing_qr_code(campaign="beta", size=200, save_path=None):
    """
    Generate a QR code for marketing materials
    
    Args:
        campaign (str): Campaign identifier
        size (int): Size of the QR code in pixels
        save_path (str, optional): If provided, save the QR code to this path
        
    Returns:
        bytes or str: QR code image data if save_path is None, otherwise the save path
    """
    # Use environment variable or default to a standard domain
    base_url = os.environ.get('APP_BASE_URL', 'https://myproletto.com')
    marketing_url = f"{base_url}/upgrade?ref={campaign}"
    return generate_qr_code(marketing_url, size, "png", save_path)