# GUÍA DE SINCRONIZACIÓN: AGENTE AUTÓNOMO

Sigue estos pasos para conectar tu flujo de trabajo de la oficina con este MacBook personal.

## 1. PREPARACIÓN EN MACBOOK (HOY)
- [ ] **Instalar Google Drive Desktop:** Vincular con cuenta laboral.
- [ ] **Configurar Finder:** Asegurar que la unidad de Google Drive sea visible.
- [ ] **Entorno Local:** Instalar [Python](https://www.python.org/downloads/) o [Node.js](https://nodejs.org/) según corresponda.

## 2. ACCIONES EN PC OFICINA (MAÑANA)
- [ ] **Cargar al Drive:** Mover la carpeta del proyecto a la unidad de Google Drive.
- [ ] **Limpiar archivos innecesarios:**
    - Borrar `venv/` o `.env` (si contienen datos sensibles).
    - Borrar `node_modules/` o `__pycache__/`.
- [ ] **Exportar dependencias:** 
    - Ejecutar `pip freeze > requirements.txt` en la terminal.

## 3. RECONEXIÓN FINAL
- [ ] **Confirmación en Mac:** Abrir la carpeta desde el MacBook.
- [ ] **Instalación de librerías:** Ejecutar `pip install -r requirements.txt`.
- [ ] **Validación:** Iniciar el chat con el asistente para confirmar que todo funciona.

---
*Nota: El asistente está listo para optimizar el código una vez se realice la conexión exitosa.*
