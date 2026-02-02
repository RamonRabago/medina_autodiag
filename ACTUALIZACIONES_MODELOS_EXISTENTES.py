# ACTUALIZACIONES_MODELOS_EXISTENTES.py
"""
Este archivo contiene las actualizaciones que debes hacer a tus modelos existentes
para que funcionen correctamente con el módulo de Órdenes de Trabajo

IMPORTANTE: Estas son adiciones, NO reemplaces tus archivos completos
"""

# ============================================
# 1. ACTUALIZAR app/models/vehiculo.py
# ============================================
"""
Agregar esta importación al inicio del archivo:
"""
# from sqlalchemy.orm import relationship

"""
Agregar esta relación dentro de la clase Vehiculo:
"""
# ordenes_trabajo = relationship("OrdenTrabajo", back_populates="vehiculo")


# ============================================
# 2. ACTUALIZAR app/models/cliente.py
# ============================================
"""
Agregar esta importación al inicio del archivo:
"""
# from sqlalchemy.orm import relationship

"""
Agregar esta relación dentro de la clase Cliente:
"""
# ordenes_trabajo = relationship("OrdenTrabajo", back_populates="cliente")


# ============================================
# 3. ACTUALIZAR app/models/usuario.py
# ============================================
"""
Agregar esta importación al inicio del archivo:
"""
# from sqlalchemy.orm import relationship

"""
Agregar esta relación dentro de la clase Usuario:
"""
# ordenes_asignadas = relationship("OrdenTrabajo", back_populates="tecnico")


# ============================================
# 4. ACTUALIZAR app/models/repuesto.py
# ============================================
"""
Agregar esta importación al inicio del archivo:
"""
# from sqlalchemy.orm import relationship

"""
Agregar esta relación dentro de la clase Repuesto:
"""
# detalles_orden = relationship("DetalleRepuestoOrden", back_populates="repuesto")


# ============================================
# 5. ACTUALIZAR app/models/__init__.py
# ============================================
"""
Agregar estas importaciones:
"""
# from app.models.servicio import Servicio
# from app.models.orden_trabajo import OrdenTrabajo
# from app.models.detalle_orden import DetalleOrdenTrabajo, DetalleRepuestoOrden


# ============================================
# 6. ACTUALIZAR app/routers/main.py
# ============================================
"""
Agregar estas importaciones:
"""
# from app.routers import servicios, ordenes_trabajo

"""
Agregar estos routers en la función que incluye todos los routers:
"""
# app.include_router(servicios.router, prefix="/api")
# app.include_router(ordenes_trabajo.router, prefix="/api")


# ============================================
# VERIFICACIÓN COMPLETA DE ARCHIVOS MODIFICADOS
# ============================================
print("""
📋 RESUMEN DE ACTUALIZACIONES NECESARIAS:

1️⃣  app/models/vehiculo.py
   └─ Agregar: ordenes_trabajo = relationship("OrdenTrabajo", back_populates="vehiculo")

2️⃣  app/models/cliente.py
   └─ Agregar: ordenes_trabajo = relationship("OrdenTrabajo", back_populates="cliente")

3️⃣  app/models/usuario.py
   └─ Agregar: ordenes_asignadas = relationship("OrdenTrabajo", back_populates="tecnico")

4️⃣  app/models/repuesto.py
   └─ Agregar: detalles_orden = relationship("DetalleRepuestoOrden", back_populates="repuesto")

5️⃣  app/models/__init__.py
   └─ Agregar imports de: Servicio, OrdenTrabajo, DetalleOrdenTrabajo, DetalleRepuestoOrden

6️⃣  app/routers/main.py
   └─ Agregar include_router para servicios y ordenes_trabajo

⚠️  IMPORTANTE: Después de hacer estos cambios, ejecutar:
   1. db_ordenes_trabajo.sql en MySQL
   2. python poblar_ordenes_trabajo.py
   3. Reiniciar la aplicación FastAPI
""")
