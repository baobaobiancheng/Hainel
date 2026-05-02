from app.api.v1 import knowledge


class FakeNeo4jClient:
    def run(self, cypher: str, parameters: dict) -> list[dict]:
        if "(n1)-[r2]->(n2)" in cypher:
            return [
                {
                    "src": "胸痛",
                    "rel": "need_check",
                    "tgt": "心电图",
                    "tgt_labels": ["Exam"],
                }
            ]
        return [
            {
                "src": parameters["name"],
                "rel": "has_symptom",
                "tgt": "胸痛",
                "tgt_labels": ["Symptom"],
            }
        ]


def test_build_graph_includes_filterable_node_and_relation_metadata(monkeypatch):
    monkeypatch.setattr(knowledge, "get_neo4j_client", lambda: FakeNeo4jClient())

    graph = knowledge._build_graph_from_neo4j("心脏病", depth=2, limit=60)

    center = next(node for node in graph["nodes"] if node["name"] == "心脏病")
    symptom = next(node for node in graph["nodes"] if node["name"] == "胸痛")
    exam = next(node for node in graph["nodes"] if node["name"] == "心电图")

    assert center["category"] == "Center"
    assert center["hop"] == 0
    assert symptom["category"] == "Symptom"
    assert symptom["hop"] == 1
    assert exam["category"] == "Exam"
    assert exam["hop"] == 2

    symptom_link = next(link for link in graph["links"] if link["target"] == "胸痛")
    exam_link = next(link for link in graph["links"] if link["target"] == "心电图")

    assert symptom_link["relation"] == "has_symptom"
    assert symptom_link["label"] == "症状"
    assert symptom_link["category"] == "symptom"
    assert exam_link["relation"] == "need_check"
    assert exam_link["label"] == "诊断检查"
    assert exam_link["category"] == "exam"

    category_names = {category["name"] for category in graph["categories"]}
    assert {"Center", "Symptom", "Exam"}.issubset(category_names)


def test_related_entities_are_derived_from_graph_neighbors(monkeypatch):
    monkeypatch.setattr(knowledge, "get_neo4j_client", lambda: FakeNeo4jClient())

    related_entities = knowledge._get_related_entities_from_graph("心脏病")

    assert related_entities == ["胸痛"]
