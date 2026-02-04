"""
Prueba: venta manual descuenta stock y la cancelación lo devuelve.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    from app.database import SessionLocal
    from app.models.venta import Venta
    from app.models.detalle_venta import DetalleVenta
    from app.models.repuesto import Repuesto
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo
    from app.models.usuario import Usuario

    db = SessionLocal()
    try:
        rep = db.query(Repuesto).filter(Repuesto.activo == True, Repuesto.eliminado == False, Repuesto.stock_actual >= 2).first()
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.activo == True).first()
        if not all([rep, cli, vh, usr]):
            print("Faltan datos (repuesto, cliente, vehículo, usuario)")
            return 1

        stock_antes = rep.stock_actual
        cantidad = 1

        # Crear venta manual vía lógica (simulando API)
        from decimal import Decimal
        venta = Venta(id_cliente=cli.id_cliente, id_vehiculo=vh.id_vehiculo, id_usuario=usr.id_usuario, total=50.0)
        db.add(venta)
        db.commit()
        db.refresh(venta)

        det = DetalleVenta(id_venta=venta.id_venta, tipo="PRODUCTO", id_item=rep.id_repuesto, descripcion=rep.nombre, cantidad=cantidad, precio_unitario=50, subtotal=50)
        db.add(det)
        db.flush()

        from app.services.inventario_service import InventarioService
        from app.schemas.movimiento_inventario import MovimientoInventarioCreate
        from app.models.movimiento_inventario import TipoMovimiento

        InventarioService.registrar_movimiento(db, MovimientoInventarioCreate(
            id_repuesto=rep.id_repuesto, tipo_movimiento=TipoMovimiento.SALIDA, cantidad=cantidad,
            precio_unitario=None, referencia=f"Venta#{venta.id_venta}", motivo="Venta manual"
        ), usr.id_usuario)

        db.expire_all()
        r2 = db.query(Repuesto).filter(Repuesto.id_repuesto == rep.id_repuesto).first()
        stock_despues_venta = r2.stock_actual
        assert stock_despues_venta == stock_antes - cantidad, f"Stock debería ser {stock_antes - cantidad}, es {stock_despues_venta}"

        # Devolver al cancelar
        InventarioService.registrar_movimiento(db, MovimientoInventarioCreate(
            id_repuesto=rep.id_repuesto, tipo_movimiento=TipoMovimiento.ENTRADA, cantidad=cantidad,
            precio_unitario=None, referencia=f"Venta#{venta.id_venta}", motivo="Devolución cancelación"
        ), usr.id_usuario)

        venta.estado = "CANCELADA"
        db.commit()

        db.expire_all()
        r3 = db.query(Repuesto).filter(Repuesto.id_repuesto == rep.id_repuesto).first()
        stock_final = r3.stock_actual
        assert stock_final == stock_antes, f"Stock final debería ser {stock_antes}, es {stock_final}"

        print("OK: Venta manual descuenta stock y la cancelación lo devuelve.")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
