# ADR: M1.1: Backend project scaffolding and database layer

**Status**: proposed
**ID**: c6eda17d
**Proyecto**: [[projects/guardian-live-monitor/README|guardian-live-monitor]]

## Description

Created backend directory with FastAPI app structure, async SQLAlchemy engine, Event ORM model, Pydantic models with validators, Redis async client, WebSocket connection manager, events REST endpoint, and main FastAPI application with Redis Pub/Sub background worker.

## Rationale

Alternatives considered: sync SQLAlchemy (discarded for async I/O requirements), Kafka instead of Redis Pub/Sub (overkill for single-instance), raw WebSocket handling without manager (coupling concern).
