from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Query, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import db_interface
import uvicorn


app = FastAPI()
db = db_interface.DBInterface()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/contexts", response_class=HTMLResponse)
async def render_contexts(request: Request):
    contexts = db.get_contexts()
    html = "<option value="">Select Context</option>" + "".join([
        f'<option value="{context[0]}">{context[1]}</option>' for context in contexts
    ])
    return HTMLResponse(content=html)


@app.get("/groups", response_class=HTMLResponse)
async def render_groups(request: Request, context: Optional[str] = Query(None)):
    if not context:
        return HTMLResponse(content='')

    context_id = int(context)
    groups = db.get_groups(context_id)
    html = "".join([
        f'<input class="mr-2" type="checkbox" name="group" value="{group[0]}">{group[1]}</input><br>' for group in groups
    ])
    return HTMLResponse(content=html)


@app.get("/datasets", response_class=HTMLResponse)
async def render_datasets(request: Request, context: Optional[str] = Query(None)):
    if not context:
        return HTMLResponse(content='')

    context_id = int(context)
    datasets = db.get_datasets(context_id)
    html = "".join([
        f'<input class="mr-2" type="checkbox" name="set" value="{dataset[0]}">{dataset[1]}</input><br>' for dataset in datasets
    ])
    return HTMLResponse(content=html)


@app.get("/data-table", response_class=HTMLResponse)
async def render_data_table(
    request: Request,
    context: Optional[str] = Query(None),
    group: List[str] = Query(None),
    set:   List[str] = Query(None),
):
    """
    Produces an HTML table:
      - First column header: the context_name (e.g. "Locations").
      - Each row in the first column is an entity's name (e.g. "London", "Paris", etc.).
      - Each subsequent column is one of the selected datasets (e.g. "Population", "Area").
      - The cells contain the 'value' from datavalues.
    """

    # 1) Validate & convert query params
    if not context:
        return HTMLResponse("No context selected.", status_code=400)
    try:
        context_id = int(context)
    except ValueError:
        return HTMLResponse("Invalid context ID.", status_code=400)

    try:
        group_ids = [int(g) for g in group] if group else []
    except ValueError:
        return HTMLResponse("Invalid group ID(s).", status_code=400)

    try:
        dataset_ids = [int(s) for s in set] if set else []
    except ValueError:
        return HTMLResponse("Invalid dataset ID(s).", status_code=400)

    # If no groups or no datasets are selected, we can't pivot data
    if not group_ids or not dataset_ids:
        return HTMLResponse("No groups or datasets selected.")

    # 2) Query the DB for all relevant rows
    rows = db.get_data_for_table(context_id, group_ids, dataset_ids)
    if not rows:
        return HTMLResponse("No data found.")

    # 'rows' are like:
    # [
    #   (context_name, entity_id, entity_name, dataset_id, dataset_name, value),
    #   ...
    # ]

    # 3) Pivot the data in Python
    context_label = None
    datasets_by_id = {}
    entities_data = {}  # key = entity_id -> { 'name': X, 'values': { dataset_id: val } }

    for (ctx_name, ent_id, ent_name, ds_id, ds_name, val) in rows:
        if context_label is None:
            context_label = ctx_name  # e.g. "Locations" or "Products" etc.

        # Store dataset name by ID
        if ds_id not in datasets_by_id:
            datasets_by_id[ds_id] = ds_name

        # Prepare entity structure if not present
        if ent_id not in entities_data:
            entities_data[ent_id] = {
                "name": ent_name,
                "values": {}
            }

        # Store the data value
        entities_data[ent_id]["values"][ds_id] = val

    # 4) Build the HTML table
    #    The first column header is the context name (context_label).
    #    Then a column for each selected dataset (in the order selected, if you like).

    html = "<table border='1' cellpadding='5' cellspacing='0'>"

    # -- Table header
    header_context = context_label if context_label else "Entities"
    html += "<thead><tr>"
    # First column header
    html += f"<th>{header_context}</th>"
    # One column per selected dataset
    for ds_id in dataset_ids:
        ds_name = datasets_by_id.get(ds_id, f"Dataset {ds_id}")
        html += f"<th>{ds_name}</th>"
    html += "</tr></thead>"

    # -- Table body
    html += "<tbody>"

    # Sort entities by entity_name
    def sort_key(item):
        # item is (ent_id, { 'name': 'London', 'values': {...} })
        return item[1]["name"]

    for ent_id, data in sorted(entities_data.items(), key=sort_key):
        entity_name = data["name"]
        html += "<tr>"
        # First cell: entity name
        html += f"<td>{entity_name}</td>"

        # Then each dataset cell in user-selected order
        for ds_id in dataset_ids:
            val = data["values"].get(ds_id, "")
            html += f"<td>{val}</td>"
        html += "</tr>"

    html += "</tbody></table>"

    return HTMLResponse(content=html)


@app.get("/citations", response_class=HTMLResponse)
async def render_citations(request: Request, set: List[str] = Query(None)):
    if not set:
        return HTMLResponse("")
    citations = [db.get_citation(s) for s in set]
    html = "".join([
        f"<div><b>[{i+1}]</b> {c['author']}. {c['text']}: {c['start_date']}" + (f" to {c['end_date']}" if c['end_date'] else "") + f". Available at <a href='http://www.{c['url']}'>{c['url']}</a>.</div>"
        for i, c in enumerate(citations)
    ])
    return HTMLResponse(content=html)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
