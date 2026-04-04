# Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools). This architecture separates concerns so that probabilistic AI handles reasoning while deterministic code handles execution. That separation is what makes this system reliable.

## Project: АГСК-3 Рабочее место

Цифровая платформа формирования спецификаций оборудования, изделий и материалов на базе каталога **АГСК-3** (Агрегированный сборник сметных классификаторов, Часть 3, Республика Казахстан, март 2026).

Аналог InSmartBase (in-sb.ru/workspace), но на базе казахстанского нормативного каталога.

### Стек технологий

- **Backend:** Python 3.14 + FastAPI + uvicorn
- **Database:** SQLite + FTS5 (полнотекстовый поиск, 234 291 позиция)
- **Frontend:** Vanilla HTML/CSS/JS (single-page app)
- **Excel:** openpyxl — экспорт спецификации по ГОСТ 21.110-2013 на базе шаблона
- **Формат:** А3 landscape, 5 страниц, 107 слотов данных, штамп по ГОСТ 21.1101-2009

### Запуск

```bash
cd "g:/Мой диск/AI/Claude Code/InSmart AGSK-3"
python app.py
# Открыть: http://127.0.0.1:8000
```

## The WAT Architecture

**Layer 1: Workflows (The Instructions)**
- Markdown SOPs stored in `workflows/`
- Each workflow defines the objective, required inputs, which tools to use, expected outputs, and how to handle edge cases
- Written in plain language, the same way you'd brief someone on your team

**Layer 2: Agents (The Decision-Maker)**
- This is your role. You're responsible for intelligent coordination.
- Read the relevant workflow, run tools in the correct sequence, handle failures gracefully, and ask clarifying questions when needed
- You connect intent to execution without trying to do everything yourself
- Example: If you need to pull data from a website, don't attempt it directly. Read `workflows/scrape_website.md`, figure out the required inputs, then execute `tools/scrape_single_site.py`

**Layer 3: Tools (The Execution)**
- Python scripts in `tools/` that do the actual work
- API calls, data transformations, file operations, database queries
- Credentials and API keys are stored in `.env`
- These scripts are consistent, testable, and fast

**Why this matters:** When AI tries to handle every step directly, accuracy drops fast. If each step is 90% accurate, you're down to 59% success after just five steps. By offloading execution to deterministic scripts, you stay focused on orchestration and decision-making where you excel.

## File Structure

```
app.py                      # FastAPI сервер (поиск, разделы, группы, экспорт ГОСТ 21.110)
static/
  index.html                # Веб-интерфейс рабочего места (SPA)
tools/
  agsk.db                   # SQLite база каталога АГСК-3 (234 291 позиция, FTS5)
  convert_agsk.py           # Конвертер Excel → SQLite
  template_spec.xlsx        # Шаблон спецификации по ГОСТ 21.110 (А3, 5 страниц)
output/                     # Сгенерированные файлы спецификаций
.claude/
  skills/                   # 16 скиллов Claude Code
    skill-creator/           # Создание и оценка скиллов
    document-processing/
      xlsx/                  # Excel: ISO-IEC29500 схемы, pack/unpack, recalc.py, валидаторы
      xlsx-official/         # Excel: формулы, форматирование, color coding
      spreadsheet/           # openpyxl + pandas для таблиц
    enterprise-communication/
      excel-analysis/        # Анализ Excel: pivot tables, графики, очистка данных
    web-development/
      fastapi-endpoint/      # Production FastAPI: async, Pydantic v2, pagination, pytest
    ai-research/
      llm-app-patterns/      # RAG, hybrid search, vector DB, agent architectures
    creative-design/
      ui-ux-pro-max/         # 50 стилей, 21 палитра, 50 шрифтовых пар
      tailwind-patterns/     # Tailwind CSS v4
      frontend-design/       # Уникальный UI
    development/
      database-design/       # SQLite/PostgreSQL, индексы, ORM
      cocoindex/             # ETL, embeddings, vector DB
      api-patterns/          # REST паттерны
      clean-code/            # SRP, DRY, KISS
      code-reviewer/         # Автоматическое ревью кода
      docker-expert/         # Контейнеризация
  agents/                   # 4 агента (database-optimization, data-engineer, ui-analyzer, refactoring)
  commands/                 # 4 команды (optimize-db, optimize-api, caching, generate-tests)
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/sections` | Список разделов АГСК-3 (21, 22, 23... 51, 52...) |
| GET | `/api/groups?section=51` | Группы внутри раздела (511-101, 511-102...) |
| GET | `/api/search?q=...&section=&group=&limit=50` | Полнотекстовый поиск по каталогу |
| GET | `/api/match?name=...&section=&limit=5` | Автоподбор кода АГСК-3 по наименованию |
| GET | `/api/context?code=511-302-0116` | Контекст позиции: родительское наименование (ст.2) + характеристика (ст.3) |
| POST | `/api/export/gost` | Экспорт спецификации в Excel по шаблону ГОСТ 21.110 |

