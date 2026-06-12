# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CLAUDE.md with enforced coding conventions and SDLC workflow
- LICENSE (MIT), CHANGELOG, and CONTRIBUTING files
- Flask-Talisman security headers middleware
- Flask-Limiter rate limiting on API endpoints
- Vitest + React Testing Library frontend test infrastructure
- pytest-cov coverage configuration with 70% minimum threshold
- Separated production and development dependencies

### Fixed
- Pinned all previously unpinned dependency versions
- Replaced `sys.path.insert()` hacks with proper Python package imports
- Separated test dependencies from production requirements

### Security
- Added Content-Security-Policy, X-Frame-Options, HSTS via Flask-Talisman
- Added rate limiting to prevent API abuse

## [1.0.0] - 2026-04-01

### Added
- Multi-objective procurement optimization engine (cost, risk, quality, lead-time)
- Flask REST API with 60+ endpoints
- React 19 frontend with interactive dashboards
- Amazon Neptune graph database integration
- Chronos-2 demand forecasting via SageMaker
- Strands AI procurement agent on Bedrock AgentCore
- AWS CDK infrastructure (14 stacks)
- Amazon Cognito authentication
- Comprehensive documentation suite
