# Auditoría de dependencias - Medina AutoDiag

**Objetivo:** Detectar vulnerabilidades conocidas en `requirements.txt` y `package.json`.

---

## Ejecución

```bash
# Desde la raíz del proyecto (con venv activado)
python scripts/auditar_dependencias.py
```

O por separado:

```bash
# Python (pip-audit)
pip install pip-audit  # si no está en requirements.txt
pip-audit

# Frontend (npm audit)
cd frontend
npm audit
# o: npm run audit
```

---

## Frecuencia recomendada

- **Semanal** durante desarrollo activo
- **Antes de cada release** o deploy a producción
- Tras añadir o actualizar dependencias

---

## Interpretación

### pip-audit

- **0 vulnerabilidades:** Todo OK
- **Vulnerabilidades:** Revisar CVE indicados. Actualizar paquetes con `pip install -U <paquete>` o esperar parche upstream si no hay fix aún.

### npm audit

- **0 vulnerabilities:** Todo OK
- **Vulnerabilidades:** Ejecutar `npm audit fix` para parches automáticos donde sea posible, o revisar manualmente.

---

## Integración en CI (opcional)

En GitHub Actions u otro CI, añadir un paso:

```yaml
- name: Auditoría de dependencias
  run: |
    pip install pip-audit
    pip-audit
    cd frontend && npm audit --audit-level=high
```

Falla el build si hay vulnerabilidades de nivel `high` o `critical`.
