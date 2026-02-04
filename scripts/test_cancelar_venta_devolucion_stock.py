"""
Script de prueba: Cancelar venta y verificar devolución de stock.
Ejecuta login, busca venta con orden, anota stock, cancela, verifica stock.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

# Configuración
BASE_URL = os.getenv("API_URL", "http://localhost:8000")


def get_db_session():
    from app.database import SessionLocal
    return SessionLocal()


def main():
    print("=" * 60)
    print("PRUEBA: Devolución de stock al cancelar venta")
    print("=" * 60)

    db = get_db_session()
    try:
        from app.models.venta import Venta
        from app.models.orden_trabajo import OrdenTrabajo
        from app.models.repuesto import Repuesto
        from app.models.usuario import Usuario

        # 1. Usuario ADMIN/CAJA para login
        usuario = db.query(Usuario).filter(
            Usuario.activo == True,
            Usuario.rol.in_(["ADMIN", "CAJA"])
        ).first()
        if not usuario:
            print("ERROR: No hay usuario ADMIN o CAJA activo. Crea uno primero.")
            return 1

        # 2. Buscar venta PAGADA o PENDIENTE con id_orden (creada desde orden)
        venta = db.query(Venta).filter(
            Venta.id_orden.isnot(None),
            Venta.estado.in_(["PAGADA", "PENDIENTE"])
        ).first()

        if not venta:
            print("No hay venta con orden asociada (PAGADA/PENDIENTE) para probar.")
            print("Crea una orden con repuestos, iníciala, crea la venta desde la orden y vuelve a ejecutar.")
            return 1

        orden = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == venta.id_orden).first()
        if not orden:
            print("ERROR: Orden no encontrada.")
            return 1

        if getattr(orden, "cliente_proporciono_refacciones", False):
            print("La orden tiene 'cliente proporcionó refacciones'. No se descontó stock, nada que devolver.")
            print("Usa una venta de orden donde el taller proporcionó los repuestos.")
            return 1

        detalles = orden.detalles_repuesto or []
        if not detalles:
            print("La orden no tiene repuestos. No hay stock que devolver.")
            return 1

        # 3. Stock antes por repuesto
        stocks_antes = {}
        for d in detalles:
            r = db.query(Repuesto).filter(Repuesto.id_repuesto == d.repuesto_id).first()
            if r:
                stocks_antes[d.repuesto_id] = {
                    "codigo": r.codigo,
                    "nombre": r.nombre,
                    "stock": r.stock_actual,
                    "cantidad_orden": d.cantidad
                }

        print(f"\nVenta ID: {venta.id_venta} | Orden ID: {venta.id_orden}")
        print("Stock ANTES de cancelar:")
        for rid, info in stocks_antes.items():
            print(f"  - {info['codigo']} ({info['nombre']}): stock={info['stock']}, en orden={info['cantidad_orden']}")

        # 4. Login (necesitamos contraseña - el script no la tiene; usaremos API si hay env)
        # Intentar login con credenciales por defecto comunes
        pwd = os.getenv("TEST_USER_PASSWORD", "admin123")  # Ajusta si tu usuario usa otra
        login_data = {"username": usuario.email, "password": pwd}
        try:
            r_login = requests.post(f"{BASE_URL}/auth/login", data=login_data, timeout=10)
        except requests.exceptions.ConnectionError:
            print("\nERROR: No se pudo conectar al API. ¿Está corriendo uvicorn en puerto 8000?")
            return 1

        if r_login.status_code != 200:
            print(f"\nERROR: Login falló ({r_login.status_code}).")
            print("Para que el script haga login automático, define TEST_USER_PASSWORD en .env")
            print("O ejecuta manualmente: POST /auth/login con email y contraseña del admin.")
            print("Luego cancela la venta desde el frontend y verifica el inventario.")
            return 1

        token = r_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 5. Cancelar venta
        motivo = "Prueba automatizada: devolución de stock"
        r_cancel = requests.post(
            f"{BASE_URL}/ventas/{venta.id_venta}/cancelar",
            json={"motivo": motivo},
            headers=headers,
            timeout=10
        )

        if r_cancel.status_code != 200:
            print(f"\nERROR: Cancelar venta falló ({r_cancel.status_code}): {r_cancel.text}")
            return 1

        print("\n✓ Venta cancelada correctamente.")

        # 6. Refrescar datos y verificar stock
        db.expire_all()  # invalidar cache
        ok = True
        print("\nStock DESPUÉS de cancelar:")
        for rid, info in stocks_antes.items():
            r = db.query(Repuesto).filter(Repuesto.id_repuesto == rid).first()
            nuevo_stock = r.stock_actual if r else 0
            esperado = info["stock"] + info["cantidad_orden"]
            coincide = nuevo_stock == esperado
            ok = ok and coincide
            symbol = "✓" if coincide else "✗"
            print(f"  {symbol} {info['codigo']}: antes={info['stock']} → después={nuevo_stock} (esperado={esperado})")

        if ok:
            print("\n" + "=" * 60)
            print("RESULTADO: Prueba exitosa. El stock se devolvió correctamente.")
            print("=" * 60)
            return 0
        else:
            print("\nRESULTADO: ERROR. El stock no coincidió con lo esperado.")
            return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
