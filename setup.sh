mkdir -p ~/.streamlit/

cat <<EOF > ~/.streamlit/config.toml
[server]
maxUploadSize = 1024
headless = true
enableCORS = true
enableXsrfProtection = true
port = ${PORT}
EOF
