#!/bin/bash

# Start the observability stack
echo "Starting observability stack..."
docker-compose -f docker-compose.observability.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 5

# Print access information
echo "
Observability Stack is running!

Jaeger UI: http://localhost:16686
Prometheus: http://localhost:9090
Grafana: http://localhost:3000 (admin/admin)

To stop the stack, run:
docker-compose -f docker-compose.observability.yml down
"
