# python -m venv venv
#.\venv\Scripts\activate
#pip install -r requirements.txt



#python run.py
#deactivate


from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)