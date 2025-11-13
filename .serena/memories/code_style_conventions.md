# ARIS Code Style and Conventions

## Formatting
- **Formatter**: Black (line length 100)
- **Linter**: Ruff (strict mode)
- **Type Checker**: mypy (strict mode)
- **Docstrings**: Google style

## Naming Conventions
- **Files**: snake_case (e.g., `config_manager.py`)
- **Classes**: PascalCase (e.g., `ConfigManager`)
- **Functions/Variables**: snake_case (e.g., `get_api_key`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `SERVICE_NAME`)
- **Environment Variables**: `ARIS_` prefix (e.g., `ARIS_TAVILY_API_KEY`)

## Type Hints
- All functions must have type hints
- Use `Optional[Type]` for nullable types
- Use `list[Type]` and `dict[Key, Value]` (Python 3.11+ syntax)
- Use `-> None` for functions with no return value

## Docstrings
Google style docstrings required for:
- All public classes
- All public functions
- All module-level functions

Example:
```python
def get_api_key(self, provider: str) -> Optional[str]:
    \"\"\"Get API key for a specific provider.

    Args:
        provider: Provider name (tavily, anthropic, openai, google)

    Returns:
        The API key if found, None otherwise

    Raises:
        ConfigurationError: If configuration not loaded
    \"\"\"
```

## Import Organization
1. Standard library imports
2. Third-party imports
3. Local application imports
4. Blank line between each group

## Error Handling
- Use specific exception types
- Create custom exceptions for domain errors (e.g., `ConfigurationError`)
- Always provide helpful error messages
- Log errors appropriately

## Testing
- Unit tests for all core functionality
- Test file naming: `test_<module>.py`
- Test class naming: `Test<ClassName>`
- Test function naming: `test_<description>`
- Use fixtures for common setup/teardown
