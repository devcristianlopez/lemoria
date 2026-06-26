# ADR: Webcam browser-side con getUserMedia

**Status**: proposed
**ID**: aceaab10
**Proyecto**: [[projects/guardian-live-monitor/README|guardian-live-monitor]]

## Description

Se reemplazó el stream MJPEG del detector por la Web API getUserMedia() del navegador para acceder a la webcam. Esto evita problemas de proxying, latencia y conflictos de puertos. El dashboard intenta getUserMedia primero; si falla (sin webcam o permisos denegados), hace fallback al stream MJPEG.

## Rationale

Alternativas: MJPEG stream via nginx proxy (problemas de compatibilidad y latencia), WebRTC (complejidad excesiva para MVP). getUserMedia es la API estándar del navegador, funciona en localhost sin HTTPS, y da la menor latencia posible.
