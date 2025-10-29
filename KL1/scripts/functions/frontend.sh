#!/bin/bash

create_frontend() {
    log_info "Creating frontend application..."
    
    # Copy frontend files from src/frontend/
    if [ -f "./src/frontend/index.html" ]; then
        cp -r ./src/frontend/* "$FRONTEND_DIR/"
    else
        log_warning "Frontend files not found in src, using embedded version"
        create_embedded_frontend
    fi
    
    set_frontend_permissions
    log_success "Frontend application created"
}

create_embedded_frontend() {
    # Создаем основной HTML файл (сокращенная версия)
    cat > "$FRONTEND_DIR/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>KursLight VPN</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px;
            background: #2c3e50;
            color: white;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        .login-form { 
            background: #34495e; 
            padding: 20px; 
            border-radius: 5px;
            max-width: 400px;
            margin: 100px auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-form">
            <h2>KursLight VPN</h2>
            <form id="loginForm">
                <input type="text" placeholder="Username" required>
                <input type="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </div>
</body>
</html>
HTML
}

set_frontend_permissions() {
    chmod -R 755 "$FRONTEND_DIR"
    chown -R root:root "$FRONTEND_DIR"
}