import os

from app import create_app
from app.cli import prepare_database

app = create_app()

if __name__ == "__main__":
    # debug 모드에서는 이 파일이 두 번 실행되므로 첫 프로세스에서만 DB를 준비한다
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        with app.app_context():
            prepare_database()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "1") == "1")
