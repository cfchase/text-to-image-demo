# Worker Coordination Document

## Overview

This document coordinates the work of 6 Sonnet workers implementing the MCP Image Generation Server. Each worker has a specific domain of responsibility and should follow the interfaces and standards defined in this project.

## Worker Assignments

### Worker A: Storage System Specialist
**Responsibilities:**
- Implement `AbstractStorage` base class in `src/storage/base.py`
- Implement `FileStorage` class in `src/storage/file.py`
- Implement `S3Storage` class in `src/storage/s3.py`
- Create storage factory in `src/storage/__init__.py`
- Write comprehensive unit tests in `tests/unit/storage/`

**Key Requirements:**
- Follow the interface defined in `docs/INTERFACES.md`
- Implement async methods throughout
- Handle errors gracefully with custom exceptions
- Add structured logging for all operations
- Ensure thread-safety for concurrent access

**Deliverables:**
1. `src/storage/base.py` - Abstract base class
2. `src/storage/file.py` - File storage implementation
3. `src/storage/s3.py` - S3 storage implementation
4. `src/storage/__init__.py` - Factory and exports
5. `tests/unit/storage/test_file.py` - File storage tests
6. `tests/unit/storage/test_s3.py` - S3 storage tests

### Worker B: KServe Integration Specialist
**Responsibilities:**
- Implement `KServeClient` in `src/kserve/client.py`
- Create request/response models in `src/kserve/models.py`
- Implement retry logic and error handling
- Create health check functionality
- Write unit and integration tests

**Key Requirements:**
- Use httpx for async HTTP calls
- Implement exponential backoff for retries
- Handle v1 inference protocol correctly
- Convert between internal and KServe formats
- Add comprehensive error messages

**Deliverables:**
1. `src/kserve/client.py` - KServe client implementation
2. `src/kserve/models.py` - Request/response models
3. `src/kserve/exceptions.py` - KServe-specific exceptions
4. `src/kserve/__init__.py` - Exports
5. `tests/unit/kserve/test_client.py` - Client tests
6. `tests/integration/test_kserve_integration.py` - Integration tests

### Worker C: Configuration & Utilities Specialist
**Responsibilities:**
- Implement `Settings` class in `src/config/settings.py`
- Create logging utilities in `src/utils/logging.py`
- Implement ID generation in `src/utils/ids.py`
- Create image utilities in `src/utils/images.py`
- Set up dependency injection helpers

**Key Requirements:**
- Use pydantic-settings for configuration
- Implement structured logging with structlog
- Create secure ID generation (UUIDs)
- Add image format validation
- Support .env files for local development

**Deliverables:**
1. `src/config/settings.py` - Settings management
2. `src/config/__init__.py` - Configuration exports
3. `src/utils/logging.py` - Logging utilities
4. `src/utils/ids.py` - ID generation
5. `src/utils/images.py` - Image utilities
6. `src/utils/__init__.py` - Utility exports
7. `tests/unit/config/test_settings.py` - Settings tests
8. `tests/unit/utils/` - Utility tests

### Worker D: Testing Infrastructure Specialist
**Responsibilities:**
- Set up pytest configuration
- Create test fixtures in `tests/conftest.py`
- Implement mock classes in `tests/mocks/`
- Create test data generators
- Set up coverage reporting

**Key Requirements:**
- Create reusable fixtures for all components
- Implement async test support
- Create realistic mock implementations
- Generate test images for integration tests
- Ensure 80%+ test coverage

**Deliverables:**
1. `tests/conftest.py` - Pytest configuration and fixtures
2. `tests/mocks/storage.py` - Mock storage implementations
3. `tests/mocks/kserve.py` - Mock KServe client
4. `tests/fixtures/` - Test data files
5. `tests/utils.py` - Test utilities
6. `.coveragerc` - Coverage configuration

### Worker E: API & MCP Implementation Specialist
**Responsibilities:**
- Implement MCP server in `src/api/mcp_server.py`
- Create FastAPI app in `src/api/app.py`
- Implement image serving endpoints in `src/api/routes.py`
- Create cleanup background task in `src/api/background.py`
- Integrate all components

