# ADR: Infraestructura base del proyecto

**Status**: proposed
**ID**: ccad2ed6
**Proyecto**: [[projects/guardian-live-monitor/README|guardian-live-monitor]]

## Description

Se crearon 3 archivos: .env.example con variables de entorno para BD, Redis, Backend y Detector; .gitignore con exclusiones estándar para Python, Docker, OS e IDE; docker-compose.yml con 5 servicios (postgres, redis, backend, detector, dashboard) en red bridge guardian-net con dependencias ordenadas y healthchecks.

## Rationale

Alternativa 1: usar un solo docker-compose con perfiles (se descartó por simplicidad). Alternativa 2: usar Makefile para orquestación (se descartó porque docker compose ya cubre el ciclo de vida). Alternativa 3: separar en múltiples compose files (innecesario para este alcance).
