"""Lightweight class-scoped retrieval for student AI tutoring."""

from __future__ import annotations

import logging
import re

from repositories.mysql_question_repository import MySQLQuestionRepository
from apps.mastery.services import MasteryBackendUnavailable, MasteryService
from .intent_catalog import is_personal_weakness_query


logger = logging.getLogger("ai")

_STOPWORDS = {
    "怎么", "如何", "什么", "为什么", "请问", "一下", "这个", "那个", "是否", "可以", "帮我", "解释",
    "说明", "一下", "一下子", "请", "问", "我", "想", "知道", "的", "了", "吗", "呢", "和", "与", "是",
    "在", "把", "做", "有", "没有", "一个", "哪些", "怎样", "能不能", "使用", "实现", "区别", "以及",
}
_ENGLISH_STOPWORDS = {"the", "and", "for", "with", "what", "how", "why", "is", "are", "to", "in", "of", "a", "an"}


def _tokens(value: str) -> set[str]:
    lowered = value.lower()
    tokens = {item for item in re.findall(r"[a-z_][a-z0-9_]{1,}|\d+", lowered) if item not in _ENGLISH_STOPWORDS}
    for run in re.findall(r"[\u3400-\u9fff]+", lowered):
        if len(run) <= 4:
            tokens.add(run)
        tokens.update(run[index : index + 2] for index in range(len(run) - 1))
        tokens.update(run[index : index + 3] for index in range(len(run) - 2))
    return {token for token in tokens if token not in _STOPWORDS and len(token) > 1}


def _overlap_count(query_tokens: set[str], value: str) -> int:
    return len(query_tokens & _tokens(value))


