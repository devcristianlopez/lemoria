# ADR: Arquitectura general del sistema

**Status**: proposed
**ID**: ece2bb2b
**Proyecto**: [[projects/guardian-live-monitor/README|guardian-live-monitor]]

## Description

Se eligió FastAPI como backend asíncrono por su soporte nativo de WebSocket y async/await. PostgreSQL como base de datos relacional por su madurez y precisión de timestamps con timezone. Redis Pub/Sub como broker de mensajería en tiempo real por su simplicidad y baja latencia. WebSocket como canal de distribución al frontend para actualizaciones en tiempo real sin polling. OpenCV para detección de movimiento por frame differencing (simple y eficiente para MVP).

## Rationale

Alternativas consideradas: Django Channels (demasiado pesado para MVP), MQTT (overkill para un solo canal), Server-Sent Events (unidireccional, no permite control bidireccional futuro), MOG2/KNN de OpenCV (más precisos pero más costosos computacionalmente). Se descartaron por complejidad innecesaria para el alcance del MVP.
