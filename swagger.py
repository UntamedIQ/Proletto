"""
Proletto API - OpenAPI/Swagger Documentation

This module provides OpenAPI/Swagger documentation for the Proletto Public API.
It uses Flask-Swagger-UI to serve a Swagger UI interface for exploring and testing the API.
"""

import os
import json
from flask import Blueprint, jsonify, current_app
from flask_swagger_ui import get_swaggerui_blueprint

# Create a blueprint for the Swagger documentation
swagger_bp = Blueprint('swagger', __name__)

# Define the base URL for the Swagger documentation
SWAGGER_URL = '/api/docs'
API_URL = '/api/swagger.json'

# Create the Swagger UI blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Proletto API",
        'dom_id': '#swagger-ui',
        'layout': 'BaseLayout',
        'deepLinking': True,
        'validatorUrl': None,
        'displayRequestDuration': True,
        'docExpansion': 'list',
    }
)

@swagger_bp.route('/swagger.json')
def swagger_json():
    """
    Serve the Swagger JSON specification
    """
    # Build the OpenAPI specification as a Python dictionary
    swagger_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Proletto Public API",
            "description": "API for Proletto's artist opportunity platform",
            "version": "2.0.0",
            "contact": {
                "email": "support@myproletto.com"
            },
            "license": {
                "name": "Proprietary",
                "url": "https://www.myproletto.com/terms"
            }
        },
        "servers": [
            {
                "url": "https://api.myproletto.com",
                "description": "Production server"
            },
            {
                "url": "http://localhost:5001",
                "description": "Development server"
            }
        ],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "query",
                    "name": "key"
                },
                "ApiKeyHeader": {
                    "type": "apiKey",
                    "in": "header", 
                    "name": "X-API-KEY"
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "api_version": {
                            "type": "string",
                            "example": "v2"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2025-05-06T21:49:25.123456Z"
                        },
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {
                                    "type": "integer",
                                    "example": 400
                                },
                                "message": {
                                    "type": "string",
                                    "example": "Invalid parameter"
                                }
                            }
                        }
                    }
                },
                "HealthResponse": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["ok", "degraded", "maintenance"],
                            "example": "ok"
                        },
                        "api_version": {
                            "type": "string",
                            "example": "v2"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2025-05-06T21:49:25.123456Z"
                        },
                        "server_time": {
                            "type": "string",
                            "example": "2025-05-06 21:49:25 UTC"
                        }
                    }
                },
                "StatsResponse": {
                    "type": "object",
                    "properties": {
                        "api_version": {
                            "type": "string",
                            "example": "v2"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2025-05-06T21:49:25.123456Z"
                        },
                        "stats": {
                            "type": "object",
                            "properties": {
                                "user_count": {
                                    "type": "integer",
                                    "example": 3
                                },
                                "premium_users": {
                                    "type": "integer",
                                    "example": 2
                                },
                                "opportunity_count": {
                                    "type": "integer",
                                    "example": 2254
                                },
                                "scheduler_status": {
                                    "type": "string",
                                    "enum": ["running", "paused", "stopped", "not_initialized", "unknown"],
                                    "example": "running"
                                },
                                "environments": {
                                    "type": "object",
                                    "properties": {
                                        "web": {
                                            "type": "boolean",
                                            "example": True
                                        },
                                        "api": {
                                            "type": "boolean",
                                            "example": True
                                        },
                                        "scheduler": {
                                            "type": "boolean",
                                            "example": True
                                        },
                                        "database": {
                                            "type": "boolean",
                                            "example": True
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "Recommendation": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "example": "123"
                        },
                        "title": {
                            "type": "string",
                            "example": "Artist Residency Program"
                        },
                        "url": {
                            "type": "string",
                            "format": "uri",
                            "example": "https://example.com/opportunity/123"
                        },
                        "confidence": {
                            "type": "number",
                            "format": "float",
                            "minimum": 0,
                            "maximum": 1,
                            "example": 0.92
                        },
                        "category": {
                            "type": "string",
                            "example": "residency"
                        },
                        "deadline": {
                            "type": "string",
                            "format": "date",
                            "example": "2025-06-15"
                        }
                    }
                },
                "RecommendationsResponse": {
                    "type": "object",
                    "properties": {
                        "api_version": {
                            "type": "string",
                            "example": "v2"
                        },
                        "timestamp": {
                            "type": "string",
                            "format": "date-time",
                            "example": "2025-05-06T21:49:25.123456Z"
                        },
                        "recommendations": {
                            "type": "array",
                            "items": {
                                "$ref": "#/components/schemas/Recommendation"
                            }
                        },
                        "user_id": {
                            "type": "integer",
                            "example": 1
                        },
                        "count": {
                            "type": "integer",
                            "example": 10
                        },
                        "pagination": {
                            "type": "object",
                            "properties": {
                                "limit": {
                                    "type": "integer",
                                    "example": 10
                                },
                                "offset": {
                                    "type": "integer",
                                    "example": 0
                                },
                                "next_offset": {
                                    "type": ["integer", "null"],
                                    "example": 10
                                },
                                "has_more": {
                                    "type": "boolean",
                                    "example": True
                                }
                            }
                        }
                    }
                }
            }
        },
        "security": [
            {
                "ApiKeyAuth": []
            },
            {
                "ApiKeyHeader": []
            }
        ],
        "paths": {
            "/api/v2/health": {
                "get": {
                    "summary": "Get API health status",
                    "description": "Returns the current health status of the API",
                    "operationId": "getHealthStatus",
                    "tags": ["System"],
                    "parameters": [
                        {
                            "name": "key",
                            "in": "query",
                            "description": "API key",
                            "required": True,
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/HealthResponse"
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Invalid API key",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v2/stats": {
                "get": {
                    "summary": "Get API usage statistics",
                    "description": "Returns high-level API usage statistics",
                    "operationId": "getApiStats",
                    "tags": ["System"],
                    "parameters": [
                        {
                            "name": "key",
                            "in": "query",
                            "description": "API key",
                            "required": True,
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/StatsResponse"
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Invalid API key",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v2/recommendations": {
                "get": {
                    "summary": "Get personalized art opportunity recommendations",
                    "description": "Returns personalized art opportunity recommendations for a user",
                    "operationId": "getRecommendations",
                    "tags": ["Recommendations"],
                    "parameters": [
                        {
                            "name": "key",
                            "in": "query",
                            "description": "API key",
                            "required": True,
                            "schema": {
                                "type": "string"
                            }
                        },
                        {
                            "name": "user_id",
                            "in": "query",
                            "description": "ID of the user to get recommendations for",
                            "required": True,
                            "schema": {
                                "type": "integer"
                            }
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "Maximum number of recommendations to return",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10
                            }
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "description": "Number of recommendations to skip for pagination",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "minimum": 0,
                                "default": 0
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/RecommendationsResponse"
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Invalid parameters",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Invalid API key",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    return jsonify(swagger_spec)

def init_app(app):
    """
    Initialize the Swagger documentation blueprint
    """
    # Register the Swagger blueprint
    app.register_blueprint(swagger_bp, url_prefix='/api')
    
    # Register the Swagger UI blueprint
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    
    print(f"Swagger UI is available at {SWAGGER_URL}")
    print(f"Swagger JSON is available at /api{API_URL}")