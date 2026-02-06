"""
Script para probar el envío de correo vía Microsoft Graph API.
Ejecutar: python scripts/test_graph_email.py [email_destino]

Requiere AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SEND_AS_EMAIL en .env
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    from dotenv import load_dotenv
    load_dotenv()

    tenant = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    send_as = os.getenv("AZURE_SEND_AS_EMAIL")
    dest = sys.argv[1] if len(sys.argv) > 1 else send_as

    print("=" * 50)
    print("Prueba Microsoft Graph API - Envío de correo")
    print("=" * 50)
    print(f"AZURE_TENANT_ID:      {tenant or '(no configurado)'}")
    print(f"AZURE_CLIENT_ID:      {client_id or '(no configurado)'}")
    print(f"AZURE_CLIENT_SECRET:  {'***' if client_secret else '(no configurado)'}")
    print(f"AZURE_SEND_AS_EMAIL:  {send_as or '(no configurado)'}")
    print(f"Enviar a:             {dest}")
    print()

    if not all([tenant, client_id, client_secret, send_as]):
        print("ERROR: Configura AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SEND_AS_EMAIL en .env")
        print("Ver GUIA_GRAPH_API_EMAIL.md para los pasos.")
        return 1

    from app.services.email_service import enviar_orden_compra_a_proveedor

    ok, err = enviar_orden_compra_a_proveedor(
        email_destino=dest,
        nombre_proveedor="Proveedor de prueba",
        numero_orden="PRUEBA-001",
        lineas=[{"nombre_repuesto": "Producto prueba", "cantidad_solicitada": 1}],
        observaciones="Correo de prueba desde Medina AutoDiag.",
        vehiculo_info="Ford Edge 2016",
    )

    if ok:
        print("OK: Correo enviado correctamente vía Microsoft Graph.")
        return 0
    else:
        print(f"ERROR: {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
