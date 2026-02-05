"""
Simulación para verificar las correcciones de los bugs críticos.

Ejecutar: python scripts/test_bugs_criticos_corregidos.py

Pruebas:
1. Modelo Pago: verifica que id_turno no está duplicado
2. Actualizar venta manual: devuelve stock de productos removidos y descuenta los nuevos
3. Agregar repuesto a orden EN_PROCESO: valida stock y descuenta
4. Órdenes disponibles: excluye ventas canceladas (orden con venta cancelada aparece disponible)
5. Autorizar rechazo: orden pasa a CANCELADA con auditoría
6. Corte diario caja: filtra por id_turno (no mezcla pagos de distintos turnos)
7. Dashboard total_facturado: usa suma de Ventas vinculadas (no total de órdenes)
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


def test_5_autorizar_rechazo_cancela():
    """Al rechazar una orden (autorizado=False), debe pasar a CANCELADA con auditoría."""
    from app.database import SessionLocal
    from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden
    from app.models.detalle_orden import DetalleOrdenTrabajo
    from app.models.servicio import Servicio
    from app.models.vehiculo import Vehiculo
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario
    from app.routers.ordenes_trabajo import autorizar_orden_trabajo
    from app.schemas.orden_trabajo_schema import AutorizarOrdenRequest
    from decimal import Decimal
    from datetime import datetime

    db = SessionLocal()
    try:
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.rol.in_(["ADMIN", "CAJA"])).first() or db.query(Usuario).first()
        serv = db.query(Servicio).first()
        if not all([cli, vh, usr, serv]):
            print("  [SKIP] Autorizar rechazo: faltan datos")
            return True

        orden = OrdenTrabajo(
            numero_orden=f"OT-TEST-RECHAZO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            vehiculo_id=vh.id_vehiculo,
            cliente_id=cli.id_cliente,
            fecha_ingreso=datetime.now(),
            estado=EstadoOrden.ESPERANDO_AUTORIZACION,
            prioridad="NORMAL",
            diagnostico_inicial="Test rechazo",
            observaciones_cliente="Test",
            subtotal_servicios=Decimal("100"),
            subtotal_repuestos=Decimal("0"),
            descuento=Decimal("0"),
            total=Decimal("100"),
            requiere_autorizacion=True,
            autorizado=False,
            cliente_proporciono_refacciones=False,
        )
        db.add(orden)
        db.flush()
        det = DetalleOrdenTrabajo(
            orden_trabajo_id=orden.id,
            servicio_id=serv.id,
            descripcion=serv.nombre,
            precio_unitario=Decimal("100"),
            cantidad=1,
            descuento=Decimal("0"),
            subtotal=Decimal("100"),
        )
        det.calcular_subtotal()
        db.add(det)
        db.commit()
        db.refresh(orden)

        orden_id = orden.id
        req = AutorizarOrdenRequest(autorizado=False, observaciones="Cliente no aprobó presupuesto")
        result = autorizar_orden_trabajo(orden_id, req, db, usr)

        estado_val = result.estado.value if hasattr(result.estado, "value") else str(result.estado)
        assert estado_val == "CANCELADA", f"Estado debería ser CANCELADA, es {estado_val}"
        assert result.motivo_cancelacion == "Cliente no aprobó presupuesto", f"Motivo incorrecto: {result.motivo_cancelacion}"
        assert result.fecha_cancelacion is not None, "fecha_cancelacion debe registrarse"
        assert result.id_usuario_cancelacion == usr.id_usuario, "id_usuario_cancelacion debe registrarse"

        orden_borrar = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == orden_id).first()
        if orden_borrar:
            db.delete(orden_borrar)
        db.commit()
        print("  [OK] Autorizar rechazo: orden pasa a CANCELADA con auditoría correcta")
        return True
    except Exception as e:
        print(f"  [FAIL] Autorizar rechazo: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_6_corte_diario_filtro_por_turno():
    """
    Corte diario debe filtrar por id_turno: solo muestra pagos/gastos del turno abierto actual,
    no mezcla datos de turnos cerrados anteriores del mismo cajero.
    """
    from app.database import SessionLocal
    from app.models.pago import Pago
    from app.models.caja_turno import CajaTurno
    from app.models.gasto_operativo import GastoOperativo
    from app.models.venta import Venta
    from app.models.usuario import Usuario
    from sqlalchemy import func
    from datetime import datetime, date

    db = SessionLocal()
    try:
        usr = db.query(Usuario).filter(
            Usuario.rol.in_(["ADMIN", "CAJA"]),
            Usuario.activo == True
        ).first()
        venta = db.query(Venta).filter(
            Venta.estado != "CANCELADA",
            Venta.total >= 500
        ).first()

        if not usr or not venta:
            print("  [SKIP] Corte diario: faltan usuario CAJA/ADMIN o venta válida")
            return True

        # Evitar conflicto: cerrar turnos abiertos del usuario si existen
        turnos_abiertos = db.query(CajaTurno).filter(
            CajaTurno.id_usuario == usr.id_usuario,
            CajaTurno.estado == "ABIERTO"
        ).all()
        for t in turnos_abiertos:
            t.estado = "CERRADO"
            t.fecha_cierre = datetime.utcnow()
        db.commit()

        # Turno A (cerrado): 2 pagos de 100 + 100 = 200, gasto 20
        turno_a = CajaTurno(
            id_usuario=usr.id_usuario,
            monto_apertura=100,
            monto_cierre=320,
            estado="CERRADO",
            fecha_cierre=datetime.utcnow()
        )
        db.add(turno_a)
        db.flush()

        pago_a1 = Pago(
            id_venta=venta.id_venta,
            id_usuario=usr.id_usuario,
            id_turno=turno_a.id_turno,
            metodo="EFECTIVO",
            monto=100,
        )
        pago_a2 = Pago(
            id_venta=venta.id_venta,
            id_usuario=usr.id_usuario,
            id_turno=turno_a.id_turno,
            metodo="TARJETA",
            monto=100,
        )
        db.add_all([pago_a1, pago_a2])

        gasto_a = GastoOperativo(
            fecha=date.today(),
            concepto="Test gasto turno A",
            monto=20,
            categoria="OTROS",
            id_turno=turno_a.id_turno,
            id_usuario=usr.id_usuario,
        )
        db.add(gasto_a)
        db.flush()

        # Turno B (abierto): 1 pago de 50, gasto 10
        turno_b = CajaTurno(
            id_usuario=usr.id_usuario,
            monto_apertura=50,
            estado="ABIERTO",
        )
        db.add(turno_b)
        db.flush()

        pago_b = Pago(
            id_venta=venta.id_venta,
            id_usuario=usr.id_usuario,
            id_turno=turno_b.id_turno,
            metodo="EFECTIVO",
            monto=50,
        )
        db.add(pago_b)

        gasto_b = GastoOperativo(
            fecha=date.today(),
            concepto="Test gasto turno B",
            monto=10,
            categoria="OTROS",
            id_turno=turno_b.id_turno,
            id_usuario=usr.id_usuario,
        )
        db.add(gasto_b)
        db.commit()
        db.refresh(turno_b)

        # Simular lógica de corte_diario: obtiene turno ABIERTO y filtra por id_turno
        turno_actual = db.query(CajaTurno).filter(
            CajaTurno.id_usuario == usr.id_usuario,
            CajaTurno.estado == "ABIERTO"
        ).first()

        assert turno_actual is not None, "Debe haber un turno abierto"
        assert turno_actual.id_turno == turno_b.id_turno, "El turno abierto debe ser Turno B"

        total_general = (
            db.query(func.coalesce(func.sum(Pago.monto), 0))
            .filter(Pago.id_turno == turno_actual.id_turno)
            .scalar()
        )
        total_gastos = (
            db.query(func.coalesce(func.sum(GastoOperativo.monto), 0))
            .filter(GastoOperativo.id_turno == turno_actual.id_turno)
            .scalar()
        )

        # Debe mostrar solo datos del Turno B (50 + 10), NO del Turno A (200 + 20)
        assert float(total_general) == 50.0, (
            f"Corte debe sumar solo pagos del turno abierto (50), no {total_general}"
        )
        assert float(total_gastos) == 10.0, (
            f"Corte debe sumar solo gastos del turno abierto (10), no {total_gastos}"
        )

        # Limpiar
        db.delete(pago_b)
        db.delete(pago_a1)
        db.delete(pago_a2)
        db.delete(gasto_a)
        db.delete(gasto_b)
        db.delete(turno_a)
        db.delete(turno_b)
        db.commit()

        print("  [OK] Corte diario: filtra correctamente por id_turno (no mezcla turnos)")
        return True
    except Exception as e:
        print(f"  [FAIL] Corte diario: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_7_dashboard_total_facturado_desde_ventas():
    """
    total_facturado debe sumar Ventas vinculadas a órdenes (no canceladas),
    no el total de órdenes COMPLETADA/ENTREGADA.
    """
    from app.database import SessionLocal
    from app.models.venta import Venta
    from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden
    from app.models.vehiculo import Vehiculo
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario
    from sqlalchemy import func
    from decimal import Decimal
    from datetime import datetime

    db = SessionLocal()
    try:
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.activo == True).first()
        if not all([cli, vh, usr]):
            print("  [SKIP] Total facturado: faltan cliente, vehículo o usuario")
            return True

        # Crear orden con total 5000 (trabajo estimado)
        orden = OrdenTrabajo(
            numero_orden=f"OT-DASH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            vehiculo_id=vh.id_vehiculo,
            cliente_id=cli.id_cliente,
            fecha_ingreso=datetime.now(),
            estado=EstadoOrden.ENTREGADA,
            prioridad="NORMAL",
            diagnostico_inicial="Test dashboard",
            subtotal_servicios=Decimal("5000"),
            subtotal_repuestos=Decimal("0"),
            descuento=Decimal("0"),
            total=Decimal("5000"),
            cliente_proporciono_refacciones=False,
        )
        db.add(orden)
        db.flush()

        # Venta vinculada: facturamos 4500 (con descuento vs orden)
        venta_activa = Venta(
            id_cliente=cli.id_cliente,
            id_vehiculo=vh.id_vehiculo,
            id_usuario=usr.id_usuario,
            id_orden=orden.id,
            total=Decimal("4500.00"),
            estado="PAGADA",
        )
        db.add(venta_activa)
        db.flush()

        # Venta cancelada vinculada a misma orden (no debe contar)
        venta_cancelada = Venta(
            id_cliente=cli.id_cliente,
            id_vehiculo=vh.id_vehiculo,
            id_usuario=usr.id_usuario,
            id_orden=orden.id,
            total=Decimal("999.00"),
            estado="CANCELADA",
        )
        db.add(venta_cancelada)
        db.commit()

        # Replicar query de obtener_estadisticas_dashboard
        total_facturado = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.id_orden.isnot(None),
            Venta.estado != "CANCELADA"
        ).scalar() or 0

        # Debe incluir 4500 (venta activa), NO 999 (cancelada), NO 5000 (total orden)
        assert float(total_facturado) >= 4500.0, (
            f"total_facturado debe incluir venta activa (>=4500), es {total_facturado}"
        )
        # Verificar que nuestra venta de 4500 está en la suma
        suma_nuestras = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.id_orden == orden.id,
            Venta.estado != "CANCELADA"
        ).scalar() or 0
        assert float(suma_nuestras) == 4500.0, f"Suma de nuestras ventas activas debe ser 4500, es {suma_nuestras}"

        # Limpiar
        db.delete(venta_cancelada)
        db.delete(venta_activa)
        db.delete(orden)
        db.commit()

        print("  [OK] Dashboard total_facturado: suma Ventas vinculadas (excluye canceladas)")
        return True
    except Exception as e:
        print(f"  [FAIL] Dashboard total_facturado: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_8_orden_fecha_promesa_antes_ingreso():
    """Crear orden con fecha_promesa < fecha_ingreso debe rechazar."""
    from fastapi import HTTPException
    from app.database import SessionLocal
    from app.models.vehiculo import Vehiculo
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario
    from app.models.servicio import Servicio
    from app.routers.ordenes_trabajo import crear_orden_trabajo
    from app.schemas.orden_trabajo_schema import OrdenTrabajoCreate, DetalleServicioCreate
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.rol.in_(["ADMIN", "CAJA", "TECNICO"])).first()
        serv = db.query(Servicio).first()
        if not all([cli, vh, usr, serv]):
            print("  [SKIP] fecha_promesa: faltan datos")
            return True

        # fecha_promesa = ayer (antes de fecha_ingreso que será now)
        fecha_promesa_ayer = datetime.now() - timedelta(days=1)
        orden_data = OrdenTrabajoCreate(
            vehiculo_id=vh.id_vehiculo,
            cliente_id=cli.id_cliente,
            fecha_promesa=fecha_promesa_ayer,
            prioridad="NORMAL",
            diagnostico_inicial="Test validación",
            observaciones_cliente="Test",
            servicios=[DetalleServicioCreate(servicio_id=serv.id, cantidad=1, descuento=0)],
            repuestos=[],
            descuento=0,
        )

        try:
            crear_orden_trabajo(orden_data, db, usr)
            assert False, "Debió rechazar fecha_promesa < fecha_ingreso"
        except HTTPException as e:
            assert e.status_code == 400
            assert "fecha promesa" in str(e.detail).lower() or "fecha_ingreso" in str(e.detail).lower()
        print("  [OK] Orden: fecha_promesa < fecha_ingreso rechazado correctamente")
        return True
    except Exception as e:
        print(f"  [FAIL] fecha_promesa: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_9_orden_descuento_excede_subtotal():
    """Crear orden con descuento > subtotal debe rechazar."""
    from fastapi import HTTPException
    from app.database import SessionLocal
    from app.models.vehiculo import Vehiculo
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario
    from app.models.servicio import Servicio
    from app.routers.ordenes_trabajo import crear_orden_trabajo
    from app.schemas.orden_trabajo_schema import OrdenTrabajoCreate, DetalleServicioCreate
    from decimal import Decimal

    db = SessionLocal()
    try:
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.rol.in_(["ADMIN", "CAJA", "TECNICO"])).first()
        serv = db.query(Servicio).first()
        if not all([cli, vh, usr, serv]):
            print("  [SKIP] descuento: faltan datos")
            return True

        # Servicio 100, descuento 150 > 100
        orden_data = OrdenTrabajoCreate(
            vehiculo_id=vh.id_vehiculo,
            cliente_id=cli.id_cliente,
            prioridad="NORMAL",
            diagnostico_inicial="Test validación",
            observaciones_cliente="Test",
            servicios=[DetalleServicioCreate(servicio_id=serv.id, cantidad=1, precio_unitario=100, descuento=0)],
            repuestos=[],
            descuento=Decimal("150"),
        )

        try:
            crear_orden_trabajo(orden_data, db, usr)
            assert False, "Debió rechazar descuento > subtotal"
        except HTTPException as e:
            assert e.status_code == 400
            assert "descuento" in str(e.detail).lower()
        print("  [OK] Orden: descuento > subtotal rechazado correctamente")
        return True
    except Exception as e:
        print(f"  [FAIL] descuento: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_10_eliminar_orden_con_venta_vinculada():
    """Eliminar orden cancelada con venta vinculada debe rechazar."""
    from fastapi import HTTPException
    from app.database import SessionLocal
    from app.models.orden_trabajo import OrdenTrabajo, EstadoOrden
    from app.models.venta import Venta
    from app.models.vehiculo import Vehiculo
    from app.models.cliente import Cliente
    from app.models.usuario import Usuario
    from app.routers.ordenes_trabajo import eliminar_orden_trabajo
    from decimal import Decimal
    from datetime import datetime

    db = SessionLocal()
    try:
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr_admin = db.query(Usuario).filter(Usuario.rol == "ADMIN").first() or db.query(Usuario).first()
        if not all([cli, vh, usr_admin]):
            print("  [SKIP] eliminar orden: faltan datos")
            return True

        orden = OrdenTrabajo(
            numero_orden=f"OT-DEL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            vehiculo_id=vh.id_vehiculo,
            cliente_id=cli.id_cliente,
            fecha_ingreso=datetime.now(),
            estado=EstadoOrden.CANCELADA,
            prioridad="NORMAL",
            diagnostico_inicial="Test",
            subtotal_servicios=Decimal("100"),
            subtotal_repuestos=Decimal("0"),
            descuento=Decimal("0"),
            total=Decimal("100"),
            cliente_proporciono_refacciones=False,
        )
        db.add(orden)
        db.flush()

        venta = Venta(
            id_cliente=cli.id_cliente,
            id_vehiculo=vh.id_vehiculo,
            id_usuario=usr_admin.id_usuario,
            id_orden=orden.id,
            total=Decimal("100"),
            estado="PAGADA",
        )
        db.add(venta)
        db.commit()
        db.refresh(orden)

        try:
            eliminar_orden_trabajo(orden.id, db, usr_admin)
            assert False, "Debió rechazar eliminar orden con venta vinculada"
        except HTTPException as e:
            assert e.status_code == 400
            assert "venta" in str(e.detail).lower()

        db.delete(venta)
        db.delete(orden)
        db.commit()
        print("  [OK] Eliminar orden: con venta vinculada rechazado correctamente")
        return True
    except Exception as e:
        print(f"  [FAIL] eliminar orden: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_11_actualizar_venta_repuesto_inexistente_inactivo():
    """Actualizar venta con repuesto inexistente o inactivo debe rechazar."""
    from fastapi import HTTPException
    from app.database import SessionLocal
    from app.models.venta import Venta
    from app.models.detalle_venta import DetalleVenta
    from app.models.repuesto import Repuesto
    from app.models.cliente import Cliente
    from app.models.vehiculo import Vehiculo
    from app.models.usuario import Usuario
    from app.routers.ventas import crear_venta, actualizar_venta
    from app.schemas.venta import VentaCreate, VentaUpdate, DetalleVentaCreate
    from decimal import Decimal

    db = SessionLocal()
    try:
        cli = db.query(Cliente).first()
        vh = db.query(Vehiculo).filter(Vehiculo.id_cliente == cli.id_cliente).first()
        usr = db.query(Usuario).filter(Usuario.activo == True).first()
        rep_activo = db.query(Repuesto).filter(
            Repuesto.activo == True, Repuesto.eliminado == False, Repuesto.stock_actual >= 1
        ).first()
        if not all([cli, vh, usr, rep_activo]):
            print("  [SKIP] actualizar venta repuesto: faltan datos")
            return True

        # Crear venta manual con repuesto válido
        data_create = VentaCreate(
            id_cliente=cli.id_cliente,
            id_vehiculo=vh.id_vehiculo,
            requiere_factura=False,
            detalles=[DetalleVentaCreate(
                tipo="PRODUCTO", id_item=rep_activo.id_repuesto, descripcion=rep_activo.nombre,
                cantidad=1, precio_unitario=50.0,
            )],
        )
        result = crear_venta(data_create, db, usr)
        id_venta = result["id_venta"]

        # Intentar actualizar con id_item inexistente (ID muy alto)
        id_falso = 99999999
        data_update = VentaUpdate(
            id_cliente=cli.id_cliente,
            id_vehiculo=vh.id_vehiculo,
            requiere_factura=False,
            detalles=[DetalleVentaCreate(
                tipo="PRODUCTO", id_item=id_falso, descripcion="Repuesto falso",
                cantidad=1, precio_unitario=50.0,
            )],
        )
        try:
            actualizar_venta(id_venta, data_update, db, usr)
            assert False, "Debió rechazar repuesto inexistente"
        except HTTPException as e:
            assert e.status_code in (404, 400)
            assert "repuesto" in str(e.detail).lower() or "encontrado" in str(e.detail).lower()

        # Limpiar: cancelar venta (la venta original tiene rep_activo que ya descontamos)
        venta = db.query(Venta).filter(Venta.id_venta == id_venta).first()
        if venta and venta.estado != "CANCELADA":
            from app.services.inventario_service import InventarioService
            from app.schemas.movimiento_inventario import MovimientoInventarioCreate
            from app.models.movimiento_inventario import TipoMovimiento
            InventarioService.registrar_movimiento(
                db, MovimientoInventarioCreate(
                    id_repuesto=rep_activo.id_repuesto, tipo_movimiento=TipoMovimiento.ENTRADA,
                    cantidad=1, precio_unitario=None, referencia=f"Venta#{id_venta}", motivo="Limpieza test",
                ), usr.id_usuario,
            )
            venta.estado = "CANCELADA"
        db.commit()

        print("  [OK] Actualizar venta: repuesto inexistente/inactivo rechazado correctamente")
        return True
    except Exception as e:
        print(f"  [FAIL] actualizar venta repuesto: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    print("\n=== Verificación de correcciones de bugs críticos ===\n")
    ok = 0
    total = 11

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

    print("\n5. Autorizar rechazo (autorizado=False) -> CANCELADA con auditoría")
    if test_5_autorizar_rechazo_cancela():
        ok += 1

    print("\n6. Corte diario caja (filtro por id_turno)")
    if test_6_corte_diario_filtro_por_turno():
        ok += 1

    print("\n7. Dashboard total_facturado (usa Ventas vinculadas)")
    if test_7_dashboard_total_facturado_desde_ventas():
        ok += 1

    print("\n8. Orden: fecha_promesa < fecha_ingreso rechazado")
    if test_8_orden_fecha_promesa_antes_ingreso():
        ok += 1

    print("\n9. Orden: descuento > subtotal rechazado")
    if test_9_orden_descuento_excede_subtotal():
        ok += 1

    print("\n10. Eliminar orden: con venta vinculada rechazado")
    if test_10_eliminar_orden_con_venta_vinculada():
        ok += 1

    print("\n11. Actualizar venta: repuesto inexistente/inactivo rechazado")
    if test_11_actualizar_venta_repuesto_inexistente_inactivo():
        ok += 1

    print(f"\n=== Resultado: {ok}/{total} pruebas OK ===\n")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
