# 21 Monitoring & Observability Setup

## Objective
Implement application metrics, logging, and tracing for critical flows.

## Prerequisites
- Core services stable

## Deliverables
- Metrics export (Prometheus format)
- Structured logging (request ID correlation)
- Basic traces for booking & payment flows

## Suggested Steps
1. Integrate Prometheus metrics endpoint.
2. Add middleware injecting correlation IDs.
3. Instrument booking and payment services with traces (OpenTelemetry).
4. Dashboard sketches (Grafana panels list).

## Prompts You Can Use
- "Expose Prometheus metrics from FastAPI using prometheus-fastapi-instrumentator."
- "Add request correlation IDs middleware in FastAPI with structlog."
- "Instrument booking flow with OpenTelemetry spans in async FastAPI."
- "Set up logging with loguru for structured async logging." 

## Acceptance Criteria
- Metrics accessible; logs contain correlation IDs.
- Traces show end-to-end booking path.

## Next Task
Proceed to 22 Deployment Pipeline & Environments.