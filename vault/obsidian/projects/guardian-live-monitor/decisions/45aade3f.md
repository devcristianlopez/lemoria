# ADR: Dashboard y distribución en tiempo real

**Status**: proposed
**ID**: 45aade3f
**Proyecto**: [[projects/guardian-live-monitor/README|guardian-live-monitor]]

## Description

Dashboard construido como SPA con Vanilla JS + Tailwind CDN (sin build step). WebSocket con reconexión exponencial (backoff 1s-30s). Event feed con límite de 100 eventos para evitar consumo excesivo de memoria. Animaciones CSS slideIn para nuevos eventos. Indicadores de severidad con código de colores (verde/amarillo/rojo).

## Rationale

Alternativas: React/Vue (overkill para SPA simple, requiere build step), SSE (unidireccional), SockJS (dependencia externa innecesaria). Vanilla JS + WebSocket API nativa es la opción más liviana y directa.
