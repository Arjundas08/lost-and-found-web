# /lost_and_found_app/run.py
from app import create_app

# This line MUST be here, outside of the 'if' block
app = create_app()

if __name__ == "__main__":
    app.run()