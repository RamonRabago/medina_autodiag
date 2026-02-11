"""
Servicio de Inventario - Lógica de negocio
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import List, Optional
from decimal import Decimal

from app.models.repuesto import Repuesto
from app.models.movimiento_inventario import MovimientoInventario, TipoMovimiento
from app.models.alerta_inventario import AlertaInventario, TipoAlertaInventario
from app.models.categoria_repuesto import CategoriaRepuesto
from app.models.proveedor import Proveedor
from app.schemas.repuesto import RepuestoCreate, RepuestoUpdate
from app.schemas.movimiento_inventario import MovimientoInventarioCreate, AjusteInventario
from app.utils.decimal_utils import to_decimal, money_round, to_float_money

import logging

logger = logging.getLogger(__name__)


class InventarioService:
    """Servicio para gestionar operaciones de inventario"""
    
    @staticmethod
    def registrar_movimiento(
        db: Session,
        movimiento: MovimientoInventarioCreate,
        id_usuario: int,
        autocommit: bool = True,
    ) -> MovimientoInventario:
        """
        Registra un movimiento de inventario y actualiza el stock.
        Usa SELECT FOR UPDATE para evitar condiciones de carrera con operaciones simultáneas.
        """
        # Obtener el repuesto con bloqueo exclusivo (evita race conditions)
        repuesto = db.query(Repuesto).filter(
            Repuesto.id_repuesto == movimiento.id_repuesto
        ).with_for_update().first()
        
        if not repuesto:
            raise ValueError(f"Repuesto con ID {movimiento.id_repuesto} no encontrado")
        
        if not repuesto.activo:
            raise ValueError(f"El repuesto '{repuesto.nombre}' está inactivo")
        
        # Guardar stock anterior
        stock_anterior = repuesto.stock_actual
        
        # Calcular nuevo stock según tipo de movimiento
        if movimiento.tipo_movimiento in [TipoMovimiento.ENTRADA, TipoMovimiento.AJUSTE_POSITIVO]:
            stock_nuevo = stock_anterior + movimiento.cantidad
        elif movimiento.tipo_movimiento in [TipoMovimiento.SALIDA, TipoMovimiento.AJUSTE_NEGATIVO, TipoMovimiento.MERMA]:
            stock_nuevo = stock_anterior - movimiento.cantidad
            if stock_nuevo < 0:
                raise ValueError(
                    f"Stock insuficiente. Stock actual: {stock_anterior}, "
                    f"cantidad solicitada: {movimiento.cantidad}"
                )
        else:
            raise ValueError(f"Tipo de movimiento no válido: {movimiento.tipo_movimiento}")
        
        # Calcular costo total (Decimal para precisión monetaria)
        precio_unitario = to_decimal(movimiento.precio_unitario or repuesto.precio_compra or 0)
        costo_total = money_round(precio_unitario * movimiento.cantidad)

        # Costo promedio ponderado: para ENTRADA o AJUSTE+ con precio, actualizar precio_compra
        if movimiento.tipo_movimiento in [TipoMovimiento.ENTRADA, TipoMovimiento.AJUSTE_POSITIVO]:
            precio_anterior = to_decimal(repuesto.precio_compra or 0)
            valor_anterior = stock_anterior * precio_anterior
            valor_entrada = movimiento.cantidad * precio_unitario
            if stock_nuevo > 0:
                nuevo_costo_promedio = money_round((valor_anterior + valor_entrada) / stock_nuevo)
                repuesto.precio_compra = nuevo_costo_promedio
        
        # Crear registro de movimiento
        nuevo_movimiento = MovimientoInventario(
            id_repuesto=movimiento.id_repuesto,
            tipo_movimiento=movimiento.tipo_movimiento,
            cantidad=movimiento.cantidad,
            precio_unitario=precio_unitario,
            costo_total=costo_total,
            stock_anterior=stock_anterior,
            stock_nuevo=stock_nuevo,
            referencia=movimiento.referencia,
            motivo=movimiento.motivo,
            id_venta=movimiento.id_venta,
            id_usuario=id_usuario,
            id_proveedor=movimiento.id_proveedor,
            imagen_comprobante_url=movimiento.imagen_comprobante_url,
            fecha_adquisicion=movimiento.fecha_adquisicion
        )
        
        # Actualizar stock del repuesto
        repuesto.stock_actual = stock_nuevo
        repuesto.actualizado_en = datetime.utcnow()
        
        db.add(nuevo_movimiento)
        if autocommit:
            db.commit()
            db.refresh(nuevo_movimiento)
            InventarioService.verificar_alertas_stock(db, repuesto)
        
        logger.info(
            f"Movimiento registrado: {movimiento.tipo_movimiento} - "
            f"Repuesto: {repuesto.nombre} - Cantidad: {movimiento.cantidad} - "
            f"Stock: {stock_anterior} → {stock_nuevo}"
        )
        
        return nuevo_movimiento
    
    @staticmethod
    def ajustar_inventario(
        db: Session,
        ajuste: AjusteInventario,
        id_usuario: int
    ) -> MovimientoInventario:
        """
        Ajusta el inventario a un valor específico
        """
        repuesto = db.query(Repuesto).filter(
            Repuesto.id_repuesto == ajuste.id_repuesto
        ).first()
        
        if not repuesto:
            raise ValueError(f"Repuesto con ID {ajuste.id_repuesto} no encontrado")
        
        stock_anterior = repuesto.stock_actual
        diferencia = ajuste.stock_nuevo - stock_anterior
        
        if diferencia == 0:
            raise ValueError("El nuevo stock es igual al actual, no se requiere ajuste")
        
        # Determinar tipo de ajuste
        if diferencia > 0:
            tipo_movimiento = TipoMovimiento.AJUSTE_POSITIVO
            cantidad = diferencia
        else:
            tipo_movimiento = TipoMovimiento.AJUSTE_NEGATIVO
            cantidad = abs(diferencia)
        
        # Crear movimiento de ajuste
        movimiento_ajuste = MovimientoInventarioCreate(
            id_repuesto=ajuste.id_repuesto,
            tipo_movimiento=tipo_movimiento,
            cantidad=cantidad,
            precio_unitario=repuesto.precio_compra,
            referencia=ajuste.referencia,
            motivo=f"AJUSTE DE INVENTARIO: {ajuste.motivo}"
        )
        
        return InventarioService.registrar_movimiento(db, movimiento_ajuste, id_usuario)
    
    @staticmethod
    def verificar_alertas_stock(db: Session, repuesto: Repuesto):
        """
        Verifica el stock y crea alertas si es necesario
        """
        # Verificar si ya existe una alerta activa para este repuesto
        alerta_existente = db.query(AlertaInventario).filter(
            and_(
                AlertaInventario.id_repuesto == repuesto.id_repuesto,
                AlertaInventario.activa == True
            )
        ).first()
        
        # Determinar tipo de alerta según el stock
        tipo_alerta = None
        mensaje = None
        
        if repuesto.stock_actual == 0:
            tipo_alerta = TipoAlertaInventario.SIN_STOCK
            mensaje = f"¡CRÍTICO! El repuesto '{repuesto.nombre}' está SIN STOCK"
        elif repuesto.stock_actual < repuesto.stock_minimo:
            tipo_alerta = TipoAlertaInventario.STOCK_CRITICO
            mensaje = (
                f"Stock crítico: '{repuesto.nombre}' - "
                f"Actual: {repuesto.stock_actual}, Mínimo: {repuesto.stock_minimo}"
            )
        # 20% por encima del mínimo (float evita Decimal*float)
        elif float(repuesto.stock_actual or 0) <= float(repuesto.stock_minimo or 0) * 1.2:
            tipo_alerta = TipoAlertaInventario.STOCK_BAJO
            mensaje = (
                f"Stock bajo: '{repuesto.nombre}' - "
                f"Actual: {repuesto.stock_actual}, Mínimo: {repuesto.stock_minimo}"
            )
        elif repuesto.stock_actual > repuesto.stock_maximo:
            tipo_alerta = TipoAlertaInventario.SOBRE_STOCK
            mensaje = (
                f"Sobre-stock: '{repuesto.nombre}' - "
                f"Actual: {repuesto.stock_actual}, Máximo: {repuesto.stock_maximo}"
            )
        
        # Si no hay problema de stock, resolver alertas activas
        if tipo_alerta is None and alerta_existente:
            alerta_existente.activa = False
            alerta_existente.fecha_resolucion = datetime.utcnow()
            db.commit()
            logger.info(f"Alerta resuelta automáticamente para '{repuesto.nombre}'")
            return
        
        # Si hay alerta y no existe una activa, crearla
        if tipo_alerta and not alerta_existente:
            nueva_alerta = AlertaInventario(
                id_repuesto=repuesto.id_repuesto,
                tipo_alerta=tipo_alerta,
                mensaje=mensaje,
                stock_actual=repuesto.stock_actual,
                stock_minimo=repuesto.stock_minimo,
                stock_maximo=repuesto.stock_maximo
            )
            db.add(nueva_alerta)
            db.commit()
            logger.warning(f"Nueva alerta creada: {mensaje}")
        
        # Si cambió el tipo de alerta, actualizar la existente
        elif tipo_alerta and alerta_existente and alerta_existente.tipo_alerta != tipo_alerta:
            alerta_existente.tipo_alerta = tipo_alerta
            alerta_existente.mensaje = mensaje
            alerta_existente.stock_actual = repuesto.stock_actual
            db.commit()
            logger.warning(f"Alerta actualizada: {mensaje}")
    
    @staticmethod
    def verificar_productos_sin_movimiento(db: Session, dias: int = 90):
        """
        Verifica productos sin movimientos en los últimos X días
        """
        fecha_limite = datetime.utcnow() - timedelta(days=dias)
        
        # Obtener repuestos activos (excluir eliminados)
        repuestos = db.query(Repuesto).filter(
            Repuesto.activo == True,
            Repuesto.eliminado == False
        ).all()
        
        for repuesto in repuestos:
            # Verificar último movimiento
            ultimo_movimiento = db.query(MovimientoInventario).filter(
                MovimientoInventario.id_repuesto == repuesto.id_repuesto
            ).order_by(MovimientoInventario.fecha_movimiento.desc()).first()
            
            # Si no hay movimientos o el último es muy antiguo
            if not ultimo_movimiento or ultimo_movimiento.fecha_movimiento < fecha_limite:
                # Verificar si ya existe alerta
                alerta_existente = db.query(AlertaInventario).filter(
                    and_(
                        AlertaInventario.id_repuesto == repuesto.id_repuesto,
                        AlertaInventario.tipo_alerta == TipoAlertaInventario.SIN_MOVIMIENTO,
                        AlertaInventario.activa == True
                    )
                ).first()
                
                if not alerta_existente:
                    dias_sin_mov = (datetime.utcnow() - ultimo_movimiento.fecha_movimiento).days if ultimo_movimiento else 999
                    nueva_alerta = AlertaInventario(
                        id_repuesto=repuesto.id_repuesto,
                        tipo_alerta=TipoAlertaInventario.SIN_MOVIMIENTO,
                        mensaje=f"Sin movimientos por {dias_sin_mov} días: '{repuesto.nombre}'",
                        stock_actual=repuesto.stock_actual
                    )
                    db.add(nueva_alerta)
        
        db.commit()
        logger.info(f"Verificación de productos sin movimiento completada ({dias} días)")
    
    @staticmethod
    def calcular_valor_inventario(db: Session) -> dict:
        """
        Calcula el valor total del inventario
        """
        resultado = db.query(
            func.sum(Repuesto.stock_actual * Repuesto.precio_compra).label("valor_compra"),
            func.sum(Repuesto.stock_actual * Repuesto.precio_venta).label("valor_venta"),
            func.count(Repuesto.id_repuesto).label("total_productos"),
            func.sum(Repuesto.stock_actual).label("total_unidades")
        ).filter(Repuesto.activo == True, Repuesto.eliminado == False).first()
        
        return {
            "valor_compra": to_float_money(resultado.valor_compra or 0),
            "valor_venta": to_float_money(resultado.valor_venta or 0),
            "utilidad_potencial": to_float_money((resultado.valor_venta or 0) - (resultado.valor_compra or 0)),
            "total_productos": resultado.total_productos or 0,
            "total_unidades": resultado.total_unidades or 0
        }
    
    @staticmethod
    def obtener_productos_mas_vendidos(db: Session, limite: int = 10) -> List[dict]:
        """
        Obtiene los productos más vendidos
        """
        resultado = db.query(
            Repuesto.id_repuesto,
            Repuesto.codigo,
            Repuesto.nombre,
            func.sum(MovimientoInventario.cantidad).label("total_vendido")
        ).join(
            MovimientoInventario,
            Repuesto.id_repuesto == MovimientoInventario.id_repuesto
        ).filter(
            MovimientoInventario.tipo_movimiento == TipoMovimiento.SALIDA,
            Repuesto.eliminado == False
        ).group_by(
            Repuesto.id_repuesto
        ).order_by(
            func.sum(MovimientoInventario.cantidad).desc()
        ).limit(limite).all()
        
        return [
            {
                "id_repuesto": r.id_repuesto,
                "codigo": r.codigo,
                "nombre": r.nombre,
                "total_vendido": r.total_vendido
            }
            for r in resultado
        ]
