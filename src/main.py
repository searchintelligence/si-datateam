from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import db_interface
import uvicorn


app = FastAPI()
db = db_interface.create_connection()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/data_categories", response_class=HTMLResponse)
async def get_data_categories(request: Request):
    query = "SELECT category_id, category_name FROM Categories;"
    data = db_interface.execute_query(db, query)
    options_html = '<option value="">Select a category...</option>' + "".join([
        f'<option value="{item[0]}">{item[1]}</option>' for item in data
    ])
    return HTMLResponse(content=options_html)


@app.get("/data_contexts/{category_id}", response_class=HTMLResponse)
async def get_data_contexts(request: Request, category_id: int):
    query = "SELECT context_id, context_name FROM Contexts WHERE category_id = %s;"
    params = (category_id,)
    data = db_interface.execute_query(db, query, params)
    options_html = '<option value="">Select a context...</option>' + "".join([
        f'<option value="{item[0]}">{item[1]}</option>' for item in data
    ])
    return HTMLResponse(content=options_html)


@app.get("/data_sets/{category_id}/{context_id}", response_class=HTMLResponse)
async def get_data_sets(request: Request, category_id: int, context_id: int):
    query = "SELECT dataset_id, dataset_name FROM Datasets WHERE context_id = %s;"
    params = (context_id,)
    data = db_interface.execute_query(db, query, params)
    checkboxes_html = "".join([
        f'''
        <div class="checkbox-group">
            <input type="checkbox" id="dataset_{item[0]}" name="datasets" value="{item[0]}">
            <label for="dataset_{item[0]}">{item[1]}</label>
        </div>
        '''
        for item in data
    ])
    return HTMLResponse(content=checkboxes_html)


@app.post("/data", response_class=JSONResponse)
async def get_data(
    request: Request,
    context_id: int = Form(...),
    datasets: list = Form(...)
):
    dataset_ids_list = [int(dataset_id) for dataset_id in datasets]

    if not dataset_ids_list:
        return JSONResponse(content={"error": "No datasets selected"}, status_code=400)

    placeholders = ','.join(['%s'] * len(dataset_ids_list))

    query = f"""
        SELECT e.entity_name, d.dataset_name, dv.value
        FROM datavalues dv
        JOIN Entities e ON dv.entity_id = e.entity_id
        JOIN Datasets d ON dv.dataset_id = d.dataset_id
        WHERE e.context_id = %s AND dv.dataset_id IN ({placeholders});
    """
    params = [context_id] + dataset_ids_list

    data = db_interface.execute_query(db, query, params)

    result = {}
    for entity_name, dataset_name, value in data:
        if entity_name not in result:
            result[entity_name] = {}
        result[entity_name][dataset_name] = value

    return JSONResponse(content=result)


@app.get("/citations/{dataset_id}", response_class=JSONResponse)
async def get_citations(request: Request, dataset_id: int):
    query = """
        SELECT citation_id, text, author, url, start_date, end_date, date_accessed
        FROM Citations
        WHERE dataset_id = %s;
    """
    params = (dataset_id,)
    citations = db_interface.execute_query(db, query, params)
    citations_list = [
        {
            "citation_id": item[0],
            "text": item[1],
            "author": item[2],
            "url": item[3],
            "start_date": item[4].isoformat() if item[4] else None,
            "end_date": item[5].isoformat() if item[5] else None,
            "date_accessed": item[6].isoformat() if item[6] else None,
        }
        for item in citations
    ]
    return JSONResponse(content={"citations": citations_list})

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
