mkdir -p ~/.streamlit/

echo "[server]
headless = true
enableCORS = true
enableXsrfProtection = false
port = ${PORT}
" > ~/.streamlit/config.toml
