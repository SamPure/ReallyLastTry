# FastAPI Application Documentation

Welcome to the documentation for our FastAPI application. This application provides a robust API for handling various operations including health checks, metrics, and batch processing.

## Features

- **Health Monitoring**: Comprehensive health check endpoints
- **Metrics**: Prometheus-compatible metrics endpoint
- **Batch Processing**: Efficient batch operations
- **External Integrations**: Google Sheets and Supabase support
- **Email & SMS**: Communication capabilities
- **Redis Integration**: Caching and pub/sub functionality

## Quick Start

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/ReallyLastTry.git
   cd ReallyLastTry
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. Set up environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Health Checks

- `GET /health`: Basic health check
- `GET /ready`: Readiness check
- `GET /metrics`: Prometheus metrics

### Batch Operations

- `POST /batch`: Process batch operations

## Development

See the [Development Guide](development/setup.md) for detailed instructions on setting up your development environment and contributing to the project.

## Testing

Run the test suite:

```bash
./scripts/check_all.sh
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
