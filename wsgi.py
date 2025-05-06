from app_factory import create_app

# Criar a aplicação usando o padrão factory
app = create_app()

# Ponto de entrada para servidores WSGI como Gunicorn
if __name__ == '__main__':
    app.run(debug=True) 