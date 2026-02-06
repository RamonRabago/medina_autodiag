"""
Script para probar la conexión SMTP con las credenciales del .env.
Ejecutar desde la raíz del proyecto: python scripts/test_smtp.py

Uso:
  python scripts/test_smtp.py           # Solo prueba conexión y login
  python scripts/test_smtp.py --enviar  # Envía un correo de prueba al destinatario
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def main():
    from dotenv import load_dotenv
    load_dotenv()

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    print("=" * 50)
    print("Prueba de configuración SMTP")
    print("=" * 50)
    print(f"SMTP_HOST:        {host or '(no configurado)'}")
    print(f"SMTP_PORT:        {port}")
    print(f"SMTP_USER:        {user or '(no configurado)'}")
    print(f"SMTP_PASSWORD:    {'***' if password else '(no configurado)'}")
    print(f"SMTP_FROM_EMAIL:  {from_email or '(no configurado)'}")
    print(f"SMTP_USE_TLS:     {use_tls}")
    print()

    if not host or not user or not password:
        print("ERROR: Faltan SMTP_HOST, SMTP_USER o SMTP_PASSWORD en el .env")
        return 1

    print("Conectando al servidor SMTP...")
    try:
        import smtplib
        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                print("Iniciando TLS...")
                server.starttls()
            print("Autenticando...")
            server.login(user, password)
            print("OK: Autenticación exitosa.")
    except smtplib.SMTPAuthenticationError as e:
        print(f"ERROR DE AUTENTICACIÓN: {e}")
        print()
        print("Posibles causas:")
        print("  - Contraseña incorrecta")
        print("  - Si tienes 2FA: usa una 'Contraseña de aplicación' desde account.microsoft.com/security")
        print("  - SMTP AUTH deshabilitado para tu cuenta en Microsoft 365")
        return 1
    except smtplib.SMTPException as e:
        print(f"ERROR SMTP: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return 1

    # Enviar correo de prueba si se pide
    if "--enviar" in sys.argv:
        idx = sys.argv.index("--enviar")
        dest = sys.argv[idx + 1] if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-") else user
        print()
        print(f"Enviando correo de prueba a {dest}...")
        try:
            from email.mime.text import MIMEText
            msg = MIMEText("Este es un correo de prueba desde Medina AutoDiag.", "plain", "utf-8")
            msg["Subject"] = "Prueba SMTP - Medina AutoDiag"
            msg["From"] = from_email or user
            msg["To"] = dest
            with smtplib.SMTP(host, port, timeout=15) as server:
                if use_tls:
                    server.starttls()
                server.login(user, password)
                server.sendmail(from_email or user, [dest], msg.as_string())
            print("OK: Correo de prueba enviado correctamente.")
        except Exception as e:
            print(f"ERROR al enviar: {e}")
            return 1

    print()
    print("La configuración SMTP parece correcta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
