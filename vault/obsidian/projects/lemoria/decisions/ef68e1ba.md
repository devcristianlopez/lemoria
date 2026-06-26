---
id: ef68e1ba
type: decision
status: proposed
project: lemoria
---

# ADR: Desvincular upstream y establecer devcristianlopez como repo principal

**Status**: proposed
**ID**: ef68e1ba
**Proyecto**: [[projects/lemoria/README|lemoria]]

## Description

Se eliminó el remote upstream que apuntaba a cristianl0pez-dev/lemoria (cuenta que se borrará). El remote origin ya apuntaba a devcristianlopez/lemoria (cuenta actual). Se actualizó el repo_url del proyecto en la BD.

## Rationale

Alternativas consideradas: 1) Mantener ambos remotos — se descartó porque la otra cuenta se borrará. 2) Renombrar origin/main → upstream y crear nuevo origin — no era necesario porque origin ya apuntaba a la cuenta correcta. 3) Clonar desde cero — innecesario, el historial git estaba completo en el origin actual.
