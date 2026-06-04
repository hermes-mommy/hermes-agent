# FinOps Dashboard & PDF Report — Production Patterns Research

**Date:** 2026-06-03
**Request:** P9-011 (monthly PDF reports) + P9-012 (FinOps Grafana dashboard)
**Stack:** Python 3.12, FastAPI, PostgreSQL 16 (TimescaleDB), Redis 7, Grafana

---

## 1. Grafana Dashboard-as-Code: Python-Native Approach

### Winner: `grafanalib` (weaveworks/grafanalib)

**Evidence** ([grafanalib/core.py — SqlTarget](https://github.com/weaveworks/grafanalib/blob/a79ef6eaf143ae1fb0fedb8f655a2e9aa7c1c5d1/grafanalib/core.py#L635-L666)):

```python
from grafanalib.core import (
    Dashboard, Graph, GridPos, SqlTarget, RowPanel,
    Time, YAxes, YAxis, SHORT_FORMAT, OPS_FORMAT,
)

dashboard = Dashboard(
    title="Guinevere FinOps Monthly",
    uid="guinevere-finops",
    time=Time("now-30d", "now"),
    panels=[
        RowPanel(title="Cost Overview", gridPos=GridPos(h=1, w=24, x=0, y=0)),
        Graph(
            title="Monthly LLM Cost ($)",
            dataSource="PostgreSQL-TimescaleDB",
            targets=[
                SqlTarget(
                    rawSql="""SELECT month AS "time", total_cost
                              FROM finops.monthly_summary
                              WHERE $__timeFilter(month)""",
                    refId="A",
                ),
            ],
            yAxes=YAxes(YAxis(format=SHORT_FORMAT)),
            gridPos=GridPos(h=8, w=12, x=0, y=1),
        ),
    ],
).auto_panel_ids()
```

**Generation pipeline** ([grafanalib/_gen.py](https://github.com/weaveworks/grafanalib/blob/a79ef6eaf143ae1fb0fedb8f655a2e9aa7c1c5d1/grafanalib/_gen.py#L169-L184)):

```bash
# Write `my_dashboard.dashboard.py` (must end in .dashboard.py)
generate-dashboard -o provisioning/dashboards/finops.json my_dashboard.dashboard.py
```

**Production adopters confirmed**:
- **RisingWave** (`grafana/risingwave-user-dashboard.dashboard.py`) — uses env vars for source UID and dashboard UID
- **TiKV** (`metrics/grafana/common.py`) — extensive grafanalib patterns with Heatmap, Stat, Table panels
- **Microservices Demo** (`graphs/kubernetes.dashboard.py`) — multi-dashboard provisioning
- **Scality Zenko** (`monitoring/redis/dashboard.py`) — TimeSeries, PieChart, GaugePanel with PostgreSQL datasource

### Three paths for Guinevere:

| Path | Tool | Approach |
|------|------|----------|
| **Python-native (recommended)** | `grafanalib` | Write Python, generate JSON, file-provision |
| **Jsonnet** | Grafonnet (deprecated by Grafana) | JSON templates; harder to Python-embed |
| **API upload** | `grafana_client` + `grafanalib` | Generate + POST to `/api/dashboards/db` |

---

## 2. PDF Report Generation: Library Comparison

### Head-to-head benchmarks (M5 Pro, Python 3.12.13, 2026-04)

**Evidence** ([verityengine/pdf-engine-benchmarks](https://github.com/verityengine/pdf-engine-benchmarks)):

| Engine | 1-page time | Type | Approach | Best for |
|--------|-------------|------|----------|----------|
| **fpdf2** | 0.05s | Python API | Procedural | Fast, simple docs |
| **ReportLab** | 0.08s | Python API | Programmatic | Complex layouts, precise control |
| **WeasyPrint** | 0.35s | HTML→CSS | CSS layout engine | HTML templates, rich CSS |
| **Typst (py)** | ~0.05s | Template | Markup compiled | Fast templating (new) |
| **pdfkit/wkhtmltopdf** | 0.65s | HTML→PDF | Browser wrapper | JS-dependent pages |

### Winner for Guinevere: **WeasyPrint** (primary) + **ReportLab** (fallback)

**Evidence** — production financial report pattern ([FinceptTerminal/financial_report_generator.py](https://github.com/Fincept-Corporation/FinceptTerminal/blob/main/fincept-qt/scripts/financial_report_generator.py)):

```python
from weasyprint import HTML, CSS
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader
import base64
from io import BytesIO

class FinancialReportGenerator:
    def generate_chart(self, chart_config: dict) -> str:
        """matplotlib → PNG → base64 → embed in HTML → WeasyPrint → PDF"""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(x_data, y_data)
        ax.set_title(title)

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{img_base64}"

    def generate_pdf(self, template_data, output_path):
        html = self.generate_html(template_data)  # Jinja2 render
        HTML(string=html).write_pdf(output_path)   # WeasyPrint
```

**Why WeasyPrint wins for automated financial reports:**
- CSS `@page` directives for headers/footers/page numbers
- Native `@top-center`, `@bottom-center` for recurring elements
- `@page { size: A4 portrait; margin: 2cm; }` for page layout
- Base64-embedded matplotlib PNGs via `<img>` tags
- Jinja2 templating for dynamic data injection
- No external binary dependency (unlike pdfkit/wkhtmltopdf)
- **Async-safe**: runs in thread pool with `run_in_executor`

**Why NOT just fpdf2:**
- No CSS, no HTML templates — procedural API only
- Manual table building, no auto page break intelligence
- Limited Unicode/chart support

**Why NOT pdfkit:**
- Requires wkhtmltopdf binary (deployment headache)
- Slower (0.65s vs 0.35s)
- External dependency breakage risk

**ReportLab as fallback:**
When WeasyPrint system deps (Pango, Cairo) fail, fall back to ReportLab's pure-Python `SimpleDocTemplate` + `Table` + `Paragraph`.

---

## 3. Chart Generation: matplotlib vs alternatives

### Winner: **matplotlib (Agg backend)** for PDF; **Plotly** for Grafana

**For PDF reports** — matplotlib is the only sane choice:
- `matplotlib.use('Agg')` — non-interactive, thread-safe, no display needed
- `savefig(buf, format='png', dpi=150)` → base64 → `<img src="data:image/png;base64,...">`
- WeasyPrint renders inline base64 images natively
- Production pattern from [SpharxTeam/AgentOS](https://github.com/SpharxTeam/AgentOS/blob/main/scripts/ops/benchmark/report_generator.py): matplotlib + Jinja2 → weasyprint

**For Grafana dashboards** — write SQL queries directly; no chart library needed. Grafana handles rendering.

**Why not Plotly for PDF?**
- Plotly generates interactive HTML widgets; WeasyPrint can't render JavaScript
- Plotly static image export (`kaleido`) adds another dependency chain
- Heavier memory footprint than matplotlib

**Why not Altair?**
- Vega-Lite → SVG; WeasyPrint SVG support is partial
- No direct PNG/binary export (requires `altair_saver` or `vl-convert`)

---

## 4. Grafana + PostgreSQL/TimescaleDB Provisioning as Code

### Datasource YAML (`provisioning/datasources/postgres.yaml`)

**Evidence** — production pattern from [huggingface/transformers](https://github.com/huggingface/transformers/blob/main/benchmark/grafana_datasource.yaml):

```yaml
apiVersion: 1
datasources:
  - name: Guinevere-FinOps
    uid: guinevere-finops-pg
    type: postgres
    url: ${PG_HOST}:5432
    user: ${PG_USER}
    secureJsonData:
      password: ${PG_PASSWORD}
    jsonData:
      database: guinevere_finops
      sslmode: disable
      maxOpenConns: 100
      maxIdleConns: 100
      maxIdleConnsAuto: true
      connMaxLifetime: 14400
      postgresVersion: 1600    # PostgreSQL 16
      timescaledb: true        # Enable TimescaleDB toggle
```

**Dashboard provider YAML** (`provisioning/dashboards/default.yaml`):

```yaml
apiVersion: 1
providers:
  - name: 'Guinevere FinOps'
    orgId: 1
    folder: 'FinOps'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30    # reload every 30s in dev
    allowUiUpdates: false        # prevent drift in production
    options:
      path: /etc/grafana/provisioning/dashboards
```

**Version mapping for `postgresVersion`:**
| PostgreSQL | Value |
|------------|-------|
| 13 | 1300 |
| 14 | 1400 |
| 15 | 1500 |
| 16 | 1600 |

### File system layout (GitOps-ready):

```
grafana/
  provisioning/
    dashboards/
      default.yaml                 # provider config
      finops_cost.dashboard.py     # grafanalib source
      finops_cost.json             # generated JSON
      finops_trends.dashboard.py
      finops_trends.json
    datasources/
      postgres.yaml                # TimescaleDB connection
```

### Production reference: Timescale's own `tobs`

**Evidence** ([timescale/tobs chart](https://github.com/timescale/tobs/blob/main/chart/templates/grafana-datasources-sec.yaml)) — sets `timescaledb: true` in jsonData and uses Kubernetes secrets for credentials.

---

## 5. Real Grafana Dashboards for Cost Tracking / FinOps

For Guinevere specifically, the pattern is:

**Data pipeline:**
```
PostgreSQL hypertable (finops.cost_events)
    → continuous aggregates (finops.daily_costs, finops.monthly_costs)
    → Grafana SQL queries with $__timeFilter()
    → TimeSeries / Stat / Table panels
```

**Sample TimescaleDB schema for FinOps:**

```sql
CREATE TABLE finops.cost_events (
    time        TIMESTAMPTZ NOT NULL,
    source      TEXT NOT NULL,        -- 'llm', 'hosting', 'api', 'tool'
    provider    TEXT,                  -- 'openai', 'deepseek', 'anthropic'
    model       TEXT,                  -- 'gpt-5.5', 'deepseek-v4'
    cost_usd    NUMERIC(10,6),
    tokens_in   BIGINT,
    tokens_out  BIGINT,
    metadata    JSONB
);

SELECT create_hypertable('finops.cost_events', 'time');

-- Continuous aggregate: daily rollup
CREATE MATERIALIZED VIEW finops.daily_costs
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    source,
    provider,
    SUM(cost_usd) AS total_cost,
    SUM(tokens_in) AS total_tokens_in,
    SUM(tokens_out) AS total_tokens_out
FROM finops.cost_events
GROUP BY 1, 2, 3;
```

**Dashboard panels to build (grafanalib SqlTarget):**

| Panel | Type | Query pattern |
|-------|------|---------------|
| Cumulative month cost | Stat | `SELECT SUM(cost_usd) FROM finops.daily_costs WHERE $__timeFilter(day)` |
| Daily cost trend | TimeSeries | `SELECT day, total_cost FROM finops.daily_costs WHERE $__timeFilter(day) ORDER BY 1` |
| Cost by provider (pie) | PieChart | `SELECT provider, SUM(total_cost) FROM ... GROUP BY provider` |
| Cost by model | Table | `SELECT model, SUM(total_cost) FROM ... GROUP BY model ORDER BY 2 DESC` |
| 30-day forecast | TimeSeries | TimescaleDB `forecast()` or manual moving average |

**Key `$__timeFilter()` macro**: Grafana injects the dashboard time range filter. Inhypertable queries, this triggers TimescaleDB chunk pruning for efficient scans.

---

## 6. Async Integration with FastAPI

```python
# FastAPI endpoint for monthly report generation
from fastapi import APIRouter, BackgroundTasks
from weasyprint import HTML
import matplotlib; matplotlib.use('Agg')

router = APIRouter(prefix="/finops")

@router.post("/reports/monthly")
async def generate_monthly_report(
    year: int, month: int,
    background_tasks: BackgroundTasks,
):
    """Trigger async monthly FinOps PDF generation"""
    report_id = f"{year}-{month:02d}"

    # Schedule PDF generation in background (not blocking)
    background_tasks.add_task(build_monthly_report, report_id)

    return {"status": "queued", "report_id": report_id}

async def build_monthly_report(report_id: str):
    """Actual PDF generation (runs in thread pool via weasyprint)"""
    # 1. Query TimescaleDB for monthly data
    # 2. Generate matplotlib charts → base64 PNGs
    # 3. Render Jinja2 HTML template with data + charts
    # 4. HTML(string=html).write_pdf(output_path)
    # 5. Store PDF path in Redis for retrieval
    pass
```

**Why `BackgroundTasks` not `Celery`:** For a single-VPS setup, FastAPI's built-in background tasks are sufficient. WeasyPrint isn't true async (CPU-bound), but `BackgroundTasks` runs it in a thread pool without blocking the event loop.

---

## Summary: Recommended Stack

| Layer | Library | Purpose |
|-------|---------|---------|
| **Dashboard-as-code** | `grafanalib` | Python → JSON → file provisioning |
| **Datasource config** | Static YAML | `provisioning/datasources/postgres.yaml` |
| **PDF generation** | `weasyprint` (primary) | HTML/CSS → PDF |
| | `reportlab` (fallback) | Pure Python PDF |
| **HTML templating** | `jinja2` | Report layout with dynamic data |
| **Charts (PDF)** | `matplotlib` (Agg) | PNG → base64 → embed |
| **Data source** | `asyncpg` + TimescaleDB hypertables | Time-series cost data |
| **Async context** | FastAPI `BackgroundTasks` | Non-blocking PDF generation |
| **Chart styling** | CSS `@page` directives | Headers, footers, page numbers |

### File structure for your project:

```
guinevere/
  grafana/
    provisioning/
      dashboards/
        default.yaml              # provider config
        finops_cost.dashboard.py  # grafanalib Python source
      datasources/
        postgres.yaml             # TimescaleDB datasource
  src/finops/
    models.py                     # Pydantic cost models
    queries.py                    # asyncpg SQL queries
    charts.py                     # matplotlib chart generators
    templates/
      monthly_report.html         # Jinja2 report template
    report_builder.py             # HTML assembly + PDF generation
    router.py                     # FastAPI endpoints
  migrations/
    001_finops_schema.sql         # Hypertable + continuous aggregates
```