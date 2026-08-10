# DAS-LLM System Architecture & Data Flow

## Overview
DAS-LLM (Deterministic Adversarial Simulation) provides a unified security lifecycle for AI agents across pre-deployment CI/CD testing and real-time production runtime interception.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DAS-LLM Data Protection Architecture                      │
│                                                                             │
│   Incoming Prompt / Document / Web Trajectory                               │
│                       │                                                     │
│                       ▼                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                 Local In-Memory Evaluation Proxy                    │   │
│   │  • Sub-millisecond Execution (<0.1ms)                               │   │
│   │  • Zero Third-Party API Calls (No external LLM judge)               │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                PrivacyGuard Zero-Leakage Engine                     │   │
│   │  • Redacts PCI-DSS Credit Cards & CVVs                              │   │
│   │  • Redacts PII SSNs, Emails, and Phone Numbers                      │   │
│   │  • Redacts Secret API Keys & Auth Bearer Tokens                     │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│   Clean Sanitized Audit Exports (JUnit XML, SOC2 JSON, HTML Certs)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Modules
- **`BoundaryEvaluator` (`src/das_llm/proxy.py`)**: Sub-millisecond tool parameter interceptor.
- **`SimulationRunner` (`src/das_llm/runner.py`)**: Monte Carlo simulation engine.
- **`PrivacyGuard` (`src/das_llm/sanitizer.py`)**: Zero-leakage PCI-DSS & PII regex sanitizer.
- **`DeltaDebugger` (`src/das_llm/shrinker.py`)**: Set reduction algorithm (`ddmin`) for minimal exploit payload extraction.
- **`MutationalFuzzer` (`src/das_llm/fuzzer.py`)**: Homoglyph, zero-width space, and Base64 adversarial fuzzer.
- **`LogToTestIngester` (`src/das_llm/replay.py`)**: Ingests production logs into regression seeds.
- **`DifferentialModelTester` (`src/das_llm/differential.py`)**: Multi-model risk scorecard tester.
- **`RegulatoryComplianceReporter` (`src/das_llm/compliance.py`)**: HTML compliance certificate generator.
