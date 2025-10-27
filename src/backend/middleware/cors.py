from flask import request, jsonify

def setup_cors(app):
    """Настройка CORS для фронтенда"""
    
    @app.after_request
    def after_request(response):
        # Разрешить запросы с любого origin (в разработке)
        # В продакшене заменить на конкретный домен
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Key')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = jsonify({"status": "preflight"})
            response.status_code = 200
            return response