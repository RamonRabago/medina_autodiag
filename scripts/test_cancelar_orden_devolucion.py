"""
Prueba: cancelar orden con devolución de repuestos usa CPP (precio_compra).
Valida que InventarioService.registrar_movimiento se usa correctamente.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from app.database import SessionLocal
    from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden
    from app.models.detalle_orden import DetalleRepuestoOrden
    from app.models.repuesto import Repuesto
    from app.models.vehiculo import Vehiculo
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario
    from app.services.inventario_service import InventarioService
    from app.schemas.movimiento_inventario import MovimientoInventarioCreate
    from app.models.movimiento_inventario import TipoMovimiento
    from datetime import datetime
    from decimal import Decimal

    db = SessionLocal()
    try:
        # Datos base
        rep = db.query(Repuesto).filter(
            Repuesto.activo == True, Repuesto.eliminado == False, Repuesto.stock_actual >= 2
        ).first()
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.activo == True).first()
        if not all([rep, cli, vh, usr]):
            print("Faltan datos (repuesto, cliente, vehículo, usuario)")
            return 1

        stock_inicial = rep.stock_actual
        cantidad = 2
        precio_compra = float(rep.precio_compra or 100)
        precio_venta_orden = 150.0  # precio en la orden (mayor que CPP)

        # 1. Crear orden con repuesto
        orden = OrdenTrabajo(
            numero_orden=f"OT-TEST-CANC-{datetime.now().strftime('%Y%m%d%H%M')}",
            vehiculo_id=vh.id_vehiculo,
            cliente_id=cli.id_cliente,
            tecnico_id=usr.id_usuario,
            fecha_ingreso=datetime.now(),
            estado=EstadoOrden.PENDIENTE,
            subtotal_servicios=Decimal("0"),
            subtotal_repuestos=Decimal(str(precio_venta_orden * cantidad)),
            descuento=Decimal("0"),
            total=Decimal(str(precio_venta_orden * cantidad)),
            cliente_proporciono_refacciones=False,
        )
        db.add(orden)
        db.commit()
        db.refresh(orden)

        det = DetalleRepuestoOrden(
            orden_trabajo_id=orden.id,
            repuesto_id=rep.id_repuesto,
            cantidad=cantidad,
            precio_unitario=Decimal(str(precio_venta_orden)),
            cliente_provee=False,
            descuento=Decimal("0"),
            subtotal=Decimal(str(precio_venta_orden * cantidad)),
        )
        db.add(det)
        db.commit()

        # 2. Autorizar e iniciar (descuenta stock con CPP)
        orden.autorizado = True
        orden.estado = EstadoOrden.EN_PROCESO
        orden.fecha_inicio = datetime.now()
        db.commit()

        InventarioService.registrar_movimiento(
            db,
            MovimientoInventarioCreate(
                id_repuesto=rep.id_repuesto,
                tipo_movimiento=TipoMovimiento.SALIDA,
                cantidad=cantidad,
                precio_unitario=None,
                referencia=orden.numero_orden,
                motivo="Prueba - iniciar orden",
            ),
            usr.id_usuario,
        )

        db.expire_all()
        r1 = db.query(Repuesto).filter(Repuesto.id_repuesto == rep.id_repuesto).first()
        stock_despues_iniciar = r1.stock_actual
        assert stock_despues_iniciar == stock_inicial - cantidad, (
            f"Stock después de iniciar: esperado {stock_inicial - cantidad}, actual {stock_despues_iniciar}"
        )

        # 3. Cancelar orden con devolución (ahora usa InventarioService con CPP)
        from app.routers.ordenes_trabajo import cancelar_orden_trabajo
        from unittest.mock import MagicMock

        # Simular request: llamar lógica sin HTTP
        orden_cancelada = cancelar_orden_trabajo(
            orden_id=orden.id,
            motivo="Prueba automatizada - validar devolución con CPP",
            devolver_repuestos=True,
            db=db,
            current_user=usr,
        )

        db.expire_all()
        r2 = db.query(Repuesto).filter(Repuesto.id_repuesto == rep.id_repuesto).first()
        stock_final = r2.stock_actual
        assert stock_final == stock_inicial, (
            f"Stock final: esperado {stock_inicial}, actual {stock_final}"
        )

        # Verificar que el movimiento de devolución usó CPP (no precio_venta)
        from app.models.movimiento_inventario import MovimientoInventario
        movs = db.query(MovimientoInventario).filter(
            MovimientoInventario.id_repuesto == rep.id_repuesto,
            MovimientoInventario.tipo_movimiento == "ENTRADA",
            MovimientoInventario.referencia == orden.numero_orden,
        ).order_by(MovimientoInventario.id_movimiento.desc()).limit(1).all()
        if movs:
            m = movs[0]
            # precio_unitario en ENTRADA de devolución debe ser ~precio_compra, no precio_venta
            pu = float(m.precio_unitario or 0)
            assert abs(pu - precio_compra) < 1, (
                f"Devolución debería usar CPP (~{precio_compra}), usó {pu}"
            )

        print("OK: Cancelar orden con devolución usa CPP correctamente.")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
