# Imágenes del manual de usuario

Para agregar imágenes (capturas de pantalla, diagramas) al manual:

1. **Coloca las imágenes** en `frontend/public/manual/` (ej. `login.png`, `ventas-listado.png`).

2. **Referéncialas** en `frontend/src/content/manualContenido.js` usando sintaxis Markdown:

```markdown
![Descripción de la imagen](/manual/nombre-archivo.png)
```

Ejemplo en una sección:

```javascript
contenido: `
## Iniciar sesión
1. Ingresa tu **email** y **contraseña**...

![Pantalla de inicio de sesión](/manual/login.png)

2. Haz clic en **Iniciar sesión**.
`
```

3. **Formatos recomendados**: PNG o JPG. Resolución sugerida: 800–1200 px de ancho para buena legibilidad.
