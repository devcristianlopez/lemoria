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

## Principios

1. Toda implementación comienza con un PRD
2. Toda tarea se deriva de un PRD o spec
3. Todo commit referencia una tarea
4. Toda decisión se registra antes de implementar
5. La documentación se actualiza en cada ciclo

## Roles en el flujo

- **Orquestador**: decide el flujo y asigna tareas
- **Backend Agent**: implementa
- **DB Agent**: gestiona esquemas
- **Testing Agent**: prueba
- **Review Agent**: revisa
- **GitHub Agent**: registra commits
- **Documentation Agent**: documenta y sincroniza
