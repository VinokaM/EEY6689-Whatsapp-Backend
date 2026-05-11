# Test Suite Documentation

## Overview

This directory contains the comprehensive test suite for the multi-platform chatbot backend. The test suite validates webhook handling, message processing, AI response generation, security controls, performance characteristics, and cross-platform consistency.

## Test Framework

The test suite uses **pytest** as the primary test runner with the following extensions:

- **pytest-cov**: Code coverage measurement and reporting
- **pytest-mock**: Mocking support for external dependencies
- **pytest-asyncio**: Support for testing asynchronous code
- **pytest-xdist**: Parallel test execution for faster runs
- **hypothesis**: Property-based testing for input validation

## Setup

### Install Test Dependencies

```bash
pip install -r test/requirements-test.txt
```

### Install Project Dependencies

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Performance tests only
pytest -m performance

# Security tests only
pytest -m security

# Property-based tests only
pytest -m property
```

### Run Specific Test Files

```bash
# WhatsApp tests
pytest test/test_whatsapp.py

# Telegram tests
pytest test/test_telegram.py

# LLaMA AI tests
pytest test/test_llama.py

# Integration tests
pytest test/test_integration.py
```

### Run with Verbose Output

```bash
# Verbose mode
pytest -v

# Very verbose mode (shows test docstrings)
pytest -vv
```

### Run Tests in Parallel

```bash
# Auto-detect number of CPUs
pytest -n auto

# Specify number of workers
pytest -n 4
```

## Coverage Reports

### Generate Coverage Report

Coverage reports are automatically generated when running tests. The configuration in `pytest.ini` ensures:

- Minimum 80% coverage threshold
- HTML report in `htmlcov/` directory
- Terminal report with missing lines

### View HTML Coverage Report

```bash
# Generate and open HTML report
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in your browser
```

### Coverage Configuration

Coverage settings are defined in `.coveragerc`:

- **Source paths**: All project files
- **Omit patterns**: Test files, virtual environments, `__pycache__`
- **Branch coverage**: Enabled
- **Report formats**: HTML, terminal, XML, JSON

## Test Organization

```
test/
├── conftest.py                 # Shared fixtures and configuration
├── fixtures/                   # Test data and sample payloads
│   ├── whatsapp_payloads.json
│   ├── telegram_payloads.json
│   └── ai_responses.json
├── test_whatsapp.py           # WhatsApp webhook and service tests
├── test_telegram.py           # Telegram webhook and service tests
├── test_llama.py              # LLaMA AI service tests
├── test_integration.py        # End-to-end flow tests
├── test_performance.py        # Performance and load tests
└── test_security.py           # Security validation tests
```

## Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests for component interactions
- `@pytest.mark.performance`: Performance and load tests
- `@pytest.mark.security`: Security validation tests
- `@pytest.mark.property`: Property-based tests using Hypothesis

## Writing Tests

### Test Naming Convention

Follow the pattern: `test_<feature>_<scenario>`

```python
def test_whatsapp_webhook_verification_valid_token():
    """Test that valid verify token returns challenge string"""
    # Test implementation
```

### Using Fixtures

Fixtures are defined in `conftest.py` and can be used by including them as function parameters:

```python
def test_send_message(app_client, mock_whatsapp_api):
    """Test message sending with mocked API"""
    # app_client and mock_whatsapp_api are automatically provided
```

### Property-Based Tests

Use Hypothesis for property-based testing:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=4096))
def test_message_handling_property(message_text):
    """Property: All valid messages are processed correctly"""
    result = process_message(message_text)
    assert result is not None
```

## Mock Strategy

The test suite extensively mocks external dependencies:

- **WhatsApp API**: All HTTP requests to Facebook Graph API
- **Telegram API**: All HTTP requests to Telegram Bot API
- **Groq API**: All HTTP requests to Groq AI service

This ensures:
- Fast test execution (no network delays)
- Reliable tests (no external service dependencies)
- Deterministic behavior (consistent results)

## Performance Requirements

- **Unit tests**: Complete in under 5 seconds
- **Integration tests**: Complete in under 10 seconds
- **Full test suite**: Complete in under 15 seconds

## Coverage Threshold

The test suite enforces a **minimum 80% code coverage** threshold. Tests will fail if coverage drops below this level.

## Debugging Failed Tests

### View Captured Output

```bash
# Show captured stdout/stderr for failed tests
pytest -s

# Show captured output for all tests
pytest -s -v
```

### Run Specific Test

```bash
# Run a single test function
pytest test/test_whatsapp.py::test_webhook_verification_valid_token

# Run a single test class
pytest test/test_telegram.py::TestTelegramWebhook
```

### Show Full Traceback

```bash
# Long traceback format
pytest --tb=long

# Short traceback format (default)
pytest --tb=short

# No traceback
pytest --tb=no
```

## Continuous Integration

The test suite is designed for CI/CD integration:

- **Exit codes**: Non-zero on test failure or coverage below threshold
- **JUnit XML**: Generate reports for CI systems with `--junitxml=report.xml`
- **Coverage reports**: XML format for coverage tracking services

### Example CI Command

```bash
pytest --cov=. --cov-report=xml --junitxml=test-results.xml
```

## Best Practices

1. **Write descriptive test names** that explain what is being tested
2. **Include docstrings** for all test functions
3. **Use fixtures** for repeated setup code
4. **Keep tests isolated** - each test should be independent
5. **Mock external dependencies** - never make real API calls in tests
6. **Test edge cases** - empty inputs, boundary values, error conditions
7. **Maintain fast execution** - unit tests should run in milliseconds
8. **Update tests with code changes** - keep tests in sync with implementation

## Troubleshooting

### Import Errors

If you encounter import errors, ensure:
1. You're running pytest from the project root directory
2. All dependencies are installed: `pip install -r requirements.txt -r test/requirements-test.txt`
3. The project structure matches the expected layout

### Coverage Not Measured

If coverage is not being measured:
1. Check that `.coveragerc` exists in the project root
2. Verify `pytest.ini` includes `--cov=.` in `addopts`
3. Ensure you're running pytest from the project root

### Tests Running Slowly

If tests are slow:
1. Verify all external APIs are mocked
2. Use parallel execution: `pytest -n auto`
3. Run only specific test categories: `pytest -m unit`

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [pytest-mock Documentation](https://pytest-mock.readthedocs.io/)
