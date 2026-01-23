"""
LaTeX知识图谱抽取器
基于规则 + 可选LLM对节点进行合并与标题精炼
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)


COMMENT_RE = re.compile(r'(?<!\\)%.*$')
NEWTCLISTING_RE = re.compile(r'\\newtcblisting\s*\{')
BEGIN_RE = re.compile(r'\\begin\{([^\}]+)\}')
END_RE = re.compile(r'\\end\{([^\}]+)\}')
CHAPTER_SECTION_RE = re.compile(r'\\(chapter|section|subsection)\*?\{((?:[^{}]|\{[^{}]*\})*)\}')

STYLE_BLOCK_PATTERNS = [
    r'\\tcbset\s*\{.*?\}\s*',
    r'\\definecolor\s*\{.*?\}\s*\{.*?\}\s*\{.*?\}\s*',
    r'\\lstdefinestyle\s*\{.*?\}\s*\{.*?\}\s*',
    r'\\newcommand\s*\{.*?\}\s*\{.*?\}\s*',
    r'\\renewcommand\s*\{.*?\}\s*\{.*?\}\s*',
]

LATEX_LAYOUT_CMD_RE = re.compile(
    r'(\\noindent|\\par|\\smallskip|\\medskip|\\bigskip|\\vspace\*?\{[^}]*\}|'
    r'\\hspace\*?\{[^}]*\}|\\newline|\\\\)'
)
MYTEXT_TYPE_RE = re.compile(r'^mytext\d+$')


@dataclass
class ExtractOptions:
    do_llm_title_refine: bool = True
    do_llm_text_merge: bool = True
    merge_soft_envs: Tuple[str, ...] = ("quotation", "quote")
    llm_max_desc_chars: int = 4000
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None

    def __post_init__(self):
        if not self.llm_model:
            self.llm_model = os.getenv("LLM_MODEL_NAME") or os.getenv("LLM_MODEL") or "gpt-5-nano"
        if not self.llm_base_url:
            self.llm_base_url = os.getenv("LLM_BASE_URL") or os.getenv("LLM_API_URL") or "https://api.nuwaapi.com/v1"
        if not self.llm_api_key:
            self.llm_api_key = os.getenv("LLM_API_KEY", "")


class LatexKGExtractor:
    """LaTeX知识图谱抽取器（替换原有解析逻辑）"""

    def extract_from_file(self, latex_file_path: str, options: Optional[ExtractOptions] = None) -> Dict:
        options = options or ExtractOptions()
        text = self._read_text(latex_file_path)

        tex_clean = strip_comments(text)
        tex_clean = remove_newtcblisting_defs(tex_clean)
        tex_clean = remove_style_settings(tex_clean)

        nodes = extract_kg(tex_clean)
        nodes = prune_empty_text_nodes(nodes, min_chars=8)
        nodes = merge_soft_env_between_text(nodes, soft_envs=set(options.merge_soft_envs))
        nodes = merge_mytext_into_prev_any(nodes)

        if options.do_llm_text_merge:
            nodes = llm_merge_text_into_prev(
                nodes,
                base_url=options.llm_base_url,
                chat_model=options.llm_model,
                api_key=options.llm_api_key,
                max_desc_chars=options.llm_max_desc_chars,
                allowed_prev_types=("text", "CoqCmd", "CoqLtac", "CoqExpr", "ex"),
            )

        if options.do_llm_title_refine:
            refined = refine_titles_with_llm(
                nodes,
                base_url=options.llm_base_url,
                chat_model=options.llm_model,
                api_key=options.llm_api_key,
            )
            logger.info("✅ LLM标题精炼: %s", refined)

        graph = self._build_graph(nodes)
        stats = self._generate_statistics(graph["nodes"], graph["edges"])

        result = {
            "graph": graph,
            "statistics": stats,
            "metadata": {
                "total_nodes": len(graph["nodes"]),
                "total_edges": len(graph["edges"]),
            },
            "latex_data": {
                "document_info": {},
                "statistics": {
                    "total_chapters": stats["nodes_by_type"].get("chapter", 0),
                    "total_equations": stats["nodes_by_type"].get("equation", 0),
                    "total_figures": stats["nodes_by_type"].get("figure", 0),
                },
            },
        }
        return result

    def to_visualization_data(self, kg_data: Dict) -> Dict:
        nodes = kg_data.get("graph", {}).get("nodes", [])
        edges = kg_data.get("graph", {}).get("edges", [])
        graph = nx.DiGraph()
        for node in nodes:
            graph.add_node(node["id"])
        for edge in edges:
            graph.add_edge(edge["source"], edge["target"])

        try:
            pos = nx.spring_layout(graph, k=2, iterations=50)
        except Exception:
            pos = {}

        vis_nodes = []
        for node in nodes:
            node_id = node["id"]
            node_copy = dict(node)
            if node_id in pos:
                node_copy["x"] = float(pos[node_id][0] * 500)
                node_copy["y"] = float(pos[node_id][1] * 500)
            node_copy["size"] = max(10, 30 - int(node.get("level", 0)) * 5)
            node_copy["color"] = _node_color(node.get("type", ""))
            vis_nodes.append(node_copy)

        return {"nodes": vis_nodes, "edges": edges}

    def build_viz_json(self, kg_data: Dict) -> Dict:
        nodes = kg_data.get("graph", {}).get("nodes", [])
        if not nodes:
            nodes = kg_data.get("knowledge_graph", {}).get("nodes", [])
        return build_viz_json_from_nodes(nodes)

    def _read_text(self, latex_file_path: str) -> str:
        with open(latex_file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _build_graph(self, nodes: List[Dict]) -> Dict:
        graph_nodes = []
        edges = []
        for n in nodes:
            node = {
                "id": n["id"],
                "label": n.get("title", ""),
                "title": n.get("title", ""),
                "type": n.get("type", ""),
                "level": n.get("level", 0),
                "content": n.get("description", ""),
                "parent_id": n.get("parent_id"),
            }
            graph_nodes.append(node)

        for n in nodes:
            if n.get("parent_id"):
                edges.append(
                    {"source": n["parent_id"], "target": n["id"], "relation": "contains"}
                )

        return {"nodes": graph_nodes, "edges": edges}

    def _generate_statistics(self, nodes: List[Dict], edges: List[Dict]) -> Dict:
        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "nodes_by_type": {},
            "nodes_by_level": {},
            "max_depth": 0,
        }
        for node in nodes:
            ntype = node.get("type", "")
            level = int(node.get("level", 0))
            stats["nodes_by_type"][ntype] = stats["nodes_by_type"].get(ntype, 0) + 1
            stats["nodes_by_level"][level] = stats["nodes_by_level"].get(level, 0) + 1
            stats["max_depth"] = max(stats["max_depth"], level)
        return stats


def strip_comments(s: str) -> str:
    return "\n".join(COMMENT_RE.sub("", line) for line in s.splitlines())


def _extract_balanced_brace_arg(s: str, start_idx: int):
    if start_idx >= len(s) or s[start_idx] != "{":
        return None, start_idx
    depth = 0
    out = []
    i = start_idx
    while i < len(s):
        ch = s[i]
        if ch == "{":
            depth += 1
            if depth > 1:
                out.append(ch)
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(out), i + 1
            out.append(ch)
        else:
            out.append(ch)
        i += 1
    return "".join(out), i


def remove_newtcblisting_defs(s: str) -> str:
    """删除形如 \\newtcblisting{mytext53}{...} 的整段定义"""
    out = []
    i = 0
    n = len(s)
    while i < n:
        m = NEWTCLISTING_RE.search(s, i)
        if not m:
            out.append(s[i:])
            break
        out.append(s[i:m.start()])
        j = m.end() - 1
        while j < n and s[j] != "{":
            j += 1
        if j >= n:
            break
        _, j = _extract_balanced_brace_arg(s, j)
        while j < n and s[j].isspace():
            j += 1
        if j < n and s[j] == "{":
            _, j = _extract_balanced_brace_arg(s, j)
        i = j
    return "".join(out)


def remove_style_settings(s: str) -> str:
    for pat in STYLE_BLOCK_PATTERNS:
        s = re.sub(pat, "", s, flags=re.DOTALL)
    return s


def extract_first_cmd_arg(text: str, cmd: str):
    m = re.search(r"\\" + re.escape(cmd) + r"\s*\{", text)
    if not m:
        return None
    brace_start = m.end() - 1
    arg, _ = _extract_balanced_brace_arg(text, brace_start)
    return arg


def latex_to_plain(s: str) -> str:
    if s is None:
        return ""
    s = re.sub(r"\\lstinline\{([^}]*)\}", r"\1", s)
    for cmd in ["textbf", "textit", "emph", "underline"]:
        s = re.sub(r"\\" + cmd + r"\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\textcolor\{[^}]*\}\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", s)
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_env_title(env_content: str, env_name: str) -> str:
    t = extract_first_cmd_arg(env_content, "textbf")
    if t:
        pt = latex_to_plain(t)
        return pt[:80].strip() or env_name
    for line in env_content.splitlines():
        pl = latex_to_plain(line)
        if pl:
            pl = re.split(r"[。\.:\\n]", pl)[0].strip()
            return pl[:80] if pl else env_name
    return env_name


def split_into_sections(full_text: str):
    matches = list(CHAPTER_SECTION_RE.finditer(full_text))
    sections = []
    for idx, m in enumerate(matches):
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
        chunk = full_text[start:end]
        header_line = chunk.splitlines(True)[0]
        cmd = m.group(1)
        title_raw = m.group(2)
        body = chunk[len(header_line) :]
        sections.append((cmd, title_raw, header_line, body))
    return sections


def split_blocks_by_env(text: str):
    blocks = []
    i = 0
    n = len(text)
    while i < n:
        b = BEGIN_RE.search(text, i)
        if not b:
            if i < n:
                blocks.append(("text", None, text[i:]))
            break

        env = b.group(1).strip()
        if env == "document":
            blocks.append(("text", None, text[i : b.end()]))
            i = b.end()
            continue

        if b.start() > i:
            blocks.append(("text", None, text[i : b.start()]))

        depth = 1
        j = b.end()
        while j < n:
            b2 = BEGIN_RE.search(text, j)
            e2 = END_RE.search(text, j)
            if not e2 and not b2:
                blocks.append(("env", env, text[b.start() :]))
                i = n
                break

            next_pos = n
            next_is_begin = False
            if b2:
                next_pos = b2.start()
                next_is_begin = True
            if e2 and (e2.start() < next_pos):
                next_pos = e2.start()
                next_is_begin = False

            if next_is_begin:
                if b2.group(1).strip() == env:
                    depth += 1
                j = b2.end()
            else:
                if e2.group(1).strip() == env:
                    depth -= 1
                    j = e2.end()
                    if depth == 0:
                        blocks.append(("env", env, text[b.start() : j]))
                        i = j
                        break
                else:
                    j = e2.end()
        else:
            i = n
    return blocks


def build_nodes_for_blocks(blocks, level, path_prefix, parent_id, keep_text_children=True):
    nodes = []
    sibling_idx = 0
    for kind, env, content in blocks:
        sibling_idx += 1
        node_id = f"L{level}_" + "_".join(path_prefix + [str(sibling_idx)])

        if kind == "text":
            if not keep_text_children:
                continue
            nodes.append(
                {
                    "id": node_id,
                    "level": level,
                    "parent_id": parent_id,
                    "title": "text",
                    "type": "text",
                    "description": content,
                }
            )
            continue

        env_name = env
        title = extract_env_title(content, env_name)
        nodes.append(
            {
                "id": node_id,
                "level": level,
                "parent_id": parent_id,
                "title": title,
                "type": env_name,
                "description": content,
            }
        )

        inner = content
        first_nl = inner.find("\n")
        inner_body = inner[first_nl + 1 :] if first_nl != -1 else ""
        ends = list(END_RE.finditer(inner_body))
        if ends and ends[-1].group(1).strip() == env_name:
            inner_body = inner_body[: ends[-1].start()]

        child_blocks = split_blocks_by_env(inner_body)
        if child_blocks:
            nodes.extend(
                build_nodes_for_blocks(
                    child_blocks,
                    level=level + 1,
                    path_prefix=path_prefix + [str(sibling_idx)],
                    parent_id=node_id,
                    keep_text_children=False,
                )
            )
    return nodes


def extract_kg(tex_clean: str):
    sections = split_into_sections(tex_clean)
    nodes = []
    for s_idx, (cmd, title_raw, header_line, body) in enumerate(sections, start=1):
        sec_id = f"L1_{s_idx}"
        sec_title = latex_to_plain(title_raw)
        nodes.append(
            {
                "id": sec_id,
                "level": 1,
                "parent_id": None,
                "title": sec_title,
                "type": cmd,
                "description": header_line,
            }
        )
        nodes.extend(
            build_nodes_for_blocks(
                split_blocks_by_env(body),
                2,
                [str(s_idx)],
                sec_id,
                keep_text_children=True,
            )
        )
    return nodes


def _id_key(n):
    parts = n["id"].split("_")
    lvl = int(parts[0][1:])
    path = tuple(int(x) for x in parts[1:])
    return (lvl, *path)


def is_meaningful_text(desc: str, min_chars: int = 8) -> bool:
    if desc is None:
        return False
    s = LATEX_LAYOUT_CMD_RE.sub("", desc)
    s = re.sub(r"\s+", "", s)
    return len(s) >= min_chars


def prune_empty_text_nodes(nodes, min_chars: int = 8):
    out = []
    for n in nodes:
        if n.get("type") == "text":
            if not is_meaningful_text(n.get("description", ""), min_chars=min_chars):
                continue
        out.append(n)
    return out


def merge_soft_env_between_text(nodes, soft_envs):
    nodes_sorted = sorted(nodes, key=_id_key)
    children = {}
    for n in nodes_sorted:
        children.setdefault((n.get("parent_id"), n.get("level")), []).append(n)

    id2 = {n["id"]: n for n in nodes_sorted}
    drop = set()

    for (_pid, _lvl), arr in children.items():
        i = 0
        while i + 2 < len(arr):
            a, b, c = arr[i], arr[i + 1], arr[i + 2]
            if a.get("type") == "text" and b.get("type") in soft_envs and c.get("type") == "text":
                id2[a["id"]]["description"] = (
                    (id2[a["id"]].get("description") or "")
                    + "\n\n"
                    + (id2[b["id"]].get("description") or "")
                    + "\n\n"
                    + (id2[c["id"]].get("description") or "")
                )
                drop.add(b["id"])
                drop.add(c["id"])
                i += 3
            else:
                i += 1

    return [n for n in nodes_sorted if n["id"] not in drop]


def merge_mytext_into_prev_any(nodes):
    nodes_sorted = sorted(nodes, key=_id_key)
    groups = {}
    for n in nodes_sorted:
        groups.setdefault((n.get("parent_id"), n.get("level")), []).append(n)

    id2 = {n["id"]: n for n in nodes_sorted}
    drop = set()

    for (_pid, _lvl), arr in groups.items():
        for i in range(1, len(arr)):
            cur = arr[i]
            prev = arr[i - 1]
            if cur["id"] in drop:
                continue
            if MYTEXT_TYPE_RE.match(cur.get("type", "")):
                id2[prev["id"]]["description"] = (
                    (id2[prev["id"]].get("description") or "")
                    + "\n\n"
                    + (id2[cur["id"]].get("description") or "")
                )
                drop.add(cur["id"])

    return [n for n in nodes_sorted if n["id"] not in drop]


def llm_merge_text_into_prev(
    nodes,
    base_url,
    chat_model,
    api_key,
    max_desc_chars=4000,
    allowed_prev_types=("text", "CoqCmd", "CoqLtac", "CoqExpr", "ex"),
    sleep_s=0.02,
):
    if not api_key:
        logger.info("ℹ️ Skip LLM merge: LLM_API_KEY not set")
        return nodes

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    system = (
        "你是知识笔记节点的合并判定器。\n"
        "给定同一 parent、同一 level 的两个相邻节点 prev(前) 和 cur(后)。\n"
        "你只回答：cur 是否应该合并进 prev。\n\n"
        "硬约束：\n"
        "1) 只有当 cur.type == \"text\" 时才允许 merge=true。\n"
        "2) 如果 prev.type 不在允许集合（text/CoqCmd/CoqLtac/CoqExpr/ex），必须 merge=false。\n"
        "3) 如果 cur.description 只有空白/\\noindent/排版命令，必须 merge=true。\n\n"
        "合并标准（非常保守）：\n"
        "- merge=true：cur 明确是在延续 prev 的同一微主题。\n"
        "- merge=false：cur 开启新概念/新命题/新定义/新例子/新习题/新证明步骤/新小节。\n"
        "默认 merge=false，除非你非常确定应合并。\n\n"
        "只输出 JSON：{\"merge\": true/false}\n"
    )

    nodes_sorted = sorted(nodes, key=_id_key)
    id2 = {n["id"]: n for n in nodes_sorted}

    groups = {}
    for n in nodes_sorted:
        groups.setdefault((n.get("parent_id"), n.get("level")), []).append(n)

    drop = set()

    layout_re = re.compile(r"(\\noindent|\\par|\\smallskip|\\medskip|\\bigskip|\\newline|\\\\)")

    def is_trivial_text(desc: str) -> bool:
        if not desc:
            return True
        s = layout_re.sub("", desc)
        s = re.sub(r"\s+", "", s)
        return len(s) == 0

    for (_pid, _lvl), arr in groups.items():
        prev_idx = None
        for i in range(len(arr)):
            cur = arr[i]
            if cur["id"] in drop:
                continue

            if prev_idx is None:
                prev_idx = i
                continue

            prev = arr[prev_idx]
            if prev["id"] in drop:
                prev_idx = i
                continue

            if cur.get("type") != "text":
                prev_idx = i
                continue

            if prev.get("type") not in allowed_prev_types:
                prev_idx = i
                continue

            if is_trivial_text(cur.get("description", "")):
                id2[prev["id"]]["description"] = (
                    (id2[prev["id"]].get("description") or "")
                    + "\n\n"
                    + (id2[cur["id"]].get("description") or "")
                )
                drop.add(cur["id"])
                continue

            payload = {
                "prev": {
                    "id": prev["id"],
                    "type": prev.get("type", ""),
                    "title": prev.get("title", ""),
                    "desc": (prev.get("description", "") or "")[:max_desc_chars],
                },
                "cur": {
                    "id": cur["id"],
                    "type": cur.get("type", ""),
                    "title": cur.get("title", ""),
                    "desc": (cur.get("description", "") or "")[:max_desc_chars],
                },
            }

            try:
                resp = client.chat.completions.create(
                    model=chat_model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )
                out = json.loads(resp.choices[0].message.content)
                merge = bool(out.get("merge", False))

                if merge:
                    id2[prev["id"]]["description"] = (
                        (id2[prev["id"]].get("description") or "")
                        + "\n\n"
                        + (id2[cur["id"]].get("description") or "")
                    )
                    drop.add(cur["id"])
                    time.sleep(sleep_s)
                else:
                    prev_idx = i

            except Exception as e:
                logger.warning("LLM merge failed: %s %s %s", prev["id"], cur["id"], e)
                prev_idx = i

    return [n for n in nodes_sorted if n["id"] not in drop]


def refine_titles_with_llm(nodes, base_url, chat_model, api_key):
    if not api_key:
        logger.info("ℹ️ Skip LLM refine: LLM_API_KEY not set")
        return 0

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    latex_noise = re.compile(r"(\\[a-zA-Z]+|\{|\}|Colorbox|lstinline|begin\{|end\{)")

    def should_refine(n):
        t = (n.get("title") or "").strip()
        if n.get("type") == "text" and t == "text":
            return True
        if len(t) > 30:
            return True
        if latex_noise.search(t):
            return True
        return False

    def validate_title(title: str) -> str:
        title = re.sub(r"\s+", " ", (title or "")).strip()
        title = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", title).strip()
        title = title.replace("{", "").replace("}", "").strip()
        if len(title) > 40:
            title = title[:40].rstrip()
        return title

    system = (
        "你是知识图谱节点标题生成器。只需要输出一个更好的 title。\n"
        "要求：\n"
        "- 输出 JSON：{\"title\": \"...\"}\n"
        "- title 必须是简短的名词短语（中文），≤ 20 字\n"
        "- 不要包含 LaTeX 命令（如 \\Colorbox, \\lstinline 等）\n"
        "- 不要以口语开头（例如：在Coq中/例如/我们可以）\n"
        "- 不要胡编不存在的概念，只能根据给定 description 归纳命名\n"
    )

    id_to = {n["id"]: n for n in nodes}
    updated = 0

    for n in nodes:
        if not should_refine(n):
            continue
        pid = n.get("parent_id")
        parent_title = id_to.get(pid, {}).get("title") if pid else ""
        payload = {
            "type": n.get("type", ""),
            "level": n.get("level", ""),
            "parent_title": parent_title,
            "current_title": n.get("title", ""),
            "description_snippet": (n.get("description", "") or "")[:2000],
        }

        try:
            resp = client.chat.completions.create(
                model=chat_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            out = json.loads(resp.choices[0].message.content)
            new_title = validate_title(out.get("title", ""))
            if new_title and new_title != n.get("title"):
                n["title"] = new_title
                updated += 1
            time.sleep(0.02)
        except Exception as e:
            logger.warning("LLM refine failed: %s %s", n.get("id"), e)

    return updated


def _node_color(node_type: str) -> str:
    type_colors = {
        "document": "#1890ff",
        "chapter": "#52c41a",
        "section": "#faad14",
        "subsection": "#722ed1",
        "subsubsection": "#eb2f96",
        "equation": "#13c2c2",
        "figure": "#fa8c16",
    }
    return type_colors.get(node_type, "#d9d9d9")


def build_viz_json_from_nodes(nodes: List[Dict]) -> Dict:
    vroot_id = "V_ROOT"
    vroot_title = "LaTeX 知识图谱"
    all_nodes = []
    all_links = []

    all_nodes.append(
        {
            "id": vroot_id,
            "title": vroot_title,
            "level": 0,
            "type": "root",
            "description": "",
            "parent_id": None,
            "is_folder": True,
        }
    )

    id_set = {vroot_id}
    for item in nodes:
        nid = item.get("id")
        if not nid:
            continue
        try:
            level = int(item.get("level", 5))
        except Exception:
            level = 5
        node = {
            "id": str(nid),
            "level": level,
            "parent_id": item.get("parent_id"),
            "title": item.get("label") or item.get("title") or "",
            "type": item.get("type", "unknown") or "unknown",
            "description": item.get("description") or item.get("content", "") or "",
        }
        pid = node.get("parent_id")
        if pid in [None, "", "null"]:
            node["parent_id"] = None
        else:
            node["parent_id"] = str(pid)
        node["is_folder"] = node["type"] == "section"
        all_nodes.append(node)
        id_set.add(node["id"])

    for node in all_nodes:
        nid = node["id"]
        if nid == vroot_id:
            continue
        pid = node.get("parent_id")
        if pid is None:
            all_links.append({"source": vroot_id, "target": nid})
        elif pid not in id_set:
            node["parent_id"] = vroot_id
            all_links.append({"source": vroot_id, "target": nid})
        else:
            all_links.append({"source": pid, "target": nid})

    return {"nodes": all_nodes, "links": all_links}