## Шаблон спецификации ГОСТ 21.110

Шаблоны: `tools/Шаблон/` (А3 landscape, paperSize=8, 25 колонок A-Y)
- `Шаблон Спецификации Первый лист.xlsx` — 44 строки, штамп Форма 5 (строки 31-44)
- `Шаблон Спецификации Последующие листы (2,3,....).xlsx` — 37 строк, малый штамп Форма 6 (строки 32-37)
- `create-excel-specification-first-sheet.md` — полная документация первого листа
- `create-excel-specification-subsequent-sheets.md` — полная документация последующих листов

### Колонки данных

| Колонка | Поле ГОСТ | Описание |
|---------|-----------|----------|
| G | Поз. | Порядковый номер позиции |
| H | Наименование и техническая характеристика | Основное описание |
| I | Тип, марка, обозначение документа | Марка, ГОСТ, ТУ |
| J (J:M merged) | Код продукции | **Код АГСК-3** |
| N (N:Q merged) | Завод-изготовитель | Производитель |
| R | Единица измерения | шт, м, м2, т, кг... |
| S | Кол-во | Количество |
| T (T:U merged) | Масса единицы | Масса в кг |
| V (V:Y merged) | Примечание | Дополнительная информация |

### Карта строк данных (DATA_ROWS)

| Шаблон | Одинарные строки | Парные строки (step=2) | Всего слотов |
|--------|------------------|------------------------|--------------|
| Первый лист (44 строки) | 4-13 (10) | 15, 17, 19, 21, 23, 25, 27, 29 (8) | 18 |
| Последующий лист (37 строк) | 4-19 (16) | 20, 22, 24, 26, 28, 30 (6) | 22 |

Экспорт автоматически добавляет последующие листы при переполнении первого.

### Штамп (страница 1, строки 38-44)

| Ячейка | Поле |
|--------|------|
| L39, P39 | Разработал (ФИО), Дата |
| L40, P40 | Проверил, Дата |
| L43, P43 | Н. контроль, Дата |
| L44, P44 | Утвердил, Дата |
| Q39 (Q39:T41) | Шифр проекта + Наименование объекта (multiline) |
| U40, W40, X40 | Стадия, Лист, Листов |
| U42 (U42:Y44) | Наименование системы |

### Левая рамка

| Merged | Текст |
|--------|-------|
| B14:C26 | Согласовано |
| C27:D31 | Доп. инв. № |
| C32:D38 | Подпись и дата |
| C39:D44 | Инв. № подл. |

## Каталог АГСК-3

- **Источник:** `АГСК-3_март 2026 all inclusive.xlsx` (C:\Users\KAIRAT_BAIKULOV\Desktop\АГСК-3\)
- **Позиций:** 234 291 (из них 57 776 с ценами)
- **Колонки:** Код, Наименование, Стандарт, Ед. изм, Сметная цена (₸), Отпускная цена (₸)
- **Структура кодов:** `XXX-YYY-ZZZZ` (XXX=группа, YYY=подгруппа, ZZZZ=позиция)
- **Разделы:** 21-28 (материалы и изделия), 51-55 (оборудование)

## How to Operate

**1. Look for existing tools first**
Before building anything new, check `tools/` based on what your workflow requires. Only create new scripts when nothing exists for that task.

**2. Learn and adapt when things fail**
When you hit an error:
- Read the full error message and trace
- Fix the script and retest (if it uses paid API calls or credits, check with me before running again)
- Document what you learned in the workflow (rate limits, timing quirks, unexpected behavior)

**3. Keep workflows current**
Workflows should evolve as you learn. When you find better methods, discover constraints, or encounter recurring issues, update the workflow. That said, don't create or overwrite workflows without asking unless I explicitly tell you to.

## The Self-Improvement Loop

Every failure is a chance to make the system stronger:
1. Identify what broke
2. Fix the tool
3. Verify the fix works
4. Update the workflow with the new approach
5. Move on with a more robust system

## Known Issues & Notes

- **Порты:** при повторном запуске `python app.py` порт может быть занят старым процессом. Убить: `cmd /c "taskkill /F /PID <pid>"` или изменить порт в app.py
- **Кодировка:** Content-Disposition header не поддерживает кириллицу напрямую — используется `filename*=UTF-8''...` (RFC 5987)
- **FTS5:** поиск через `"word"*` — каждое слово с wildcard. Fallback на LIKE при ошибке FTS
- **Шаблон Excel:** merged cells нельзя перезаписывать — пиши только в top-left ячейку merge-диапазона

## Bottom Line

You sit between what I want (workflows) and what actually gets done (tools). Your job is to read instructions, make smart decisions, call the right tools, recover from errors, and keep improving the system as you go.

Stay pragmatic. Stay reliable. Keep learning.
