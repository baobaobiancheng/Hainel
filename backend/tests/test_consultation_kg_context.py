from app.services.consultation_service import ConsultationService


def test_create_question_includes_knowledge_graph_summary():
    service = ConsultationService()

    question = service._create_question(
        symptoms="胸口不舒服",
        kg_context={
            "entities": [{"text": "胸闷", "label": "SYMPTOM"}],
            "summary": "胸闷 相关知识：胸闷 - 可能相关 - 冠心病",
        },
    )

    assert "知识图谱辅助信息" in question
    assert "胸闷 - 可能相关 - 冠心病" in question


def test_kg_context_falls_back_when_query_service_fails(monkeypatch):
    service = ConsultationService()

    class FailingKGService:
        def query_by_text(self, text, depth=2, limit=30):
            raise RuntimeError("neo4j unavailable")

    def fake_get_kg_query_service():
        return FailingKGService()

    import app.knowledge.kg_service as kg_service

    monkeypatch.setattr(kg_service, "get_kg_query_service", fake_get_kg_query_service)

    context = service._get_kg_context("胸口不舒服")

    assert context["entities"] == []
    assert context["summary"] == ""
    assert "neo4j unavailable" in context["error"]
