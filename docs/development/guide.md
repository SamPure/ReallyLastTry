# Development Guide

This guide provides detailed instructions for setting up and contributing to the project.

## Local Development Setup

1. **Clone and Setup**

   ```bash
   git clone https://github.com/yourusername/ReallyLastTry.git
   cd ReallyLastTry
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Environment Variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run Development Server**
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

```
ReallyLastTry/
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration settings
│   ├── core/             # Core functionality
│   ├── models/           # Pydantic models
│   └── services/         # External service integrations
├── tests/                # Test suite
├── docs/                 # Documentation
└── scripts/             # Utility scripts
```

## Adding New Features

### 1. Creating a New Route

1. **Define the Route**

   ```python
   @app.post("/new-endpoint")
   async def new_endpoint(request: Request):
       """New endpoint description."""
       return {"status": "success"}
   ```

2. **Add Tests**

   ```python
   def test_new_endpoint():
       response = client.post("/new-endpoint")
       assert response.status_code == 200
   ```

3. **Update Documentation**
   - Add endpoint documentation to `docs/reference/api.md`
   - Update OpenAPI tags if needed

### 2. Running Celery Tasks Locally

1. **Start Redis**

   ```bash
   docker run -d -p 6379:6379 redis
   ```

2. **Start Celery Worker**

   ```bash
   celery -A app.worker worker --loglevel=info
   ```

3. **Monitor Tasks**
   ```bash
   celery -A app.worker flower
   ```

## Testing

### Running Tests

1. **All Tests**

   ```bash
   ./scripts/check_all.sh
   ```

2. **Specific Test Categories**
   ```bash
   pytest -m "unit"      # Unit tests only
   pytest -m "integration"  # Integration tests only
   ```

### Writing Tests

1. **Unit Tests**

   ```python
   def test_function():
       result = function_to_test()
       assert result == expected_value
   ```

2. **Integration Tests**
   ```python
   @pytest.mark.integration
   def test_external_service():
       result = external_service.operation()
       assert result.is_valid
   ```

## Code Quality

### Pre-commit Hooks

The project uses pre-commit hooks for code quality:

```bash
pre-commit install
pre-commit run --all-files
```

### Type Checking

Run type checking:

```bash
mypy app
```

### Linting

Run linters:

```bash
flake8 app tests
black --check app tests
isort --check-only app tests
```

## Deployment

### Railway Deployment

1. **Configure Railway**

   - Set up environment variables
   - Configure health check path
   - Set up build command

2. **Deploy**
   ```bash
   railway up
   ```

### Docker Deployment

1. **Build Image**

   ```bash
   docker build -t your-app .
   ```

2. **Run Container**
   ```bash
   docker run -p 8000:8000 your-app
   ```

## Troubleshooting

### Common Issues

1. **Database Connection**

   - Check connection string
   - Verify network access
   - Check credentials

2. **External Services**

   - Verify API keys
   - Check service status
   - Review rate limits

3. **Performance**
   - Monitor response times
   - Check resource usage
   - Review logs for bottlenecks

## Contributing

1. **Fork and Clone**

   ```bash
   git clone https://github.com/your-fork/ReallyLastTry.git
   ```

2. **Create Branch**

   ```bash
   git checkout -b feature/your-feature
   ```

3. **Make Changes**

   - Follow code style
   - Add tests
   - Update documentation

4. **Submit PR**
   - Create pull request
   - Ensure CI passes
   - Request review