def _as_number(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_numeric(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def retrieve_student_context(username: str, class_id: str, graph_class_id: str | None, question: str) -> dict:
    """Return grounded context and safe UI source metadata, never crossing graph scope."""
    personal_weakness_query = is_personal_weakness_query(question)
    if not graph_class_id:
        if personal_weakness_query:
            return {
                "context": "当前教学班尚未配置知识图谱，无法将历史掌握度映射到知识点或推荐关联练习；应说明暂时无法获取，不要猜测。",
                "sources": [], "weak_points": [], "rag_status": "graph_unconfigured",
            }
        return {"context": "", "sources": [], "weak_points": [], "rag_status": "graph_unconfigured"}

    weak_points: list[dict] = []
    mastery_unavailable = False
    try:
        report = MasteryService().get_by_username(username, class_id)
        candidates = [node for node in report.nodes if node.node_type == "point" and node.attempted_count > 0 and node.graph_node_id]
        if personal_weakness_query and candidates:
            lowest_score = min(node.score for node in candidates)
            candidates = [node for node in candidates if node.score == lowest_score]
            candidates.sort(key=lambda node: (-node.attempted_count, str(node.graph_node_id)))
        else:
            candidates = [node for node in candidates if node.score < 60]
            candidates.sort(key=lambda node: (node.score, -node.attempted_count))
        weak_points = [
            {"uid": str(node.graph_node_id), "title": "", "score": round(node.score, 1), "attempted_count": node.attempted_count}
            for node in candidates[:5 if not personal_weakness_query else len(candidates)]
        ]
    except MasteryBackendUnavailable:
        mastery_unavailable = True
        logger.info("ai_retrieval_mastery_unavailable", extra={"class_id": class_id})

    try:
        with MySQLQuestionRepository() as repository:
            point_titles_by_uid = repository.list_ai_point_titles(str(graph_class_id))
            documents = repository.list_ai_documents(str(graph_class_id))
    except Exception:
        logger.exception("ai_retrieval_question_bank_unavailable", extra={"graph_class_id": str(graph_class_id)})
        return {"context": "", "sources": [], "weak_points": weak_points, "rag_status": "unavailable"}
    if not documents and not personal_weakness_query:
        return {"context": "", "sources": [], "weak_points": weak_points, "rag_status": "empty_question_bank"}

    for document in documents:
        for point_link in document["point_links"]:
            if point_link["title"]:
                point_titles_by_uid.setdefault(point_link["uid"], point_link["title"])
    for item in weak_points:
        item["title"] = point_titles_by_uid.get(item["uid"], "未命名知识点")

    query_tokens = _tokens(question)
    # For an explicit personal-weakness request, report the global minimum over
    # attempted points; ordinary questions only receive directly relevant weak points.
    if not personal_weakness_query:
        weak_points = [item for item in weak_points if _overlap_count(query_tokens, item["title"]) >= 2]
    weak_by_uid = {item["uid"]: item for item in weak_points}
    ranked: list[tuple[float, dict, list[dict]]] = []
    for document in documents:
        text = " ".join((document["title"], document["content"], document["analysis"], *document["point_titles"]))
        doc_tokens = _tokens(text)
        overlap = len(query_tokens & doc_tokens)
        linked_weak = [weak_by_uid[uid] for uid in document["point_uids"] if uid in weak_by_uid]
        # Query relevance leads; weak-point alignment breaks ties and provides
        # useful recommendations when the question itself has no exact match.
        score = float(overlap) + (0.35 * len(linked_weak))
        if score > 0:
            ranked.append((score, document, linked_weak))
    ranked.sort(key=lambda item: (-item[0], str(item[1]["title"]).lower(), item[1]["id"]))

    if personal_weakness_query:
        # Recommend only exercises linked to the actual lowest-mastery point(s).
        ranked = []
        for point in weak_points:
            linked_documents = [document for document in documents if point["uid"] in document["point_uids"]]
            linked_documents.sort(key=lambda document: (
                document["difficulty"] is None or not _is_numeric(document["difficulty"]),
                _as_number(document["difficulty"], 999),
                str(document["title"]).lower(),
                document["id"],
            ))
            if linked_documents:
                ranked.append((1.0, linked_documents[0], [point]))

    # If keyword matching found nothing, retrieve exercises from the student's
    # weakest points rather than returning arbitrary questions.
    if not ranked and weak_by_uid:
        for document in documents:
            linked_weak = [weak_by_uid[uid] for uid in document["point_uids"] if uid in weak_by_uid]
            if linked_weak:
                ranked.append((0.0, document, linked_weak))
        ranked.sort(key=lambda item: (min(point["score"] for point in item[2]), item[1]["id"]))

    selected = ranked[:2]
    context_parts: list[str] = []
    if personal_weakness_query:
        if mastery_unavailable:
            context_parts.append("个人掌握度数据暂时不可用；不要猜测最薄弱知识点，也不要将其表述为技能未学会。")
        elif not weak_points:
            context_parts.append("当前教学班没有可用于判断的已练习知识点掌握度记录；应明确说明数据不足，不要用普通题库命中冒充个性化分析。")
        else:
            context_parts.append("学生当前教学班的历史练习中，掌握度最低的知识点为：" + "；".join(
                f"{item['title']}（掌握度 {item['score']} 分，练习 {item['attempted_count']} 次）" for item in weak_points
            ))
            if not selected:
                context_parts.append("这些最低掌握度知识点当前没有匹配到关联练习题；不得推荐无关题目冒充相关练习。")
    elif weak_points:
        context_parts.append("与本轮问题直接相关的已练习薄弱知识点：" + "；".join(
            f"{item['title']}（掌握度 {item['score']} 分，练习 {item['attempted_count']} 次）" for item in weak_points
        ))
    for _, document, linked_weak in selected:
        if personal_weakness_query and linked_weak:
            relevant_point_titles = [linked_weak[0]["title"]]
        else:
            relevant_point_titles = [
                title for title in document["point_titles"]
                if _overlap_count(query_tokens, title) >= 2
            ]
        context_parts.append(
            "相关题目：{title}\n知识点：{points}\n题目内容：{content}".format(
                title=document["title"] or "未命名题目",
                points="、".join(relevant_point_titles or document["point_titles"][:1]) or "未关联知识点",
                content=document["content"] or "暂无题目内容",
            )
        )

    sources = []
    seen = set()
    for _, document, linked_weak in selected:
        mastery_by_uid = {item["uid"]: item for item in linked_weak}
        point_links = document["point_links"] or ({"uid": "", "title": ""},)
        # One resource card per question; prefer the knowledge point that best
        # matches the current query instead of duplicating a card for every link.
        if personal_weakness_query and linked_weak:
            point_link = next((item for item in point_links if item["uid"] == linked_weak[0]["uid"]), point_links[0])
        else:
            point_link = max(point_links, key=lambda item: _overlap_count(query_tokens, item["title"]))
        raw_difficulty = document.get("difficulty")
        try:
            difficulty = float(raw_difficulty) if raw_difficulty is not None else None
        except (TypeError, ValueError):
            difficulty = None
        key = document["id"]
        if key in seen:
            continue
        seen.add(key)
        source = {
            "question_id": document["id"],
            "question_title": document["title"] or "未命名题目",
            "point_title": point_link["title"],
            "difficulty": difficulty,
        }
        matched_weak_point = mastery_by_uid.get(point_link["uid"])
        if matched_weak_point:
            source["mastery"] = matched_weak_point["score"]
        sources.append(source)

    return {
        "context": "\n\n".join(context_parts),
        "sources": sources[:8],
        "weak_points": [{key: value for key, value in item.items() if key != "uid"} for item in weak_points],
        "rag_status": "retrieved" if selected else ("no_match" if documents else "empty_question_bank"),
    }
