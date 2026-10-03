import json

from app.db.session import session_scope
from app.services.demo_seed import seed_demo


def main() -> None:
    with session_scope() as session:
        project_id = seed_demo(session)
    print(json.dumps({"event": "demo_seed_complete", "project_id": str(project_id)}))


if __name__ == "__main__":
    main()
