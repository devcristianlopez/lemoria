# Spec Driven Development (SDD)

## Flujo

```
Idea
  ↓
Spec — Especificación detallada
  ↓
PRD — Product Requirements Document
  ↓
Tasks — Desglose en tareas
  ↓
Architecture — Diseño arquitectónico
  ↓
Implementation — Implementación
  ↓
Testing — Pruebas
  ↓
Review — Revisión técnica
  ↓
Commit — Registro con trazabilidad
  ↓
Push — Publicación
  ↓
Documentation — Actualización de docs
  ↓
Memory Update — Persistencia en memoria
```

## State Machine

Cada ejecución del flujo se persiste en `flow_steps`. Pasos:

```bash
lemoria flow step <prd-id> <step-name> --status running
  # → orquestador ejecuta el paso
lemoria flow step <prd-id> <step-name> --status completed --output "resumen"
  # → paso registrado
lemoria flow status <prd-id>
  # → muestra todos los pasos y overall state
```

Esto permite **reanudar flujos** incluso si el contexto del LLM se pierde.

## Principios

1. Toda implementación comienza con un PRD
2. Toda tarea se deriva de un PRD o spec
3. Todo commit referencia una tarea
4. Toda decisión se registra antes de implementar
5. La documentación se actualiza en cada ciclo
6. Todo paso del flujo se persiste como flow step en la DB

## Roles en el flujo

- **Orquestador**: decide el flujo, asigna tareas, ejecuta closing checklist
- **Implementation Agent**: implementación de código (backend, scripts)
- **Frontend Agent**: implementación de UI/UX
- **DB Agent**: gestiona esquemas y modelos
- **Testing Agent**: escribe y ejecuta tests
- **Review Agent**: revisa código y PRDs
- **GitHub Agent**: registra commits, pushes y PRs
- **Documentation Agent**: documenta y sincroniza con vault
