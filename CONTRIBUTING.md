# Contribuir

## Entorno
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[test]'
# opcional LLM
pip install -e '.[agent]'
```

## Estilo
- Docstrings estilo Google.
- Formato recomendado: `ruff` / `black` (opcional).
- Commits estilo Conventional Commits (feat, fix, docs, chore...).

## Tests
```bash
pytest -q
```
Agrega tests para:
- Compilación y corrida del grafo.
- Ejecución de tools y sincronización de evidencia.
- Reglas del router (estático/LLM).
