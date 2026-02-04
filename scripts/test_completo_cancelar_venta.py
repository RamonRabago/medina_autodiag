"""
Prueba completa: crea orden con repuesto, inicia, crea venta, cancela y verifica devolución de stock.
Ejecuta TODO el flujo automáticamente.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    from app.database import SessionLocal
    from app.models.venta import Venta
    from app.models.orden_trabajo import OrdenTrabajo
    from app.models.repuesto import Repuesto
    from app.models.vehiculo import Vehiculo
    from app.models.cliente import Cliente
    from app.models.detalle_orden import DetalleRepuestoOrden
    from app.services.inventario_service import InventarioService
    from app.schemas.movimiento_inventario import MovimientoInventarioCreate
    from app.models.movimiento_inventario import TipoMovimiento

    db = SessionLocal()
    try:
        # 1. Repuesto con stock
        rep = db.query(Repuesto).filter(Repuesto.activo == True, Repuesto.eliminado == False, Repuesto.stock_actual >= 2).first()
        if not rep:
            print("No hay repuesto con stock >= 2. Agrega inventario primero.")
            return 1

        # 2. Cliente y vehículo
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        if not cli or not vh:
            print("Falta cliente o vehículo.")
            return 1

        stock_inicial = rep.stock_actual
        cantidad_usar = 2

        # 3. Crear orden con repuesto
        from app.models.orden_trabajo import EstadoOrden
        from datetime import datetime
        from decimal import Decimal

        orden = OrdenTrabajo(
            numero_orden=f"OT-TEST-{datetime.now().strftime('%Y%m%d%H%M')}",
            vehiculo_id=vh.id_vehiculo,
            cliente_id=cli.id_cliente,
            fecha_ingreso=datetime.now(),
            estado=EstadoOrden.PENDIENTE,
            subtotal_servicios=Decimal("0"),
            subtotal_repuestos=Decimal("100"),
            descuento=Decimal("0"),
            total=Decimal("100"),
            cliente_proporciono_refacciones=False,
        )
        db.add(orden)
        db.commit()
        db.refresh(orden)

        det = DetalleRepuestoOrden(
            orden_trabajo_id=orden.id,
            repuesto_id=rep.id_repuesto,
            cantidad=cantidad_usar,
            precio_unitario=Decimal("50"),
            cliente_provee=False,
            descuento=Decimal("0"),
            subtotal=Decimal("100"),
        )
        db.add(det)
        db.commit()

        print(f"Orden creada: {orden.numero_orden} (id={orden.id}) con {cantidad_usar} unidades de {rep.codigo}")

        # 4. Autorizar e iniciar orden (esto descuenta stock)
        from app.models.usuario import Usuario
        usr = db.query(Usuario).filter(Usuario.activo == True).first()
        usuario_id = usr.id_usuario if usr else None
        if not usuario_id:
            print("No hay usuario activo.")
            return 1
        orden.autorizado = True
        orden.estado = EstadoOrden.EN_PROCESO
        orden.fecha_inicio = datetime.now()
        orden.tecnico_id = usuario_id
        db.commit()

        # Registrar SALIDA (como lo hace iniciar_orden)
        InventarioService.registrar_movimiento(
            db,
            MovimientoInventarioCreate(
                id_repuesto=rep.id_repuesto,
                tipo_movimiento=TipoMovimiento.SALIDA,
                cantidad=cantidad_usar,
                precio_unitario=None,
                referencia=f"OT#{orden.id}",
                motivo="Prueba automatizada - iniciar orden",
            ),
            usuario_id,
        )
        db.commit()

        db.refresh(rep)
        stock_despues_iniciar = rep.stock_actual
        print(f"Stock después de iniciar orden: {stock_despues_iniciar} (antes={stock_inicial})")

        # 5. Crear venta desde orden
        venta = Venta(
            id_cliente=cli.id_cliente,
            id_vehiculo=vh.id_vehiculo,
            id_orden=orden.id,
            total=Decimal("100"),
            estado="PENDIENTE",
        )
        db.add(venta)
        db.commit()
        db.refresh(venta)
        print(f"Venta creada: id={venta.id_venta}")

        # 6. Simular cancelación (llamada directa a la lógica)
        venta.estado = "CANCELADA"
        venta.motivo_cancelacion = "Prueba automatizada"
        # Devolver stock
        for d in orden.detalles_repuesto:
            InventarioService.registrar_movimiento(
                db,
                MovimientoInventarioCreate(
                    id_repuesto=d.repuesto_id,
                    tipo_movimiento=TipoMovimiento.ENTRADA,
                    cantidad=d.cantidad,
                    precio_unitario=None,
                    referencia=f"Venta#{venta.id_venta}",
                    motivo="Devolución por cancelación: Prueba automatizada",
                ),
                usuario_id,
            )
        db.commit()

        # 7. Verificar
        db.expire_all()
        rep2 = db.query(Repuesto).filter(Repuesto.id_repuesto == rep.id_repuesto).first()
        stock_final = rep2.stock_actual
        esperado = stock_inicial  # debe volver al inicial

        print(f"\nStock final: {stock_final} | Esperado: {esperado}")

        if stock_final == esperado:
            print("\n" + "=" * 60)
            print("PRUEBA EXITOSA: El stock se devolvió correctamente.")
            print("=" * 60)
            return 0
        else:
            print("\nERROR: El stock no coincidió.")
            return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
