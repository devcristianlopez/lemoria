# ADR: Separación de skills Python y Django

**Status**: proposed
**ID**: bc38ec4b
**Proyecto**: [[projects/skills-opencode/README|skills-opencode]]

## Description

Se crean dos skills separados en lugar de uno combinado. Python skill cubre buenas prácticas generales del lenguaje (type hints, testing, logging, etc.) y Django skill cubre el ecosistema Django/DRF (models, views, serializers, performance, seguridad). Esta separación permite activación contextual independiente.

## Rationale

Alternativas: (1) Skill único Python+Django (descartado porque el skill se activaría en cualquier proyecto Python aunque no use Django, y viceversa). (2) Skill solo Django y referenciar Python externamente (descartado porque deja Python general sin cubrir).
