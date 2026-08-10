# Contributing to DAS-LLM

Thank you for your interest in contributing to **DAS-LLM**! We welcome bug reports, pull requests, new invariant condition types, and documentation improvements.

---

## Developer Workflow

### 1. Fork & Clone Repository
```bash
git clone https://github.com/animeshs34/das-llm.git
cd das-llm
```

### 2. Setup Local Environment using `uv` or `pip`
```bash
# Using uv (Recommended)
uv sync

# Or standard virtualenv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Run Test Suite
Make sure all pytest unit and integration tests pass before creating a Pull Request:
```bash
uv run pytest -v
```

### 4. Updating Documentation
If you add or update features, run the auto-documentation compiler to regenerate markdown specs and the HTML portal:
```bash
das-llm docgen
```

---

## Submitting Pull Requests

1. Create a feature branch (`git checkout -b feature/my-new-invariant`).
2. Commit your changes with clear, descriptive commit messages.
3. Ensure all pytest tests pass cleanly.
4. Push your branch and open a Pull Request.

---

## Contact & Author

For questions, maintainer inquiries, or security reports:
* **Maintainer**: Animesh Singh
* **Email**: [animeshs34@gmail.com](mailto:animeshs34@gmail.com)
