/**
 * Manual de usuario - MedinaAutoDiag
 * Contenido del manual organizado por módulo
 */

export const seccionesManual = [
  {
    id: 'acceso',
    titulo: 'Acceso al sistema',
    contenido: `
## Iniciar sesión
1. Ingresa tu **email** y **contraseña**.
2. Haz clic en **Iniciar sesión**.
3. Si olvidaste tu contraseña, haz clic en **¿Olvidaste tu contraseña?** e ingresa tu email. Recibirás un enlace para restablecerla (revisa también la carpeta de spam).

![Pantalla de inicio de sesión](/manual/placeholder.svg)

## Crear cuenta (primera vez)
Si eres el primer usuario del sistema, verás el enlace **¿Primera vez? Crear cuenta**. Regístrate con nombre, email y contraseña. El primer usuario se crea como Administrador.

## Cerrar sesión
En el menú lateral inferior, haz clic en **Cerrar sesión**.
`,
  },
  {
    id: 'dashboard',
    titulo: 'Dashboard',
    contenido: `
## Resumen general
El Dashboard muestra:
- **Total facturado**: Pagos recibidos en el período seleccionado (mes, mes pasado, año o acumulado).
- **Órdenes de trabajo**: Resumen por estado.
- **Órdenes del día**: Las que tienen fecha de hoy.
- **Órdenes urgentes**: Las marcadas como alta prioridad.

## Cambiar período
Usa el selector **Total facturado** para ver diferentes períodos.
`,
  },
  {
    id: 'ventas',
    titulo: 'Ventas',
    contenido: `
## Crear una venta
1. Haz clic en **Nueva venta**.
2. Selecciona **cliente** y **vehículo**.
3. Marca **Requiere factura** si aplica IVA.
4. Agrega **servicios** y **repuestos** (productos).
5. Revisa el total y haz clic en **Crear venta**.

![Formulario de nueva venta](/manual/placeholder.svg)

## Registrar pago
1. En la lista de ventas, busca la venta pendiente.
2. Haz clic en el botón de pago (💳).
3. Ingresa el monto y el método (efectivo, tarjeta, transferencia, cheque).
4. Haz clic en **Registrar pago**.

## Ver detalle / descargar ticket
Haz clic en una venta para ver el detalle. Puedes descargar el **ticket** en PDF como comprobante para el cliente.

## Ingresos
En **Ventas → Ingresos** puedes ver el detalle de los pagos recibidos por período.
`,
  },
  {
    id: 'clientes',
    titulo: 'Clientes',
    contenido: `
## Registrar cliente
1. Haz clic en **Nuevo cliente**.
2. Completa nombre, teléfono, email (opcional), dirección, RFC (opcional).
3. Guarda.

## Editar cliente
Haz clic en el botón de editar (✏️) junto al cliente. Modifica los datos y guarda.

## Buscar clientes
Usa la barra de búsqueda para filtrar por nombre, teléfono o email.
`,
  },
  {
    id: 'vehiculos',
    titulo: 'Vehículos',
    contenido: `
## Registrar vehículo
1. Haz clic en **Nuevo vehículo**.
2. Selecciona el **cliente** propietario.
3. Ingresa marca, modelo, año, placas, VIN (opcional), kilometraje.
4. Guarda.

## Editar vehículo
Haz clic en el botón de editar (✏️). Actualiza los datos y guarda.

## Buscar vehículos
Filtra por cliente, marca, modelo o placas.
`,
  },
  {
    id: 'ordenes-trabajo',
    titulo: 'Órdenes de trabajo',
    contenido: `
## Crear orden de trabajo
1. Haz clic en **Nueva orden**.
2. Selecciona **cliente** y **vehículo**.
3. Asigna un **técnico** (opcional).
4. Agrega **servicios** del catálogo.
5. Agrega **repuestos** si aplica (o marca "Cliente proporciona refacciones").
6. Guarda.

## Estados de la orden
- **Pendiente**: Recién creada.
- **En proceso**: El técnico inició el trabajo.
- **Completada**: Trabajo terminado.
- **Entregada**: El cliente ya retiró el vehículo.

El técnico o el encargado puede cambiar el estado desde el detalle de la orden.

## Vincular venta
Cuando la orden está completada, puedes **Crear venta desde orden** para generar la factura y cobrar.

## Ver detalle
Haz clic en una orden para ver servicios, repuestos, estados y acciones.
`,
  },
  {
    id: 'servicios',
    titulo: 'Servicios',
    contenido: `
## Catálogo de servicios
Aquí se administran los servicios que ofrece el taller (cambio de aceite, alineación, frenos, etc.).

## Agregar servicio
1. Haz clic en **Nuevo servicio**.
2. Ingresa nombre, descripción, precio, tiempo estimado.
3. Selecciona la categoría.
4. Guarda.

## Editar o desactivar
Usa los botones ✏️ y 🗑️. Los servicios inactivos siguen en historial pero no aparecen para nuevas órdenes.

## Categorías
En **Configuración → Categorías de servicios** puedes crear categorías para organizar (Mantenimiento, Diagnóstico, etc.).
`,
  },
  {
    id: 'inventario',
    titulo: 'Inventario',
    contenido: `
## Ver repuestos
El inventario muestra todos los repuestos con código, nombre, categoría, stock, precio y estado.

## Agregar repuesto
1. Haz clic en **Nuevo repuesto**.
2. Ingresa código, nombre, categoría, precio de venta, stock inicial.
3. Opcional: bodega, ubicación, nivel, fila.
4. Guarda.

## Entrada de inventario
Cuando recibes mercancía (por orden de compra o compra directa):
1. Busca el repuesto y haz clic en **Entrada**.
2. Ingresa cantidad, motivo (entrada por OC, compra, etc.).
3. Opcional: número de factura, observaciones.
4. Guarda.

## Alertas
En **Inventario → Alertas** verás repuestos con stock bajo o crítico.

## Kardex
Desde un repuesto, haz clic en **Kardex** para ver el historial de movimientos.

## Bodegas, ubicaciones, categorías
Configúralas en **Configuración** (enlaces desde Inventario o menú).
`,
  },
  {
    id: 'proveedores',
    titulo: 'Proveedores',
    contenido: `
## Registrar proveedor
1. **Nuevo proveedor**.
2. Nombre, teléfono, email, dirección.
3. Guarda.

## Editar
Usa el botón de editar. Los proveedores inactivos no aparecen en nuevas órdenes de compra.
`,
  },
  {
    id: 'ordenes-compra',
    titulo: 'Órdenes de compra',
    contenido: `
## Crear orden de compra
1. Haz clic en **Nueva orden de compra**.
2. Selecciona **proveedor**.
3. Agrega **repuestos** (código, cantidad, precio unitario).
4. Opcional: observaciones, fecha de entrega.
5. Guarda.

## Estados
- **Borrador**: Se puede editar.
- **Enviada**: Enviada al proveedor (opcional: enviar por email).
- **Recibida**: Mercancía recibida.
- **Parcialmente recibida**: Recibimiento parcial.
- **Cancelada**: Orden cancelada.

## Recibir mercancía
1. En una orden Enviada o Parcial, haz clic en **Recibir**.
2. Ingresa cantidades recibidas por línea.
3. Opcional: número de factura, observaciones.
4. Confirma. El inventario se actualiza automáticamente.

## Pagar orden
En **Cuentas por pagar** puedes registrar los pagos a proveedores.
`,
  },
  {
    id: 'cuentas-pagar',
    titulo: 'Cuentas por pagar',
    contenido: `
## Dos tipos
- **Por orden de compra**: Saldos pendientes de órdenes de compra recibidas.
- **Manuales**: Facturas, renta, servicios u otros gastos sin orden de compra.

## Ver saldos
Cada pestaña muestra la lista con proveedor, total, pagado, saldo pendiente y antigüedad.

## Registrar pago
1. En la fila de la cuenta, haz clic en **Pagar**.
2. Ingresa monto, método de pago, referencia (opcional).
3. Guarda.

## Nueva cuenta manual
Para facturas que no pasan por orden de compra:
1. Pestaña **Manuales** → **Nueva cuenta**.
2. Concepto, proveedor o acreedor, referencia de factura, monto, vencimiento.
3. Crear.
`,
  },
  {
    id: 'citas',
    titulo: 'Citas',
    contenido: `
## Agendar cita
1. **Nueva cita**.
2. Cliente, vehículo, fecha, hora, tipo (revisión, entrega, etc.).
3. Opcional: notas.
4. Guarda.

## Estados
- **Programada**
- **Confirmada**
- **En taller**
- **Completada**
- **Cancelada**
- **No asistió**

## Editar o cancelar
Haz clic en la cita para ver detalle y cambiar estado o cancelar.
`,
  },
  {
    id: 'devoluciones',
    titulo: 'Devoluciones',
    contenido: `
## Registrar devolución
1. **Nueva devolución**.
2. Selecciona si es por **venta** o por **orden de trabajo**.
3. Elige la venta u orden.
4. Agrega los productos a devolver con cantidad.
5. Motivo y observaciones.
6. Guarda.

El inventario se ajusta automáticamente (entrada de devolución).
`,
  },
  {
    id: 'gastos',
    titulo: 'Gastos',
    contenido: `
## Registrar gasto operativo
1. **Nuevo gasto**.
2. Concepto, categoría, monto, fecha.
3. Opcional: descripción.
4. Guarda.

## Ver por período
Filtra por fechas. Los gastos sirven para reportes de utilidad y control.
`,
  },
  {
    id: 'notificaciones',
    titulo: 'Notificaciones',
    contenido: `
## Alertas del sistema
Aquí se muestran notificaciones como:
- Stock bajo en inventario.
- Órdenes de compra pendientes de recibir.
- Otros avisos configurados.

## Marcar como leída
Haz clic en una notificación para marcarla como leída o actuar sobre ella.
`,
  },
  {
    id: 'caja',
    titulo: 'Caja',
    contenido: `
## Turnos de caja
Un turno representa un período de caja abierta (ej. turno matutino, vespertino).

## Abrir turno
1. **Abrir turno**.
2. Ingresa el monto inicial en efectivo (puede ser 0).
3. Confirma.

## Cerrar turno
1. **Cerrar turno**.
2. Cuenta el efectivo en caja e ingresa el monto real.
3. El sistema compara con el esperado y muestra diferencia (si hay).
4. Confirma.

## Ver historial
Puedes ver los turnos anteriores con detalle de ingresos, egresos y totales por método de pago.
`,
  },
  {
    id: 'auditoria',
    titulo: 'Auditoría',
    contenido: `
## Registro de acciones
La auditoría muestra quién hizo qué y cuándo (crear, editar, eliminar en diferentes módulos).

## Filtros
Filtra por módulo, acción, usuario o fecha para buscar eventos específicos.
`,
  },
  {
    id: 'configuracion',
    titulo: 'Configuración',
    contenido: `
Solo **Administrador** puede acceder a Configuración.

## Usuarios
Crear, editar y desactivar usuarios. Asignar roles (ADMIN, CAJA, TECNICO, EMPLEADO).

## Usuarios y bodegas
Asignar qué bodegas puede ver cada usuario. Si no tiene bodegas asignadas, ve todo.

## Bodegas
Crear bodegas (Principal, Taller, Mostrador, etc.).

## Ubicaciones, estantes, niveles, filas
Organización del inventario físico. Útil para ubicar repuestos.

## Categorías de servicios
Para clasificar servicios (Mantenimiento, Diagnóstico, etc.).

## Categorías de repuestos
Para clasificar repuestos en inventario.
`,
  },
]
