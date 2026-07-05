# templates.py

def get_auth_success_html() -> str:
    return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autenticación Exitosa - Student Clustering API</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #7c3aed;
            --primary-hover: #6d28d9;
            --success: #10b981;
            --bg-start: #0a0518;
            --bg-end: #05020c;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background: radial-gradient(circle at 50% 50%, #1c0e3a 0%, var(--bg-start) 60%, var(--bg-end) 100%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            position: relative;
        }

        /* Ambient Glow Effects */
        body::before {
            content: '';
            position: absolute;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, transparent 70%);
            top: -100px;
            left: -100px;
            z-index: 0;
            pointer-events: none;
        }

        body::after {
            content: '';
            position: absolute;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(16, 185, 129, 0.1) 0%, transparent 70%);
            bottom: -150px;
            right: -150px;
            z-index: 0;
            pointer-events: none;
        }

        .container {
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 450px;
            padding: 24px;
        }

        .card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 24px;
            padding: 40px 32px;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .icon-container {
            width: 80px;
            height: 80px;
            background: radial-gradient(circle, rgba(16, 185, 129, 0.2) 0%, rgba(16, 185, 129, 0.05) 100%);
            border: 2px solid rgba(16, 185, 129, 0.4);
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto 28px;
            position: relative;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
            }
            70% {
                box-shadow: 0 0 0 15px rgba(16, 185, 129, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
            }
        }

        .icon-container svg {
            width: 38px;
            height: 38px;
            color: var(--success);
        }

        h1 {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #ffffff 40%, #c084fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }

        p {
            font-size: 16px;
            color: var(--text-muted);
            line-height: 1.6;
            margin-bottom: 32px;
            font-weight: 300;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 16px 24px;
            background: linear-gradient(135deg, var(--primary) 0%, #a855f7 100%);
            border: none;
            border-radius: 14px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            box-shadow: 0 4px 20px rgba(124, 58, 237, 0.3);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(124, 58, 237, 0.5);
            background: linear-gradient(135deg, var(--primary-hover) 0%, #9333ea 100%);
        }

        .btn:active {
            transform: translateY(1px);
        }

        .btn svg {
            margin-left: 8px;
            transition: transform 0.3s ease;
        }

        .btn:hover svg {
            transform: translateX(4px);
        }

        .footer {
            margin-top: 24px;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.2);
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="icon-container">
                <!-- Checkmark SVG -->
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path>
                </svg>
            </div>
            <h1>¡Autenticado con éxito!</h1>
            <p>Tu cuenta ha sido vinculada correctamente. Ya puedes cerrar esta ventana o continuar a la documentación interactiva de la API para explorar los servicios.</p>
            <a href="http://localhost:8000/docs" class="btn">
                Ir a la Documentación
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path>
                </svg>
            </a>
        </div>
        <div class="footer">
            Student Clustering API • v1.0.0
        </div>
    </div>
</body>
</html>"""
