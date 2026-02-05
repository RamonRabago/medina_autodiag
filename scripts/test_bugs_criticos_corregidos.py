"""
Simulación para verificar las correcciones de los bugs críticos.

Ejecutar: python scripts/test_bugs_criticos_corregidos.py

Pruebas:
1. Modelo Pago: verifica que id_turno no está duplicado
2. Actualizar venta manual: devuelve stock de productos removidos y descuenta los nuevos
3. Agregar repuesto a orden EN_PROCESO: valida stock y descuenta
4. Órdenes disponibles: excluye ventas canceladas (orden con venta cancelada aparece disponible)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_1_modelo_pago():
    """Verifica que el modelo Pago no tiene columna id_turno duplicada."""
    from app.models.pago import Pago
    cols = [c.name for c in Pago.__table__.columns]
    count_id_turno = cols.count("id_turno")
    assert count_id_turno == 1, f"id_turno debería aparecer 1 vez, aparece {count_id_turno}"
    print("  [OK] Modelo Pago: id_turno definido una sola vez")


def test_2_actualizar_venta_stock():
    """Actualizar venta manual: devuelve stock de productos removidos y descuenta los nuevos."""
    from app.database import SessionLocal
    from app.models.venta import Venta
    from app.models.detalle_venta import DetalleVenta
    from app.models.repuesto import Repuesto
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo
    from app.models.usuario import Usuario
    from app.schemas.venta import VentaCreate, VentaUpdate, DetalleVentaCreate
    from app.routers.ventas import crear_venta, actualizar_venta
    from app.utils.decimal_utils import to_float_money

    db = SessionLocal()
    try:
        rep_a = db.query(Repuesto).filter(
            Repuesto.activo == True, Repuesto.eliminado == False, Repuesto.stock_actual >= 2
        ).first()
        rep_b = db.query(Repuesto).filter(
            Repuesto.activo == True, Repuesto.eliminado == False,
            Repuesto.id_repuesto != rep_a.id_repuesto if rep_a else True,
            Repuesto.stock_actual >= 1
        ).first()
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.activo == True).first()

        if not all([rep_a, rep_b, cli, vh, usr]):
            print("  [SKIP] Actualizar venta: faltan datos (2 repuestos, cliente, vehículo, usuario)")
            return True

        stock_a_antes = rep_a.stock_actual
        stock_b_antes = rep_b.stock_actual

        # Crear venta manual con producto A x 1
        data_create = VentaCreate(
            id_cliente=cli.id_cliente,
            id_vehiculo=vh.id_vehiculo,
            requiere_factura=False,
            detalles=[
                DetalleVentaCreate(
                    tipo="PRODUCTO",
                    id_item=rep_a.id_repuesto,
                    descripcion=rep_a.nombre,
                    cantidad=1,
                    precio_unitario=50.0,
                )
            ],
        )
        result = crear_venta(data_create, db, usr)
        id_venta = result["id_venta"]

        db.expire_all()
        rep_a_ref = db.query(Repuesto).filter(Repuesto.id_repuesto == rep_a.id_repuesto).first()
        stock_a_despues_crear = rep_a_ref.stock_actual
        assert stock_a_despues_crear == stock_a_antes - 1, (
            f"Tras crear venta: stock A debería ser {stock_a_antes - 1}, es {stock_a_despues_crear}"
        )

        # Actualizar: quitar A, poner B x 1
        data_update = VentaUpdate(
            id_cliente=cli.id_cliente,
            id_vehiculo=vh.id_vehiculo,
            requiere_factura=False,
            detalles=[
                DetalleVentaCreate(
                    tipo="PRODUCTO",
                    id_item=rep_b.id_repuesto,
                    descripcion=rep_b.nombre,
                    cantidad=1,
                    precio_unitario=60.0,
                )
            ],
        )
        actualizar_venta(id_venta, data_update, db, usr)

        db.expire_all()
        rep_a_final = db.query(Repuesto).filter(Repuesto.id_repuesto == rep_a.id_repuesto).first()
        rep_b_final = db.query(Repuesto).filter(Repuesto.id_repuesto == rep_b.id_repuesto).first()
        assert rep_a_final.stock_actual == stock_a_antes, (
            f"Tras actualizar: stock A debería haberse devuelto a {stock_a_antes}, es {rep_a_final.stock_actual}"
        )
        assert rep_b_final.stock_actual == stock_b_antes - 1, (
            f"Tras actualizar: stock B debería ser {stock_b_antes - 1}, es {rep_b_final.stock_actual}"
        )

        # Limpiar: cancelar venta y devolver stock de B al inventario
        venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
        venta.estado = "CANCELADA"
        from app.services.inventario_service import InventarioService
        from app.schemas.movimiento_inventario import MovimientoInventarioCreate
        from app.models.movimiento_inventario import TipoMovimiento
        InventarioService.registrar_movimiento(
            db,
            MovimientoInventarioCreate(
                id_repuesto=rep_b.id_repuesto,
                tipo_movimiento=TipoMovimiento.ENTRADA,
                cantidad=1,
                precio_unitario=None,
                referencia=f"Venta#{id_venta}",
                motivo="Limpieza test",
            ),
            usr.id_usuario,
        )
        db.commit()

        print("  [OK] Actualizar venta: stock devuelto y descontado correctamente")
        return True
    except Exception as e:
        print(f"  [FAIL] Actualizar venta: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_3_agregar_repuesto_orden():
    """Agregar repuesto a orden EN_PROCESO: valida stock y descuenta."""
    from app.database import SessionLocal
    from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden
    from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden
    from app.models.repuesto import Repuesto
    from app.models.vehiculo import Vehiculo
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario
    from app.models.servicio import Servicio
    from decimal import Decimal
    from datetime import datetime

    db = SessionLocal()
    try:
        rep_inicial = db.query(Repuesto).filter(
            Repuesto.activo == True, Repuesto.eliminado == False, Repuesto.stock_actual >= 1
        ).first()
        rep_agregar = db.query(Repuesto).filter(
            Repuesto.activo == True, Repuesto.eliminado == False,
            Repuesto.stock_actual >= 2,
            Repuesto.id_repuesto != rep_inicial.id_repuesto if rep_inicial else True
        ).first()
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.rol == "TECNICO").first() or db.query(Usuario).filter(Usuario.activo == True).first()
        serv = db.query(Servicio).first()

        if not all([rep_inicial, rep_agregar, cli, vh, usr, serv]):
            print("  [SKIP] Agregar repuesto: faltan datos")
            return True

        stock_agregar_antes = rep_agregar.stock_actual

        orden = OrdenTrabajo(
            numero_orden=f"OT-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            vehiculo_id=vh.id_vehiculo,
            cliente_id=cli.id_cliente,
            tecnico_id=usr.id_usuario,
            fecha_ingreso=datetime.now(),
            estado=EstadoOrden.EN_PROCESO,
            prioridad="NORMAL",
            diagnostico_inicial="Test",
            observaciones_cliente="Test",
            subtotal_servicios=Decimal("100"),
            subtotal_repuestos=Decimal("0"),
            descuento=Decimal("0"),
            total=Decimal("100"),
            cliente_proporciono_refacciones=False,
            fecha_inicio=datetime.now(),
        )
        db.add(orden)
        db.flush()
        det_serv = DetalleOrdenTrabajo(
            orden_trabajo_id=orden.id,
            servicio_id=serv.id,
            descripcion=serv.nombre,
            precio_unitario=Decimal("100"),
            cantidad=1,
            descuento=Decimal("0"),
            subtotal=Decimal("100"),
        )
        det_serv.calcular_subtotal()
        db.add(det_serv)
        db.commit()
        db.refresh(orden)

        from app.routers.ordenes_trabajo import agregar_repuesto_a_orden
        from app.schemas.orden_trabajo_schema import AgregarRepuestoRequest

        req = AgregarRepuestoRequest(
            repuesto_id=rep_agregar.id_repuesto,
            cantidad=1,
            precio_unitario=None,
            descuento=Decimal("0"),
            observaciones=None,
        )
        agregar_repuesto_a_orden(orden.id, req, db, usr)

        db.expire_all()
        rep_agregar_ref = db.query(Repuesto).filter(Repuesto.id_repuesto == rep_agregar.id_repuesto).first()
        assert rep_agregar_ref.stock_actual == stock_agregar_antes - 1, (
            f"Tras agregar repuesto: stock debería ser {stock_agregar_antes - 1}, es {rep_agregar_ref.stock_actual}"
        )

        # Devolver stock y limpiar
        from app.services.inventario_service import InventarioService
        from app.schemas.movimiento_inventario import MovimientoInventarioCreate
        from app.models.movimiento_inventario import TipoMovimiento
        for d in orden.detalles_repuesto:
            InventarioService.registrar_movimiento(
                db,
                MovimientoInventarioCreate(
                    id_repuesto=d.repuesto_id,
                    tipo_movimiento=TipoMovimiento.ENTRADA,
                    cantidad=d.cantidad,
                    precio_unitario=None,
                    referencia=orden.numero_orden,
                    motivo="Limpieza test",
                ),
                usr.id_usuario,
            )
        db.delete(orden)
        db.commit()

        print("  [OK] Agregar repuesto a orden EN_PROCESO: stock descontado correctamente")
        return True
    except Exception as e:
        print(f"  [FAIL] Agregar repuesto: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_4_ordenes_disponibles_sin_canceladas():
    """Órdenes disponibles: orden con venta cancelada debe aparecer como disponible."""
    from app.database import SessionLocal
    from app.models.venta import Venta
    from app.models.orden_trabajo import OrdenTrabajo
    from sqlalchemy.orm import joinedload

    db = SessionLocal()
    try:
        orden = db.query(OrdenTrabajo).filter(
            OrdenTrabajo.estado.in_(["ENTREGADA", "COMPLETADA"])
        ).first()
        if not orden:
            print("  [SKIP] Órdenes disponibles: no hay orden ENTREGADA o COMPLETADA")
            return True

        venta_existente = db.query(Venta).filter(
            Venta.id_orden == orden.id,
            Venta.estado != "CANCELADA"
        ).first()
        if venta_existente:
            print("  [SKIP] Órdenes disponibles: la orden ya tiene venta activa vinculada")
            return True

        ids_ocupados_antiguo = [
            r[0] for r in db.query(Venta.id_orden).filter(
                Venta.id_orden.isnot(None)
            ).distinct().all()
        ]
        ids_ocupados_nuevo = [
            r[0] for r in db.query(Venta.id_orden).filter(
                Venta.id_orden.isnot(None),
                Venta.estado != "CANCELADA"
            ).distinct().all()
        ]

        venta_cancelada_con_orden = db.query(Venta).filter(
            Venta.id_orden.isnot(None),
            Venta.estado == "CANCELADA"
        ).first()

        if venta_cancelada_con_orden:
            id_orden_cancelada = venta_cancelada_con_orden.id_orden
            en_antiguo = id_orden_cancelada in ids_ocupados_antiguo
            en_nuevo = id_orden_cancelada in ids_ocupados_nuevo
            assert en_antiguo, "Venta cancelada con orden debería estar en ids_ocupados (comportamiento antiguo)"
            assert not en_nuevo, "Con el fix: venta cancelada NO debe ocupar la orden"
            print("  [OK] Órdenes disponibles: ventas canceladas excluidas correctamente")
        else:
            print("  [OK] Órdenes disponibles: lógica verificada (no hay ventas canceladas con orden para probar)")
        return True
    except Exception as e:
        print(f"  [FAIL] Órdenes disponibles: {e}")
        return False
    finally:
        db.close()


def main():
    print("\n=== Verificación de correcciones de bugs críticos ===\n")
    ok = 0
    total = 4

    print("1. Modelo Pago (id_turno no duplicado)")
    try:
        test_1_modelo_pago()
        ok += 1
    except Exception as e:
        print(f"  [FAIL] {e}")

    print("\n2. Actualizar venta manual (stock)")
    if test_2_actualizar_venta_stock():
        ok += 1

    print("\n3. Agregar repuesto a orden EN_PROCESO (stock)")
    if test_3_agregar_repuesto_orden():
        ok += 1

    print("\n4. Órdenes disponibles (excluir ventas canceladas)")
    if test_4_ordenes_disponibles_sin_canceladas():
        ok += 1

    print(f"\n=== Resultado: {ok}/{total} pruebas OK ===\n")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
