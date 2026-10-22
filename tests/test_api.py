from fastapi.testclient import TestClient

from app import main, store


class StubBot:
    class index:  # noqa: N801
        chunks, mode = [1], "stub"

    def answer(self, message, history, disclaimer_shown):
        return {"answer": f"echo: {message}", "sources": [], "answerable": True, "intent": "kb_question",
                "language": "English", "disclaimer": None, "cta": None, "show_lead_form": False}


def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "settings", type("S", (), {"data_dir": tmp_path, "db_file": tmp_path / "t.db"})())
    monkeypatch.setattr(main.service, "start", lambda: None)
    main.service.bot = StubBot()
    main._hits.clear()
    return TestClient(main.app)


def test_chat_lead_and_admin(tmp_path, monkeypatch):
    with client(tmp_path, monkeypatch) as c:
        assert c.get("/health").json()["ready"] is True
        assert c.post("/api/chat", json={"message": "hi"}).json()["answer"] == "echo: hi"
        assert c.post("/api/chat", json={"message": ""}).status_code == 422
        bad = {"name": "A", "email": "nope", "consent": True}
        assert c.post("/api/lead", json=bad).status_code == 400
        assert c.post("/api/lead", json={**bad, "email": "a@b.co", "consent": False}).status_code == 400
        assert c.post("/api/lead", json={**bad, "email": "a@b.co"}).json() == {"ok": True}
        assert c.post("/api/lead", json={**bad, "email": "a@b.co", "website": "spam"}).json() == {"ok": True}
        for _ in range(30):                                            # chat traffic must not eat the lead budget
            c.post("/api/chat", json={"message": "x"})
        assert len(store.list_rows("leads")) == 1                      # honeypot lead was not stored
        assert c.get("/api/admin/gaps").status_code == 401             # no token -> locked
        assert c.get("/").status_code == 200
