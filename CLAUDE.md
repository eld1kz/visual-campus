# Visual Campus

## Работа с субагентами

Субагенты лежат в `.claude/agents/`. Единый контракт данных для всех — [`docs/CONTRACT.md`](docs/CONTRACT.md): каждый агент читает его перед работой.

### Зоны файлов

| Агент | Меняет только |
|---|---|
| `sources-agent` | `backend/app/services/sources/`, `backend/tests/sources/`; перенос легаси `services/commons.py`, `services/osm.py`, `services/sources.py` |
| `verify-agent` | `backend/app/services/pipeline/`, `backend/tests/pipeline/`; перенос легаси `services/evidence.py`, `tests/test_evidence.py` |
| `api-agent` | `backend/app/routers/` (кроме `chat.py`), `backend/app/main.py`, `services/orchestrator.py`, `services/cache.py`, `services/summary.py`, `backend/tests/api/`; перенос легаси `services/profile.py`, `tests/test_profile.py` |
| `ui-agent` | `frontend/`, кроме `components/map/`, `lib/map/`, `lib/mock/map.ts`, `components/mascot/`, `lib/types.ts` |
| `map-agent` | `frontend/components/map/`, `frontend/lib/map/`, `frontend/lib/mock/map.ts` |
| `mascot-agent` | `frontend/components/mascot/`, `backend/app/routers/chat.py`, `backend/app/services/chat.py`, `backend/tests/chat/`; в `main.py` — только подключение роутера чата |
| `qa-agent` | ничего — только запускает и проверяет |
| `docs-agent` | `README.md`, `docs/` (кроме `CONTRACT.md`) |
| главный агент | `docs/CONTRACT.md`, `backend/app/models.py`, `frontend/lib/types.ts`, `backend/app/config.py`, `.env.example`-файлы и всё, что не входит в зоны выше (`resolver.py`, `wikidata.py`, `wikipedia.py`, `ror.py`, `text.py`, `hits.py`) |

`backend/requirements.txt` и `frontend/package.json` агенты могут только дополнять новыми зависимостями и сообщают об этом в отчёте.

### Правила

- **Коммитит только главный агент.** Субагенты не выполняют `git commit`, `git push`, `git stash`, `git checkout`/`git reset` файлов и не откатывают чужие изменения.
- Контракт (`docs/CONTRACT.md`, `models.py`, `types.ts`) меняет только главный агент. Субагент, которому нужно изменение, пишет его в отчёт.
- Каждый субагент в конце возвращает отчёт: что сделано, изменённые файлы, как проверить, что осталось, нужны ли изменения контракта.
- Главный агент перед коммитом проверяет, что изменения субагента не вышли за его зону, и прогоняет тесты (`cd backend && .venv/bin/python -m pytest -q`, `cd frontend && npx tsc --noEmit && npm run lint`).
