Clone the repository <br>

Run ```docker compose up --build```. <br>
If unhealthy error occurs (timeout error due to model downloading), simply run it again.

If you don't want to use docker, run ```uvicorn main:app --host 0.0.0.0 --port 8000``` then ```streamlit run streamlit_ui.py --server.port=8501 --server.address=0.0.0.0```. <br>

Input the desired URL's in the sidebar, process them, ask a question based on which URL's you want as context.