**Key Requirements:**
- Use FastMCP 2.10.6 for MCP protocol
- Implement proper error handling
- Add request validation
- Create OpenAPI documentation
- Implement graceful shutdown

**Deliverables:**
1. `src/api/mcp_server.py` - MCP server with generate_image tool
2. `src/api/app.py` - FastAPI application
3. `src/api/routes.py` - HTTP endpoints
4. `src/api/background.py` - Background tasks
5. `src/api/__init__.py` - API exports
6. `src/main.py` - Application entry point
7. `tests/unit/api/` - API unit tests

### Worker F: Documentation & Deployment Specialist
**Responsibilities:**
- Create Dockerfile in `deployment/docker/`
- Write Kubernetes manifests in `deployment/k8s/`
- Update project documentation
- Create example configurations
- Write deployment guides

**Key Requirements:**
- Multi-stage Docker build for efficiency
- Support multiple deployment scenarios
- Create clear deployment instructions
- Include troubleshooting guides
- Add performance tuning recommendations

**Deliverables:**
1. `deployment/docker/Dockerfile` - Container image
2. `deployment/docker/.dockerignore` - Build exclusions
3. `deployment/k8s/deployment.yaml` - Kubernetes deployment
4. `deployment/k8s/service.yaml` - Kubernetes service
5. `deployment/k8s/configmap.yaml` - Configuration
6. `deployment/k8s/secret.yaml` - Secret template
7. `docs/DEPLOYMENT.md` - Deployment guide
8. `docs/TROUBLESHOOTING.md` - Troubleshooting guide

## Communication Protocol

### File Dependencies
Workers should be aware of dependencies between components:
- Worker B depends on Worker C (config, logging)
- Worker E depends on Workers A, B, C (all components)
- Worker D depends on Workers A, B, C (for mocking)
- Worker F depends on all workers (for documentation)

### Interface Compliance
All workers must:
1. Follow interfaces defined in `docs/INTERFACES.md`
2. Adhere to standards in `docs/CODING_STANDARDS.md`
3. Use types defined in shared modules
4. Coordinate on shared constants/enums

### Progress Tracking
Each worker should:
1. Create their assigned files
2. Implement according to specifications
3. Write comprehensive tests
4. Document their work
5. Report completion status

## Quality Requirements

### Code Quality
- All code must pass `black` formatting
- All code must pass `isort` import sorting
- All code must pass `flake8` linting
- All code must pass `mypy` type checking
- Test coverage must exceed 80%

### Documentation
- All public functions must have docstrings
- All modules must have module docstrings
- Complex logic must include inline comments
- README files updated where appropriate

### Testing
- Unit tests for all components
- Integration tests for workflows
- Mock implementations for external dependencies
- Error cases must be tested
- Performance considerations documented

## Integration Points

### Storage Integration
```python
# Worker A provides
storage = create_storage(settings)

# Worker E uses
image_path = await storage.save_image(image_data, image_id, metadata)
url = await storage.get_image_url(image_id)
```

### KServe Integration
```python
# Worker B provides
client = KServeClient(endpoint, model_name)

# Worker E uses
result = await client.generate_image(prompt, **params)
```

### Configuration Integration
```python
# Worker C provides
settings = Settings()

# All workers use
if settings.storage_backend == "s3":
    # S3-specific logic
```

## Timeline

### Phase 1: Core Implementation (Days 1-3)
- Workers A, B, C: Implement core components
- Worker D: Set up testing infrastructure

### Phase 2: Integration (Days 4-5)
- Worker E: Integrate components into API
- Worker D: Create integration tests

### Phase 3: Deployment (Days 6-7)
- Worker F: Create deployment artifacts
- All workers: Fix issues, optimize

## Success Criteria

Each worker's code is considered complete when:
1. All assigned files are created
2. All interfaces are properly implemented
3. All tests pass with >80% coverage
4. Code passes all quality checks
5. Documentation is complete

## Notes for Workers

1. **Ask Questions**: If interfaces are unclear, ask for clarification
2. **Coordinate**: If you need something from another worker, coordinate
3. **Test Early**: Write tests as you implement, not after
4. **Document**: Document tricky parts as you go
5. **Iterate**: First make it work, then make it better

This coordination ensures all workers can work in parallel while maintaining consistency and quality across the project.