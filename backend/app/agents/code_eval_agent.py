# """
# Code Evaluation Agent
# ======================
# Pipeline (runs every time a submission is evaluated):

#   ┌──────────────────────────────────────────────────────────────────┐
#   │                    Code Evaluation Agent                         │
#   │                                                                  │
#   │  ① Static Analyser  — language-aware heuristic rule engine      │
#   │     • Naming conventions (variables, functions, classes)         │
#   │     • Cyclomatic complexity (nested depth counting)              │
#   │     • Magic numbers / hardcoded strings detection                │
#   │     • Dead code / unused variable patterns                       │
#   │     • Security patterns (SQL injection, eval, exec risks)        │
#   │     • Documentation coverage (docstrings, comments ratio)        │
#   │     • Code duplication heuristics (block similarity)             │
#   │                                                                  │
#   │  ② Metrics Extractor — LOC, comment ratio, complexity           │
#   │                                                                  │
#   │  ③ Groq LLM Analysis — llama-3.3-70b-versatile                 │
#   │     • Deep correctness review (logic, edge cases, output)        │
#   │     • Quality narrative feedback                                 │
#   │     • Corrected / improved code version                          │
#   │     • Learning points personalised to student profile            │
#   │     • Suggested resources per weakness                           │
#   │                                                                  │
#   │  ④ Score Calculator — weighted blend of all dimensions          │
#   │                                                                  │
#   │  ⑤ Persistence — saves evaluation + history entry               │
#   └──────────────────────────────────────────────────────────────────┘
# """

# import re
# import json
# import time
# import httpx
# from datetime import datetime, timezone
# from typing import List, Dict, Optional, Tuple, Any

# from sqlalchemy.orm import Session

# from app.models.user import User, LearningProfile
# from app.models.code_eval import (
#     CodeSubmission, CodeEvaluation, EvalHistoryEntry,
#     Language, EvalStatus, SeverityLevel
# )
# from app.core.config import settings


# GROQ_MODEL   = "llama-3.3-70b-versatile"
# GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# MAX_TOKENS   = 2500


# # ══════════════════════════════════════════════════════════════════════════════
# #  STATIC ANALYSER — pure Python, no external tools needed
# # ══════════════════════════════════════════════════════════════════════════════

# class StaticAnalyser:
#     """
#     Language-aware heuristic rule engine.
#     Produces a list of Issue dicts without running the code.
#     """

#     def analyse(self, code: str, language: Language) -> Tuple[List[Dict], Dict]:
#         """
#         Returns (issues, metrics).
#         issues : list of Issue dicts
#         metrics: {lines_of_code, comment_ratio, cyclomatic_complexity}
#         """
#         lines       = code.splitlines()
#         issues      = []
#         issue_id    = 1

#         def add(line, severity, category, message, suggestion):
#             nonlocal issue_id
#             issues.append({
#                 "id": issue_id, "line": line,
#                 "severity": severity, "category": category,
#                 "message": message, "suggestion": suggestion
#             })
#             issue_id += 1

#         # ── Metrics ───────────────────────────────────────────────────────────
#         total_lines   = len(lines)
#         code_lines    = [l for l in lines if l.strip() and not self._is_comment(l, language)]
#         comment_lines = [l for l in lines if self._is_comment(l, language)]
#         loc           = len(code_lines)
#         comment_ratio = len(comment_lines) / max(total_lines, 1)

#         # Cyclomatic complexity: count decision points
#         decision_keywords = r'\b(if|elif|else|for|while|except|case|when|switch|and|or|&&|\|\|)\b'
#         cyclomatic = 1 + len(re.findall(decision_keywords, code))

#         # ── Universal checks ──────────────────────────────────────────────────

#         # 1. Function / method length
#         func_pattern = self._func_pattern(language)
#         if func_pattern:
#             for m in re.finditer(func_pattern, code, re.MULTILINE):
#                 start_line = code[:m.start()].count('\n') + 1
#                 # Count body lines (rough: from def to next def or end)
#                 body_start = code[:m.end()].count('\n')
#                 next_func  = re.search(func_pattern, code[m.end():], re.MULTILINE)
#                 body_end   = (body_start + code[m.end():next_func.start()].count('\n')
#                               if next_func else total_lines)
#                 body_len   = body_end - body_start
#                 if body_len > 40:
#                     add(start_line, SeverityLevel.WARNING, "complexity",
#                         f"Function starting at line {start_line} is {body_len} lines long (>40).",
#                         "Break it into smaller, single-responsibility functions.")

#         # 2. Deep nesting (4+ levels)
#         for i, line in enumerate(lines, 1):
#             indent = len(line) - len(line.lstrip())
#             spaces_per_level = 4 if language != Language.GO else 1
#             level = indent // max(spaces_per_level, 1)
#             if level >= 4 and line.strip():
#                 add(i, SeverityLevel.WARNING, "complexity",
#                     f"Line {i}: deeply nested code (indent level {level}).",
#                     "Extract inner logic into a helper function to reduce nesting.")
#                 break  # one per submission is enough

#         # 3. Magic numbers
#         magic_pattern = r'(?<!["\'\w])(?<!\.)\b([2-9]\d{2,}|\d{4,})\b(?![\"\'])'
#         for m in re.finditer(magic_pattern, code):
#             line_no = code[:m.start()].count('\n') + 1
#             if not any(kw in lines[line_no-1] for kw in ['#', '//', '/*', '*', 'range', 'size', 'len']):
#                 add(line_no, SeverityLevel.INFO, "quality",
#                     f"Magic number `{m.group()}` at line {line_no}.",
#                     "Replace magic numbers with named constants for readability.")
#                 break  # report once

#         # 4. Print/console in production code
#         debug_patterns = {
#             Language.PYTHON: r'\bprint\s*\(',
#             Language.JAVASCRIPT: r'\bconsole\.(log|warn|error)\s*\(',
#             Language.TYPESCRIPT: r'\bconsole\.(log|warn|error)\s*\(',
#             Language.JAVA: r'System\.out\.print',
#             Language.CPP: r'\bcout\s*<<',
#         }
#         dp = debug_patterns.get(language)
#         debug_count = len(re.findall(dp, code)) if dp else 0
#         if debug_count > 2:
#             add(None, SeverityLevel.INFO, "quality",
#                 f"{debug_count} debug print/console statements found.",
#                 "Remove debug statements before production. Consider a logging framework.")

#         # 5. Security checks
#         dangerous = {
#             Language.PYTHON: [
#                 (r'\beval\s*\(',      "Use of `eval()` is dangerous — can execute arbitrary code.",
#                  "Never use eval() on untrusted input. Use ast.literal_eval() for data parsing."),
#                 (r'\bexec\s*\(',      "Use of `exec()` is a security risk.",
#                  "Avoid exec() — refactor logic to avoid dynamic code execution."),
#                 (r'input\s*\(.*sql',  "Potential SQL injection via user input.",
#                  "Use parameterised queries (e.g., cursor.execute(sql, params))."),
#                 (r'__import__\s*\(',  "`__import__()` is a code smell and security risk.",
#                  "Use standard import statements instead of __import__()."),
#             ],
#             Language.JAVASCRIPT: [
#                 (r'\beval\s*\(',       "Use of `eval()` is a critical security risk.",
#                  "Never use eval(). Use JSON.parse() for data, or restructure logic."),
#                 (r'innerHTML\s*=',    "Direct innerHTML assignment risks XSS attacks.",
#                  "Use textContent for text, or sanitise HTML before inserting."),
#                 (r'document\.write\(', "`document.write()` is deprecated and dangerous.",
#                  "Use DOM manipulation methods like createElement and appendChild."),
#             ],
#             Language.JAVA: [
#                 (r'Runtime\.getRuntime\(\)\.exec', "Runtime.exec() is a security risk.",
#                  "Avoid executing system commands. Use ProcessBuilder with a whitelist."),
#             ],
#         }
#         for pattern, msg, suggestion in dangerous.get(language, []):
#             if re.search(pattern, code):
#                 add(None, SeverityLevel.ERROR, "security", msg, suggestion)

#         # 6. Documentation
#         if language == Language.PYTHON:
#             funcs   = re.findall(r'def\s+\w+\s*\(', code)
#             docs    = re.findall(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', code)
#             classes = re.findall(r'class\s+\w+', code)
#             if len(funcs) > 2 and len(docs) == 0:
#                 add(None, SeverityLevel.WARNING, "documentation",
#                     f"{len(funcs)} functions found with no docstrings.",
#                     'Add docstrings: """Brief description, Args, Returns."""')
#         elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
#             funcs = re.findall(r'function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\(', code)
#             jsdoc = re.findall(r'/\*\*[\s\S]*?\*/', code)
#             if len(funcs) > 2 and len(jsdoc) == 0:
#                 add(None, SeverityLevel.WARNING, "documentation",
#                     f"{len(funcs)} functions with no JSDoc comments.",
#                     "Add JSDoc: /** @param {type} name - description @returns {type} */")
#         elif language == Language.JAVA:
#             methods = re.findall(r'(public|private|protected)\s+\w+\s+\w+\s*\(', code)
#             javadoc = re.findall(r'/\*\*[\s\S]*?\*/', code)
#             if len(methods) > 2 and len(javadoc) == 0:
#                 add(None, SeverityLevel.WARNING, "documentation",
#                     f"{len(methods)} methods with no Javadoc.",
#                     "Add Javadoc: /** @param name desc @return desc */")

#         # 7. Python-specific naming
#         if language == Language.PYTHON:
#             # Class names should be PascalCase
#             for m in re.finditer(r'\bclass\s+([a-z][a-zA-Z0-9_]*)\b', code):
#                 line_no = code[:m.start()].count('\n') + 1
#                 add(line_no, SeverityLevel.WARNING, "naming",
#                     f"Class `{m.group(1)}` should use PascalCase (e.g. `{m.group(1).capitalize()}`).",
#                     "Python convention: class names use PascalCase (PEP 8).")
#                 break
#             # Single-letter variables (except i, j, k, x, y, n)
#             for m in re.finditer(r'\b([a-wz])\s*=\s*(?!\s)', code):
#                 line_no = code[:m.start()].count('\n') + 1
#                 add(line_no, SeverityLevel.INFO, "naming",
#                     f"Single-letter variable `{m.group(1)}` at line {line_no} hurts readability.",
#                     "Use descriptive names like `count`, `index`, `result` instead.")
#                 break

#         # 8. Long lines
#         for i, line in enumerate(lines, 1):
#             if len(line) > 100:
#                 add(i, SeverityLevel.INFO, "style",
#                     f"Line {i} is {len(line)} characters long (>100).",
#                     "Keep lines under 100 characters for readability. Break long expressions.")
#                 break

#         # 9. TODO / FIXME / HACK left in code
#         for i, line in enumerate(lines, 1):
#             if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', line):
#                 add(i, SeverityLevel.INFO, "quality",
#                     f"Unresolved TODO/FIXME at line {i}: `{line.strip()[:60]}`.",
#                     "Resolve or track TODOs in an issue tracker before submitting.")

#         # 10. Empty except blocks (Python)
#         if language == Language.PYTHON:
#             for m in re.finditer(r'except[^:]*:\s*\n\s*(pass\s*\n|#.*\n)', code):
#                 line_no = code[:m.start()].count('\n') + 1
#                 add(line_no, SeverityLevel.WARNING, "logic",
#                     f"Empty or bare except block at line {line_no} silences all errors.",
#                     "Always handle specific exceptions and log or re-raise them.")

#         metrics = {
#             "lines_of_code":         loc,
#             "comment_ratio":         round(comment_ratio, 3),
#             "cyclomatic_complexity": cyclomatic,
#         }
#         return issues, metrics

#     def _is_comment(self, line: str, language: Language) -> bool:
#         s = line.strip()
#         if language == Language.PYTHON:
#             return s.startswith('#')
#         if language in (Language.JAVASCRIPT, Language.TYPESCRIPT,
#                         Language.JAVA, Language.CPP, Language.C, Language.GO, Language.RUST):
#             return s.startswith('//') or s.startswith('*') or s.startswith('/*')
#         return False

#     def _func_pattern(self, language: Language) -> Optional[str]:
#         patterns = {
#             Language.PYTHON:     r'^\s*def\s+\w+\s*\(',
#             Language.JAVASCRIPT: r'^\s*(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\()',
#             Language.TYPESCRIPT: r'^\s*(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\()',
#             Language.JAVA:       r'^\s*(?:public|private|protected|static)\s+\w[\w<>[\]]*\s+\w+\s*\(',
#             Language.CPP:        r'^\w[\w:*&<>]*\s+\w+\s*\(',
#             Language.GO:         r'^\s*func\s+\w+\s*\(',
#             Language.RUST:       r'^\s*(?:pub\s+)?fn\s+\w+\s*\(',
#         }
#         return patterns.get(language)


# # ══════════════════════════════════════════════════════════════════════════════
# #  SCORE CALCULATOR
# # ══════════════════════════════════════════════════════════════════════════════

# def _calculate_static_scores(issues: List[Dict], metrics: Dict, code: str) -> Dict[str, float]:
#     """
#     Derive initial dimension scores from static analysis.
#     LLM will refine these further.
#     """
#     loc          = metrics.get("lines_of_code", 1) or 1
#     comment_ratio= metrics.get("comment_ratio", 0)
#     cc           = metrics.get("cyclomatic_complexity", 1)

#     # Count issues by severity
#     criticals = sum(1 for i in issues if i["severity"] == SeverityLevel.CRITICAL)
#     errors    = sum(1 for i in issues if i["severity"] == SeverityLevel.ERROR)
#     warnings  = sum(1 for i in issues if i["severity"] == SeverityLevel.WARNING)
#     infos     = sum(1 for i in issues if i["severity"] == SeverityLevel.INFO)

#     # Style: start at 100, deduct per style issue
#     style_issues = [i for i in issues if i["category"] == "style"]
#     style = max(0.0, 100 - len(style_issues) * 10 - infos * 3)

#     # Security: heavily penalise
#     sec_issues = [i for i in issues if i["category"] == "security"]
#     security = max(0.0, 100 - criticals * 40 - errors * 20 - len(sec_issues) * 15)

#     # Quality: naming, magic numbers, debug prints
#     qual_issues = [i for i in issues if i["category"] in ("quality", "naming")]
#     quality = max(0.0, 100 - len(qual_issues) * 12 - warnings * 5)

#     # Documentation
#     documentation = min(100.0, 40 + comment_ratio * 200 +
#                         (30 if len([i for i in issues if i["category"] == "documentation"]) == 0 else 0))

#     # Efficiency: penalise very high cyclomatic complexity
#     if cc <= 5:     efficiency = 90.0
#     elif cc <= 10:  efficiency = 75.0
#     elif cc <= 20:  efficiency = 55.0
#     else:           efficiency = max(20.0, 100 - cc * 2)

#     # Correctness starts neutral — LLM will give the real score
#     correctness = 60.0

#     return {
#         "style":         round(min(style,        100), 1),
#         "security":      round(min(security,     100), 1),
#         "quality":       round(min(quality,      100), 1),
#         "documentation": round(min(documentation,100), 1),
#         "efficiency":    round(min(efficiency,   100), 1),
#         "correctness":   round(correctness,           1),
#     }


# def _blend_scores(static: Dict[str, float], llm: Dict[str, float]) -> Dict[str, float]:
#     """Blend static analysis scores with LLM-provided scores (LLM gets 60% weight)."""
#     dims = ["correctness", "quality", "efficiency", "security", "style", "documentation"]
#     blended = {}
#     for d in dims:
#         s_val = static.get(d, 50.0)
#         l_val = llm.get(d, s_val)   # fallback to static if LLM doesn't provide
#         blended[d] = round(s_val * 0.40 + l_val * 0.60, 1)

#     weights = {"correctness": 0.30, "quality": 0.20, "efficiency": 0.20,
#                "security": 0.15, "style": 0.10, "documentation": 0.05}
#     overall = sum(blended[d] * weights[d] for d in dims)
#     blended["overall"] = round(overall, 1)
#     return blended


# # ══════════════════════════════════════════════════════════════════════════════
# #  MAIN AGENT CLASS
# # ══════════════════════════════════════════════════════════════════════════════

# class CodeEvaluationAgent:

#     def __init__(self, db: Session):
#         self.db           = db
#         self.groq_api_key = settings.GROQ_API_KEY
#         self.model        = GROQ_MODEL
#         self.analyser     = StaticAnalyser()

#     # ─────────────────────────────────────────────────────────────────────────
#     #  PUBLIC: Evaluate a submission
#     # ─────────────────────────────────────────────────────────────────────────

#     def evaluate(self, submission_id: int, user_id: int) -> CodeEvaluation:
#         start_ms  = int(time.time() * 1000)
#         steps     = []

#         submission: CodeSubmission = self.db.query(CodeSubmission).filter(
#             CodeSubmission.id      == submission_id,
#             CodeSubmission.user_id == user_id,
#         ).first()
#         if not submission:
#             raise ValueError("Submission not found.")

#         # Mark running
#         submission.status = EvalStatus.RUNNING
#         submission.eval_count += 1
#         self.db.commit()

#         try:
#             user_ctx = self._get_user_context(user_id)
#             code     = submission.code
#             lang     = submission.language

#             # ── Step 1: Static analysis ───────────────────────────────────────
#             steps.append("🔍 Step 1: Running static analysis engine...")
#             issues, metrics = self.analyser.analyse(code, lang)
#             steps.append(f"   ✅ Found {len(issues)} issues | LOC={metrics['lines_of_code']} | CC={metrics['cyclomatic_complexity']}")

#             # ── Step 2: Static scores ─────────────────────────────────────────
#             steps.append("📊 Step 2: Calculating static dimension scores...")
#             static_scores = _calculate_static_scores(issues, metrics, code)
#             steps.append(f"   ✅ Static scores: {static_scores}")

#             # ── Step 3: LLM deep analysis ─────────────────────────────────────
#             steps.append("🤖 Step 3: Sending to Groq (llama-3.3-70b) for deep analysis...")
#             llm_result   = self._llm_deep_analysis(code, lang, issues, metrics, static_scores,
#                                                     submission.problem_context,
#                                                     submission.expected_output, user_ctx)
#             tokens_used  = llm_result.pop("tokens_used", 0)
#             steps.append(f"   ✅ LLM analysis complete. Tokens: {tokens_used}")

#             # ── Step 4: Blend scores ──────────────────────────────────────────
#             steps.append("⚙️  Step 4: Blending static + LLM scores...")
#             final_scores = _blend_scores(static_scores, llm_result.get("scores", {}))
#             steps.append(f"   ✅ Final overall score: {final_scores['overall']}/100")

#             # ── Step 5: Detect complexity from LLM ───────────────────────────
#             time_cx  = llm_result.get("time_complexity")
#             space_cx = llm_result.get("space_complexity")

#             # ── Step 6: Persist evaluation ────────────────────────────────────
#             steps.append("💾 Step 5: Persisting evaluation results...")
#             duration_ms = int(time.time() * 1000) - start_ms

#             evaluation = CodeEvaluation(
#                 submission_id        = submission_id,
#                 user_id              = user_id,
#                 overall_score        = final_scores["overall"],
#                 correctness_score    = final_scores["correctness"],
#                 quality_score        = final_scores["quality"],
#                 efficiency_score     = final_scores["efficiency"],
#                 security_score       = final_scores["security"],
#                 style_score          = final_scores["style"],
#                 documentation_score  = final_scores["documentation"],
#                 issues               = issues,
#                 time_complexity      = time_cx,
#                 space_complexity     = space_cx,
#                 cyclomatic_complexity= metrics["cyclomatic_complexity"],
#                 lines_of_code        = metrics["lines_of_code"],
#                 comment_ratio        = metrics["comment_ratio"],
#                 summary              = llm_result.get("summary", ""),
#                 detailed_feedback    = llm_result.get("detailed_feedback", ""),
#                 corrected_code       = llm_result.get("corrected_code"),
#                 key_improvements     = llm_result.get("key_improvements", []),
#                 learning_points      = llm_result.get("learning_points", []),
#                 best_practices_used  = llm_result.get("best_practices_used", []),
#                 anti_patterns        = llm_result.get("anti_patterns", []),
#                 suggested_resources  = llm_result.get("suggested_resources", []),
#                 agent_steps          = steps,
#                 tokens_used          = tokens_used,
#                 latency_ms           = duration_ms,
#                 model_used           = self.model,
#                 static_tool_used     = "regex_heuristics",
#             )
#             self.db.add(evaluation)
#             self.db.flush()

#             # History entry for progress tracking
#             history = EvalHistoryEntry(
#                 user_id       = user_id,
#                 submission_id = submission_id,
#                 evaluation_id = evaluation.id,
#                 overall_score = final_scores["overall"],
#                 language      = lang,
#                 eval_number   = submission.eval_count,
#             )
#             self.db.add(history)

#             submission.status = EvalStatus.DONE
#             self.db.commit()
#             self.db.refresh(evaluation)

#             steps.append(f"✅ Done! Score: {final_scores['overall']}/100 in {duration_ms}ms")
#             return evaluation

#         except Exception as exc:
#             submission.status = EvalStatus.FAILED
#             self.db.commit()
#             raise RuntimeError(f"Evaluation failed: {exc}") from exc

#     # ─────────────────────────────────────────────────────────────────────────
#     #  LLM Deep Analysis
#     # ─────────────────────────────────────────────────────────────────────────

#     def _llm_deep_analysis(
#         self,
#         code:             str,
#         language:         Language,
#         issues:           List[Dict],
#         metrics:          Dict,
#         static_scores:    Dict[str, float],
#         problem_context:  Optional[str],
#         expected_output:  Optional[str],
#         user_ctx:         Dict,
#     ) -> Dict:

#         issue_summary = "\n".join(
#             f"- [{i['severity'].upper()}] Line {i.get('line','?')} | {i['category']}: {i['message']}"
#             for i in issues[:15]
#         ) or "No static issues found."

#         system_prompt = f"""You are the Code Evaluation Agent inside aiTA — an AI teaching assistant for programming education in India.
# Your job is to perform a thorough, educational code review for a {user_ctx['skill_level']}-level student.

# Student profile:
# - Skill level: {user_ctx['skill_level']}
# - Languages they know: {', '.join(user_ctx['preferred_languages']) or 'general'}
# - Learning goals: {', '.join(user_ctx['learning_goals']) or 'general programming'}

# Static analysis already found these issues:
# {issue_summary}

# Static dimension scores (0-100): {json.dumps(static_scores)}

# Your review MUST:
# 1. Assess CORRECTNESS — does the logic actually solve the problem?
# 2. Identify TIME and SPACE complexity (Big-O notation)
# 3. Point out any ANTI-PATTERNS specific to {language.value}
# 4. List what the student did WELL (encouragement matters!)
# 5. Provide an IMPROVED version of the code with comments explaining changes
# 6. Give 3-5 LEARNING POINTS matched to the student's skill level
# 7. Suggest specific RESOURCES/TOPICS for the student to study next

# Tone: encouraging, specific, educational. Never demotivating.

# You MUST respond with ONLY valid JSON in this exact structure:
# {{
#   "scores": {{
#     "correctness": <0-100 float>,
#     "quality": <0-100 float>,
#     "efficiency": <0-100 float>,
#     "security": <0-100 float>,
#     "style": <0-100 float>,
#     "documentation": <0-100 float>
#   }},
#   "time_complexity": "<Big-O string or null>",
#   "space_complexity": "<Big-O string or null>",
#   "summary": "<2-3 sentence overall verdict, warm and encouraging>",
#   "detailed_feedback": "<full markdown feedback, structured with ## headings>",
#   "corrected_code": "<improved code with inline comments explaining every change>",
#   "key_improvements": ["improvement 1", "improvement 2", "improvement 3"],
#   "learning_points": ["concept 1 to revisit", "concept 2", "concept 3"],
#   "best_practices_used": ["good thing 1", "good thing 2"],
#   "anti_patterns": ["pattern to avoid 1", "pattern 2"],
#   "suggested_resources": ["topic/resource 1", "topic/resource 2", "topic/resource 3"]
# }}"""

#         context_block = ""
#         if problem_context:
#             context_block += f"\n\nProblem Statement:\n{problem_context}"
#         if expected_output:
#             context_block += f"\n\nExpected Output:\n{expected_output}"

#         user_prompt = f"""Please evaluate this {language.value} code:
# {context_block}

# ```{language.value}
# {code}
# ```

# Metrics from static analysis:
# - Lines of code: {metrics['lines_of_code']}
# - Comment ratio: {metrics['comment_ratio']:.1%}
# - Cyclomatic complexity: {metrics['cyclomatic_complexity']}

# Return ONLY valid JSON, no markdown fences, no extra text."""

#         try:
#             response = httpx.post(
#                 GROQ_API_URL,
#                 headers={
#                     "Authorization": f"Bearer {self.groq_api_key}",
#                     "Content-Type":  "application/json",
#                 },
#                 json={
#                     "model":       self.model,
#                     "max_tokens":  MAX_TOKENS,
#                     "temperature": 0.3,   # lower = more consistent, structured output
#                     "messages": [
#                         {"role": "system", "content": system_prompt},
#                         {"role": "user",   "content": user_prompt},
#                     ],
#                 },
#                 timeout=60.0,
#             )
#             response.raise_for_status()
#             data        = response.json()
#             raw_text    = data["choices"][0]["message"]["content"]
#             tokens_used = data.get("usage", {}).get("total_tokens", 0)

#             # Strip markdown fences if model wraps in ```json
#             clean = raw_text.strip()
#             if clean.startswith("```"):
#                 clean = clean.split("```")[1]
#                 if clean.startswith("json"):
#                     clean = clean[4:]
#             parsed = json.loads(clean.strip())
#             parsed["tokens_used"] = tokens_used
#             return parsed

#         except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
#             # Graceful fallback — use static scores only
#             return {
#                 "scores":              static_scores,
#                 "time_complexity":     None,
#                 "space_complexity":    None,
#                 "summary":             "Evaluated using static analysis (LLM unavailable).",
#                 "detailed_feedback":   "## Static Analysis Results\n\n" + issue_summary,
#                 "corrected_code":      None,
#                 "key_improvements":    [i["suggestion"] for i in issues[:5]],
#                 "learning_points":     [],
#                 "best_practices_used": [],
#                 "anti_patterns":       [],
#                 "suggested_resources": [],
#                 "tokens_used":         0,
#             }
#         except (json.JSONDecodeError, KeyError) as e:
#             return {
#                 "scores":              static_scores,
#                 "time_complexity":     None,
#                 "space_complexity":    None,
#                 "summary":             "Evaluation complete (LLM response parsing issue).",
#                 "detailed_feedback":   raw_text if 'raw_text' in dir() else "",
#                 "corrected_code":      None,
#                 "key_improvements":    [],
#                 "learning_points":     [],
#                 "best_practices_used": [],
#                 "anti_patterns":       [],
#                 "suggested_resources": [],
#                 "tokens_used":         0,
#             }

#     # ─────────────────────────────────────────────────────────────────────────
#     #  User context & query helpers
#     # ─────────────────────────────────────────────────────────────────────────

#     def _get_user_context(self, user_id: int) -> Dict:
#         user    = self.db.query(User).filter(User.id == user_id).first()
#         profile = self.db.query(LearningProfile).filter(
#             LearningProfile.user_id == user_id
#         ).first()
#         return {
#             "username":           user.username if user else "student",
#             "skill_level":        user.skill_level.value if user and user.skill_level else "beginner",
#             "preferred_languages": user.preferred_languages if user else [],
#             "learning_goals":     user.learning_goals if user else [],
#             "weak_areas":         profile.weak_areas if profile else [],
#         }

#     def get_submissions(self, user_id: int, limit: int = 20) -> List[CodeSubmission]:
#         return (
#             self.db.query(CodeSubmission)
#             .filter(CodeSubmission.user_id == user_id)
#             .order_by(CodeSubmission.created_at.desc())
#             .limit(limit)
#             .all()
#         )

#     def get_submission(self, submission_id: int, user_id: int) -> CodeSubmission:
#         sub = self.db.query(CodeSubmission).filter(
#             CodeSubmission.id      == submission_id,
#             CodeSubmission.user_id == user_id,
#         ).first()
#         if not sub:
#             raise ValueError("Submission not found.")
#         return sub

#     def get_user_stats(self, user_id: int) -> Dict:
#         from sqlalchemy import func as sqlfunc
#         evals = (
#             self.db.query(EvalHistoryEntry)
#             .filter(EvalHistoryEntry.user_id == user_id)
#             .order_by(EvalHistoryEntry.created_at.asc())
#             .all()
#         )
#         submissions = self.db.query(CodeSubmission).filter(
#             CodeSubmission.user_id == user_id
#         ).all()
#         evaluations = self.db.query(CodeEvaluation).filter(
#             CodeEvaluation.user_id == user_id
#         ).all()

#         scores    = [e.overall_score for e in evals]
#         avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
#         best      = round(max(scores), 1) if scores else 0.0

#         # Improvement trend: slope of last 5 scores
#         recent = scores[-5:]
#         trend  = 0.0
#         if len(recent) >= 2:
#             trend = round((recent[-1] - recent[0]) / max(len(recent) - 1, 1), 2)

#         languages_used = list({e.language.value for e in evals})

#         all_issues = []
#         for ev in evaluations:
#             all_issues.extend(ev.issues or [])
#         from collections import Counter
#         categories   = [i.get("category","") for i in all_issues]
#         most_common  = [cat for cat, _ in Counter(categories).most_common(5)]

#         return {
#             "total_submissions":  len(submissions),
#             "total_evaluations":  len(evaluations),
#             "avg_overall_score":  avg_score,
#             "best_score":         best,
#             "languages_used":     languages_used,
#             "most_common_issues": most_common,
#             "improvement_trend":  trend,
#             "recent_history":     evals[-10:],
#         }


"""
agents/code_eval_agent.py — FIXED:
  1. Correct code (print("Hello"), etc.) = 100% correctness
  2. Safety grading REMOVED — no more penalty for "safe" patterns
  3. Static analyser only checks REAL quality issues
  4. Scoring is purely based on: correctness, quality, efficiency, style, docs
  5. Simple correct code always scores 90-100%

Copy to: backend/app/agents/code_eval_agent.py
"""

# import re
# import ast
# import httpx
# import json
# from typing import Optional
# from app.core.config import settings

# GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# MODEL = "llama-3.3-70b-versatile"


# # ─── Static Analyser ──────────────────────────────────────────────────────────

# def static_analyse(code: str, language: str) -> dict:
#     """
#     Pure static analysis — NO safety grading.
#     Returns issues and raw dimension scores.
#     """
#     issues = []
#     language = language.lower()

#     # Only analyse Python statically (for other languages rely more on LLM)
#     if language == "python":
#         lines = code.split("\n")
#         non_empty_lines = [l for l in lines if l.strip()]
        
#         # 1. Check for deeply nested code (4+ levels)
#         for i, line in enumerate(lines):
#             indent = len(line) - len(line.lstrip())
#             if indent >= 16:  # 4+ levels of 4-space indentation
#                 issues.append({
#                     "line": i + 1,
#                     "severity": "warning",
#                     "category": "complexity",
#                     "message": "Deep nesting (4+ levels) — consider extracting to a function",
#                 })
#                 break  # Only flag once
        
#         # 2. Check variable naming (single letters except i, j, k, n, x, y)
#         allowed_single = {"i", "j", "k", "n", "x", "y", "z", "e", "f"}
#         assignments = re.findall(r'\b([a-z])\s*=\s*[^=]', code)
#         bad_names = [v for v in set(assignments) if v not in allowed_single]
#         if bad_names:
#             issues.append({
#                 "line": 0,
#                 "severity": "info",
#                 "category": "style",
#                 "message": f"Consider more descriptive variable names: {', '.join(bad_names[:3])}",
#             })
        
#         # 3. Bare except clauses
#         if re.search(r'except\s*:', code):
#             issues.append({
#                 "line": 0,
#                 "severity": "warning",
#                 "category": "error_handling",
#                 "message": "Bare 'except:' catches all exceptions — specify the exception type",
#             })
        
#         # 4. Print statements in functions (debug prints)
#         func_blocks = re.findall(r'def\s+\w+.*?(?=\ndef|\Z)', code, re.DOTALL)
#         for block in func_blocks:
#             debug_prints = re.findall(r'^\s+print\(', block, re.MULTILINE)
#             if len(debug_prints) > 2:
#                 issues.append({
#                     "line": 0,
#                     "severity": "info",
#                     "category": "style",
#                     "message": "Many print statements inside functions — remove debug prints for production",
#                 })
#                 break
        
#         # 5. Magic numbers (only flag if not in simple scripts)
#         if len(non_empty_lines) > 5:
#             magic = re.findall(r'(?<!["\'])\b(?!0\b|1\b|2\b|10\b|100\b)\d{2,}\b(?!["\'])', code)
#             if len(magic) > 2:
#                 issues.append({
#                     "line": 0,
#                     "severity": "info",
#                     "category": "style",
#                     "message": f"Magic numbers found ({', '.join(set(magic[:3]))}...) — consider named constants",
#                 })
        
#         # 6. Missing docstrings (only for longer functions, not simple scripts)
#         functions = re.findall(r'(def\s+\w+[^:]+:)\s*\n', code)
#         for func in functions:
#             func_name = re.search(r'def\s+(\w+)', func)
#             if func_name and not func_name.group(1).startswith("_"):
#                 func_body_start = code.find(func)
#                 if func_body_start >= 0:
#                     after = code[func_body_start + len(func):func_body_start + len(func) + 100]
#                     if '"""' not in after and "'''" not in after:
#                         issues.append({
#                             "line": 0,
#                             "severity": "info",
#                             "category": "documentation",
#                             "message": f"Function '{func_name.group(1)}' missing docstring",
#                         })
        
#         # 7. Long lines
#         for i, line in enumerate(lines):
#             if len(line) > 100:
#                 issues.append({
#                     "line": i + 1,
#                     "severity": "info",
#                     "category": "style",
#                     "message": f"Line {i+1} is {len(line)} chars (PEP8 recommends max 79-99)",
#                 })
#                 break
        
#         # 8. eval/exec usage — flag as info only (not security)
#         if re.search(r'\beval\s*\(|\bexec\s*\(', code):
#             issues.append({
#                 "line": 0,
#                 "severity": "warning",
#                 "category": "quality",
#                 "message": "eval()/exec() usage — consider safer alternatives",
#             })
        
#         # REMOVED: No safety grading, no "unsafe" scores, no security dimension penalties
    
#     return {"issues": issues}


# def compute_static_scores(code: str, language: str, issues: list) -> dict:
#     """
#     Compute dimension scores from static analysis.
    
#     KEY FIX: Correct simple code (like print("Hello")) = 90-100%.
#     Scores only deducted for REAL quality issues, not safety theater.
#     """
#     lines = code.split("\n")
#     non_empty = [l for l in lines if l.strip()]
#     code_length = len(non_empty)
    
#     # Categorise issues by severity
#     critical = [i for i in issues if i.get("severity") == "error"]
#     warnings = [i for i in issues if i.get("severity") == "warning"]
#     infos = [i for i in issues if i.get("severity") == "info"]
    
#     # ── Correctness Score ─────────────────────────────────────────────────────
#     # Start at 100. Only deduct for SYNTAX errors and critical issues.
#     # print("Hello") is syntactically correct → 100 correctness
#     correctness = 100
#     if critical:
#         correctness -= min(len(critical) * 20, 50)
    
#     # Try to parse Python for syntax errors
#     if language.lower() == "python":
#         try:
#             ast.parse(code)
#         except SyntaxError as e:
#             correctness -= 30
#             issues.insert(0, {
#                 "line": e.lineno or 0,
#                 "severity": "error",
#                 "category": "syntax",
#                 "message": f"Syntax error: {e.msg}",
#             })
    
#     correctness = max(correctness, 0)
    
#     # ── Quality Score ─────────────────────────────────────────────────────────
#     # Start at 85. For short simple code (≤5 lines), start at 90.
#     quality_base = 90 if code_length <= 5 else 85
#     quality = quality_base
#     quality -= len(warnings) * 8
#     quality -= len(infos) * 3
#     quality = max(min(quality, 100), 0)
    
#     # ── Efficiency Score ─────────────────────────────────────────────────────
#     # Can't determine efficiency from static analysis alone — default 80
#     # LLM will refine this
#     efficiency = 80
    
#     # ── Style Score ───────────────────────────────────────────────────────────
#     style = 90 if code_length <= 5 else 85
#     style_issues = [i for i in issues if i.get("category") == "style"]
#     style -= len(style_issues) * 5
#     style = max(min(style, 100), 0)
    
#     # ── Documentation Score ───────────────────────────────────────────────────
#     # Short scripts don't need docstrings — start at 90 for simple code
#     doc_issues = [i for i in issues if i.get("category") == "documentation"]
#     documentation = 90 if code_length <= 5 else 70
#     documentation -= len(doc_issues) * 10
#     documentation = max(min(documentation, 100), 0)
    
#     # ── Overall Score ─────────────────────────────────────────────────────────
#     # Weighted: Correctness is the most important
#     # No security dimension — REMOVED
#     overall = (
#         correctness * 0.40 +   # Correctness is king
#         quality * 0.25 +
#         efficiency * 0.20 +
#         style * 0.10 +
#         documentation * 0.05
#     )
#     overall = round(overall)
    
#     return {
#         "overall": overall,
#         "correctness": correctness,
#         "quality": quality,
#         "efficiency": efficiency,
#         "style": style,
#         "documentation": documentation,
#         # Security dimension REMOVED
#     }


# # ─── LLM Deep Analysis ────────────────────────────────────────────────────────

# async def llm_analyse(
#     code: str,
#     language: str,
#     static_issues: list,
#     static_scores: dict,
#     problem_context: Optional[str] = None,
# ) -> dict:
#     """
#     Deep LLM analysis via Groq.
#     Returns refined scores + detailed feedback.
    
#     IMPORTANT: LLM is instructed to give fair, honest scores.
#     Correct simple code should score 90-100%.
#     """
    
#     problem_ctx = f"\nProblem context: {problem_context}" if problem_context else ""
#     static_summary = f"Static analysis found {len(static_issues)} issues." if static_issues else "Static analysis found no issues."
    
#     prompt = f"""You are a fair, constructive code reviewer. Analyse this {language} code and provide honest, accurate scoring.

# CRITICAL SCORING RULES:
# 1. Simple, correct code (like print("Hello"), basic functions that work) MUST score 90-100% for correctness
# 2. Never penalise code for being "too simple" — simple correct code is GOOD code
# 3. Security is NOT a scoring dimension — ignore safety/security concerns
# 4. Score based on: does the code work correctly? is it written cleanly?
# 5. A one-liner that solves the problem perfectly = 100% correctness
# {problem_ctx}

# Code to analyse:
# ```{language}
# {code}
# ```

# {static_summary}
# Static scores (preliminary): {json.dumps(static_scores)}

# Respond ONLY with this exact JSON (no markdown, no explanation):
# {{
#   "correctness": <0-100, how correct/working is the code>,
#   "quality": <0-100, code structure and readability>,
#   "efficiency": <0-100, time/space complexity>,
#   "style": <0-100, naming, formatting>,
#   "documentation": <0-100, comments and docstrings>,
#   "complexity": {{
#     "time": "<O(1), O(n), O(n²), etc>",
#     "space": "<O(1), O(n), etc>",
#     "explanation": "<brief explanation>"
#   }},
#   "corrected_code": "<improved version with inline comments, or same code if already good>",
#   "best_practices": ["<practice 1>", "<practice 2>"],
#   "anti_patterns": ["<pattern 1 if any>"],
#   "learning_points": ["<key insight 1>", "<key insight 2>"],
#   "summary": "<2-3 sentence honest assessment. Be encouraging for correct code>",
#   "suggested_resources": ["<resource 1>"]
# }}"""
    
#     async with httpx.AsyncClient(timeout=60.0) as client:
#         response = await client.post(
#             GROQ_API_URL,
#             headers={
#                 "Authorization": f"Bearer {settings.GROQ_API_KEY}",
#                 "Content-Type": "application/json",
#             },
#             json={
#                 "model": MODEL,
#                 "messages": [{"role": "user", "content": prompt}],
#                 "max_tokens": 1500,
#                 "temperature": 0.3,  # Low temperature for consistent scoring
#             },
#         )
#         response.raise_for_status()
#         data = response.json()
    
#     raw = data["choices"][0]["message"]["content"].strip()
#     tokens = data.get("usage", {}).get("total_tokens", 0)
    
#     # Parse JSON response
#     try:
#         # Strip any markdown code fences
#         clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
#         result = json.loads(clean)
#         result["tokens_used"] = tokens
#         return result
#     except json.JSONDecodeError:
#         # Fallback: return static scores with a note
#         return {
#             **static_scores,
#             "complexity": {"time": "O(?)", "space": "O(?)", "explanation": "Analysis unavailable"},
#             "corrected_code": code,
#             "best_practices": [],
#             "anti_patterns": [],
#             "learning_points": ["Run locally to test your code"],
#             "summary": "Could not complete deep analysis. Static analysis results shown.",
#             "suggested_resources": [],
#             "tokens_used": tokens,
#         }


# # ─── Final Blended Scorer ─────────────────────────────────────────────────────

# def blend_scores(static: dict, llm: dict) -> dict:
#     """
#     Blend static (30%) and LLM (70%) scores.
#     LLM gets more weight as it understands code semantics.
    
#     FIX: For very short code (≤5 non-empty lines), if LLM says correctness ≥ 90,
#     we trust it completely — no downward pressure from static analysis.
#     """
#     dims = ["correctness", "quality", "efficiency", "style", "documentation"]
#     blended = {}
    
#     for dim in dims:
#         s = static.get(dim, 85)
#         l = llm.get(dim, 85)
        
#         # If LLM gives high correctness, trust it more
#         if dim == "correctness" and l >= 90:
#             blended[dim] = round(l)  # Trust LLM on correctness for correct code
#         else:
#             blended[dim] = round(s * 0.30 + l * 0.70)
    
#     # Recalculate overall
#     blended["overall"] = round(
#         blended["correctness"] * 0.40 +
#         blended["quality"] * 0.25 +
#         blended["efficiency"] * 0.20 +
#         blended["style"] * 0.10 +
#         blended["documentation"] * 0.05
#     )
    
#     return blended


# # ─── Main Evaluation Pipeline ─────────────────────────────────────────────────

# async def evaluate_code(
#     code: str,
#     language: str,
#     problem_context: Optional[str] = None,
# ) -> dict:
#     """
#     Full 4-step evaluation pipeline:
#     1. Static analysis (syntax + quality issues)
#     2. Static scoring (NO safety grading)
#     3. LLM deep analysis
#     4. Blended final scores
    
#     Returns complete evaluation result.
#     """
    
#     # Step 1: Static analysis
#     static_result = static_analyse(code, language)
#     issues = static_result["issues"]
    
#     # Step 2: Static scores
#     static_scores = compute_static_scores(code, language, issues)
    
#     # Step 3: LLM deep analysis
#     llm_result = await llm_analyse(
#         code=code,
#         language=language,
#         static_issues=issues,
#         static_scores=static_scores,
#         problem_context=problem_context,
#     )
    
#     # Step 4: Blend scores
#     final_scores = blend_scores(static_scores, llm_result)
    
#     return {
#         "scores": final_scores,
#         "issues": issues,
#         "complexity": llm_result.get("complexity", {}),
#         "corrected_code": llm_result.get("corrected_code", code),
#         "best_practices": llm_result.get("best_practices", []),
#         "anti_patterns": llm_result.get("anti_patterns", []),
#         "learning_points": llm_result.get("learning_points", []),
#         "summary": llm_result.get("summary", ""),
#         "suggested_resources": llm_result.get("suggested_resources", []),
#         "tokens_used": llm_result.get("tokens_used", 0),
#         "pipeline_steps": [
#             {"step": "Static Analysis", "status": "done", "findings": f"{len(issues)} issues found"},
#             {"step": "Scoring Engine", "status": "done", "findings": f"Preliminary score: {static_scores['overall']}%"},
#             {"step": "LLM Deep Analysis", "status": "done", "findings": f"Groq analysis complete"},
#             {"step": "Score Blending", "status": "done", "findings": f"Final score: {final_scores['overall']}%"},
#         ],
#     }




"""
agents/code_eval_agent.py — MERGED: Full original functionality + fixed scoring

Changes from original:
  ✅ Correct code (print("Hello")) = 100% correctness — not 91%
  ✅ Safety grading REMOVED from score weighting (security still detected as issues, just not weighted)
  ✅ Static correctness starts at 100, not 60
  ✅ LLM instructed: simple correct code = 90-100%
  ✅ blend_scores() trusts LLM correctness when it says ≥ 90
  ✅ All original features kept: StaticAnalyser class, all 10 checks, metrics, history, stats

Copy to: backend/app/agents/code_eval_agent.py
"""

import re
import json
import time
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter

from sqlalchemy.orm import Session

from app.models.user import User, LearningProfile
from app.models.code_eval import (
    CodeSubmission, CodeEvaluation, EvalHistoryEntry,
    Language, EvalStatus, SeverityLevel
)
from app.core.config import settings


GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_TOKENS   = 2500


# ══════════════════════════════════════════════════════════════════════════════
#  STATIC ANALYSER — pure Python, no external tools needed
# ══════════════════════════════════════════════════════════════════════════════

class StaticAnalyser:
    """
    Language-aware heuristic rule engine.
    Produces a list of Issue dicts without running the code.
    All 10 original checks kept. Security issues are still DETECTED and shown
    as feedback, but are no longer a scoring dimension.
    """

    def analyse(self, code: str, language: Language) -> Tuple[List[Dict], Dict]:
        """
        Returns (issues, metrics).
        issues : list of Issue dicts
        metrics: {lines_of_code, comment_ratio, cyclomatic_complexity}
        """
        lines    = code.splitlines()
        issues   = []
        issue_id = 1

        def add(line, severity, category, message, suggestion):
            nonlocal issue_id
            issues.append({
                "id": issue_id, "line": line,
                "severity": severity, "category": category,
                "message": message, "suggestion": suggestion
            })
            issue_id += 1

        # ── Metrics ───────────────────────────────────────────────────────────
        total_lines   = len(lines)
        code_lines    = [l for l in lines if l.strip() and not self._is_comment(l, language)]
        comment_lines = [l for l in lines if self._is_comment(l, language)]
        loc           = len(code_lines)
        comment_ratio = len(comment_lines) / max(total_lines, 1)

        decision_keywords = r'\b(if|elif|else|for|while|except|case|when|switch|and|or|&&|\|\|)\b'
        cyclomatic = 1 + len(re.findall(decision_keywords, code))

        # ── 1. Function / method length ───────────────────────────────────────
        func_pattern = self._func_pattern(language)
        if func_pattern:
            for m in re.finditer(func_pattern, code, re.MULTILINE):
                start_line = code[:m.start()].count('\n') + 1
                body_start = code[:m.end()].count('\n')
                next_func  = re.search(func_pattern, code[m.end():], re.MULTILINE)
                body_end   = (body_start + code[m.end():next_func.start()].count('\n')
                              if next_func else total_lines)
                body_len   = body_end - body_start
                if body_len > 40:
                    add(start_line, SeverityLevel.WARNING, "complexity",
                        f"Function starting at line {start_line} is {body_len} lines long (>40).",
                        "Break it into smaller, single-responsibility functions.")

        # ── 2. Deep nesting (4+ levels) ───────────────────────────────────────
        for i, line in enumerate(lines, 1):
            indent = len(line) - len(line.lstrip())
            spaces_per_level = 4 if language != Language.GO else 1
            level = indent // max(spaces_per_level, 1)
            if level >= 4 and line.strip():
                add(i, SeverityLevel.WARNING, "complexity",
                    f"Line {i}: deeply nested code (indent level {level}).",
                    "Extract inner logic into a helper function to reduce nesting.")
                break

        # ── 3. Magic numbers ──────────────────────────────────────────────────
        magic_pattern = r'(?<!["\'\w])(?<!\.)\b([2-9]\d{2,}|\d{4,})\b(?![\"\'])'
        for m in re.finditer(magic_pattern, code):
            line_no = code[:m.start()].count('\n') + 1
            if not any(kw in lines[line_no-1] for kw in ['#', '//', '/*', '*', 'range', 'size', 'len']):
                add(line_no, SeverityLevel.INFO, "quality",
                    f"Magic number `{m.group()}` at line {line_no}.",
                    "Replace magic numbers with named constants for readability.")
                break

        # ── 4. Print/console debug statements ────────────────────────────────
        # NOTE: A standalone print("Hello") is NOT flagged — only excessive prints
        # inside functions (>2) are flagged. Single top-level prints are fine.
        debug_patterns = {
            Language.PYTHON:     r'\bprint\s*\(',
            Language.JAVASCRIPT: r'\bconsole\.(log|warn|error)\s*\(',
            Language.TYPESCRIPT: r'\bconsole\.(log|warn|error)\s*\(',
            Language.JAVA:       r'System\.out\.print',
            Language.CPP:        r'\bcout\s*<<',
        }
        dp = debug_patterns.get(language)
        if dp:
            # Count prints INSIDE function bodies only
            func_blocks = re.findall(r'def\s+\w+.*?(?=\ndef|\Z)', code, re.DOTALL)
            prints_in_funcs = sum(
                len(re.findall(r'^\s+' + dp.lstrip('\\b'), block, re.MULTILINE))
                for block in func_blocks
            )
            # Only flag if more than 2 debug prints inside functions
            if prints_in_funcs > 2:
                add(None, SeverityLevel.INFO, "quality",
                    f"{prints_in_funcs} debug print/console statements found inside functions.",
                    "Remove debug statements before production. Consider a logging framework.")

        # ── 5. Security checks (detected but NOT used in scoring) ─────────────
        # These are shown as informational feedback, not score deductions.
        dangerous = {
            Language.PYTHON: [
                (r'\beval\s*\(',      "Use of `eval()` is dangerous — can execute arbitrary code.",
                 "Never use eval() on untrusted input. Use ast.literal_eval() for data parsing."),
                (r'\bexec\s*\(',      "Use of `exec()` is a security risk.",
                 "Avoid exec() — refactor logic to avoid dynamic code execution."),
                (r'input\s*\(.*sql',  "Potential SQL injection via user input.",
                 "Use parameterised queries (e.g., cursor.execute(sql, params))."),
                (r'__import__\s*\(',  "`__import__()` is a code smell and security risk.",
                 "Use standard import statements instead of __import__()."),
            ],
            Language.JAVASCRIPT: [
                (r'\beval\s*\(',      "Use of `eval()` is a critical security risk.",
                 "Never use eval(). Use JSON.parse() for data, or restructure logic."),
                (r'innerHTML\s*=',    "Direct innerHTML assignment risks XSS attacks.",
                 "Use textContent for text, or sanitise HTML before inserting."),
                (r'document\.write\(', "`document.write()` is deprecated and dangerous.",
                 "Use DOM manipulation methods like createElement and appendChild."),
            ],
            Language.JAVA: [
                (r'Runtime\.getRuntime\(\)\.exec', "Runtime.exec() is a security risk.",
                 "Avoid executing system commands. Use ProcessBuilder with a whitelist."),
            ],
        }
        for pattern, msg, suggestion in dangerous.get(language, []):
            if re.search(pattern, code):
                # Use WARNING not ERROR — security is informational feedback only
                add(None, SeverityLevel.WARNING, "security", msg, suggestion)

        # ── 6. Documentation ──────────────────────────────────────────────────
        if language == Language.PYTHON:
            funcs   = re.findall(r'def\s+\w+\s*\(', code)
            docs    = re.findall(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', code)
            classes = re.findall(r'class\s+\w+', code)
            if len(funcs) > 2 and len(docs) == 0:
                add(None, SeverityLevel.WARNING, "documentation",
                    f"{len(funcs)} functions found with no docstrings.",
                    'Add docstrings: """Brief description, Args, Returns."""')
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            funcs  = re.findall(r'function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\(', code)
            jsdoc  = re.findall(r'/\*\*[\s\S]*?\*/', code)
            if len(funcs) > 2 and len(jsdoc) == 0:
                add(None, SeverityLevel.WARNING, "documentation",
                    f"{len(funcs)} functions with no JSDoc comments.",
                    "Add JSDoc: /** @param {type} name - description @returns {type} */")
        elif language == Language.JAVA:
            methods = re.findall(r'(public|private|protected)\s+\w+\s+\w+\s*\(', code)
            javadoc = re.findall(r'/\*\*[\s\S]*?\*/', code)
            if len(methods) > 2 and len(javadoc) == 0:
                add(None, SeverityLevel.WARNING, "documentation",
                    f"{len(methods)} methods with no Javadoc.",
                    "Add Javadoc: /** @param name desc @return desc */")

        # ── 7. Naming conventions ─────────────────────────────────────────────
        if language == Language.PYTHON:
            for m in re.finditer(r'\bclass\s+([a-z][a-zA-Z0-9_]*)\b', code):
                line_no = code[:m.start()].count('\n') + 1
                add(line_no, SeverityLevel.WARNING, "naming",
                    f"Class `{m.group(1)}` should use PascalCase (e.g. `{m.group(1).capitalize()}`).",
                    "Python convention: class names use PascalCase (PEP 8).")
                break
            # Only flag truly non-descriptive single letters (not i, j, k, x, y, n, e, f)
            allowed_single = {"i", "j", "k", "n", "x", "y", "z", "e", "f"}
            for m in re.finditer(r'\b([a-wz])\s*=\s*(?!\s)', code):
                if m.group(1) not in allowed_single:
                    line_no = code[:m.start()].count('\n') + 1
                    add(line_no, SeverityLevel.INFO, "naming",
                        f"Single-letter variable `{m.group(1)}` at line {line_no} hurts readability.",
                        "Use descriptive names like `count`, `index`, `result` instead.")
                    break

        # ── 8. Long lines ─────────────────────────────────────────────────────
        for i, line in enumerate(lines, 1):
            if len(line) > 100:
                add(i, SeverityLevel.INFO, "style",
                    f"Line {i} is {len(line)} characters long (>100).",
                    "Keep lines under 100 characters for readability.")
                break

        # ── 9. TODO / FIXME / HACK ────────────────────────────────────────────
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', line):
                add(i, SeverityLevel.INFO, "quality",
                    f"Unresolved TODO/FIXME at line {i}: `{line.strip()[:60]}`.",
                    "Resolve or track TODOs in an issue tracker before submitting.")

        # ── 10. Empty except blocks ───────────────────────────────────────────
        if language == Language.PYTHON:
            for m in re.finditer(r'except[^:]*:\s*\n\s*(pass\s*\n|#.*\n)', code):
                line_no = code[:m.start()].count('\n') + 1
                add(line_no, SeverityLevel.WARNING, "logic",
                    f"Empty or bare except block at line {line_no} silences all errors.",
                    "Always handle specific exceptions and log or re-raise them.")

        metrics = {
            "lines_of_code":         loc,
            "comment_ratio":         round(comment_ratio, 3),
            "cyclomatic_complexity": cyclomatic,
        }
        return issues, metrics

    def _is_comment(self, line: str, language: Language) -> bool:
        s = line.strip()
        if language == Language.PYTHON:
            return s.startswith('#')
        if language in (Language.JAVASCRIPT, Language.TYPESCRIPT,
                        Language.JAVA, Language.CPP, Language.C,
                        Language.GO, Language.RUST):
            return s.startswith('//') or s.startswith('*') or s.startswith('/*')
        return False

    def _func_pattern(self, language: Language) -> Optional[str]:
        patterns = {
            Language.PYTHON:     r'^\s*def\s+\w+\s*\(',
            Language.JAVASCRIPT: r'^\s*(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\()',
            Language.TYPESCRIPT: r'^\s*(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\()',
            Language.JAVA:       r'^\s*(?:public|private|protected|static)\s+\w[\w<>[\]]*\s+\w+\s*\(',
            Language.CPP:        r'^\w[\w:*&<>]*\s+\w+\s*\(',
            Language.GO:         r'^\s*func\s+\w+\s*\(',
            Language.RUST:       r'^\s*(?:pub\s+)?fn\s+\w+\s*\(',
        }
        return patterns.get(language)


# ══════════════════════════════════════════════════════════════════════════════
#  SCORE CALCULATOR — FIXED
# ══════════════════════════════════════════════════════════════════════════════

def _calculate_static_scores(issues: List[Dict], metrics: Dict, code: str) -> Dict[str, float]:
    """
    Derive initial dimension scores from static analysis.

    KEY FIXES vs original:
    1. correctness starts at 100 (not 60) — correct code is correct
    2. Security is NOT a scoring dimension (still shown as feedback)
    3. Short/simple code gets higher base scores
    4. LLM will refine further
    """
    loc           = metrics.get("lines_of_code", 1) or 1
    comment_ratio = metrics.get("comment_ratio", 0)
    cc            = metrics.get("cyclomatic_complexity", 1)
    is_short      = loc <= 5  # Simple scripts like print("Hello")

    criticals = sum(1 for i in issues if i["severity"] == SeverityLevel.CRITICAL)
    errors    = sum(1 for i in issues if i["severity"] == SeverityLevel.ERROR)
    warnings  = sum(1 for i in issues if i["severity"] == SeverityLevel.WARNING)
    infos     = sum(1 for i in issues if i["severity"] == SeverityLevel.INFO)

    # ── Correctness: starts at 100, only real errors lower it ────────────────
    # print("Hello") has 0 errors → correctness = 100
    correctness = 100.0
    correctness -= criticals * 30
    correctness -= errors * 20
    # Security issues (now WARNING) do NOT lower correctness
    correctness = max(0.0, correctness)

    # ── Style ─────────────────────────────────────────────────────────────────
    style_issues = [i for i in issues if i["category"] == "style"]
    style = 95.0 if is_short else 85.0
    style = max(0.0, style - len(style_issues) * 8 - infos * 2)

    # ── Quality ───────────────────────────────────────────────────────────────
    qual_issues = [i for i in issues if i["category"] in ("quality", "naming")]
    quality = 90.0 if is_short else 80.0
    quality = max(0.0, quality - len(qual_issues) * 10 - warnings * 4)

    # ── Documentation ─────────────────────────────────────────────────────────
    doc_issues = [i for i in issues if i["category"] == "documentation"]
    # Short scripts don't need docstrings
    documentation = 90.0 if is_short else (
        min(100.0, 40 + comment_ratio * 200 +
            (30 if len(doc_issues) == 0 else 0))
    )

    # ── Efficiency ────────────────────────────────────────────────────────────
    if cc <= 5:    efficiency = 90.0
    elif cc <= 10: efficiency = 75.0
    elif cc <= 20: efficiency = 55.0
    else:          efficiency = max(20.0, 100 - cc * 2)

    # ── Overall (NO security dimension) ──────────────────────────────────────
    # Weights: correctness 40%, quality 25%, efficiency 20%, style 10%, docs 5%
    overall = (
        correctness  * 0.40 +
        quality      * 0.25 +
        efficiency   * 0.20 +
        style        * 0.10 +
        documentation * 0.05
    )

    return {
        "correctness":   round(min(correctness,   100), 1),
        "style":         round(min(style,         100), 1),
        "quality":       round(min(quality,       100), 1),
        "documentation": round(min(documentation, 100), 1),
        "efficiency":    round(min(efficiency,    100), 1),
        # NOTE: security removed from scores — still shown in issues list
    }


def _blend_scores(static: Dict[str, float], llm: Dict[str, float]) -> Dict[str, float]:
    """
    Blend static (40%) and LLM (60%) scores.

    KEY FIX: If LLM says correctness ≥ 90, trust it fully.
    This ensures print("Hello") → 100%, not a blended-down 91%.
    """
    dims = ["correctness", "quality", "efficiency", "style", "documentation"]
    blended = {}

    for d in dims:
        s_val = static.get(d, 80.0)
        l_val = llm.get(d, s_val)

        if d == "correctness" and l_val >= 90:
            # Trust LLM on correctness for correct code — no downward blending
            blended[d] = round(l_val, 1)
        else:
            blended[d] = round(s_val * 0.40 + l_val * 0.60, 1)

    # Overall — no security dimension
    weights = {
        "correctness":   0.40,
        "quality":       0.25,
        "efficiency":    0.20,
        "style":         0.10,
        "documentation": 0.05,
    }
    overall = sum(blended[d] * weights[d] for d in dims)
    blended["overall"] = round(overall, 1)
    return blended


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN AGENT CLASS
# ══════════════════════════════════════════════════════════════════════════════

class CodeEvaluationAgent:

    def __init__(self, db: Session):
        self.db           = db
        self.groq_api_key = settings.GROQ_API_KEY
        self.model        = GROQ_MODEL
        self.analyser     = StaticAnalyser()

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC: Evaluate a submission
    # ─────────────────────────────────────────────────────────────────────────

    def evaluate(self, submission_id: int, user_id: int) -> CodeEvaluation:
        start_ms = int(time.time() * 1000)
        steps    = []

        submission: CodeSubmission = self.db.query(CodeSubmission).filter(
            CodeSubmission.id      == submission_id,
            CodeSubmission.user_id == user_id,
        ).first()
        if not submission:
            raise ValueError("Submission not found.")

        submission.status = EvalStatus.RUNNING
        submission.eval_count += 1
        self.db.commit()

        try:
            user_ctx = self._get_user_context(user_id)
            code     = submission.code
            lang     = submission.language

            # ── Step 1: Static analysis ───────────────────────────────────────
            steps.append("🔍 Step 1: Running static analysis engine...")
            issues, metrics = self.analyser.analyse(code, lang)
            steps.append(
                f"   ✅ Found {len(issues)} issues | "
                f"LOC={metrics['lines_of_code']} | "
                f"CC={metrics['cyclomatic_complexity']}"
            )

            # ── Step 2: Static scores ─────────────────────────────────────────
            steps.append("📊 Step 2: Calculating dimension scores (no safety penalty)...")
            static_scores = _calculate_static_scores(issues, metrics, code)
            steps.append(f"   ✅ Static scores: {static_scores}")

            # ── Step 3: LLM deep analysis ─────────────────────────────────────
            steps.append("🤖 Step 3: Sending to Groq (llama-3.3-70b) for deep analysis...")
            llm_result  = self._llm_deep_analysis(
                code, lang, issues, metrics, static_scores,
                submission.problem_context,
                submission.expected_output,
                user_ctx,
            )
            tokens_used = llm_result.pop("tokens_used", 0)
            steps.append(f"   ✅ LLM analysis complete. Tokens: {tokens_used}")

            # ── Step 4: Blend scores ──────────────────────────────────────────
            steps.append("⚙️  Step 4: Blending scores (correct code protected)...")
            final_scores = _blend_scores(static_scores, llm_result.get("scores", {}))
            steps.append(f"   ✅ Final overall score: {final_scores['overall']}/100")

            time_cx  = llm_result.get("time_complexity")
            space_cx = llm_result.get("space_complexity")

            # ── Step 5: Persist ───────────────────────────────────────────────
            steps.append("💾 Step 5: Persisting evaluation results...")
            duration_ms = int(time.time() * 1000) - start_ms

            evaluation = CodeEvaluation(
                submission_id       = submission_id,
                user_id             = user_id,
                overall_score       = final_scores["overall"],
                correctness_score   = final_scores["correctness"],
                quality_score       = final_scores["quality"],
                efficiency_score    = final_scores["efficiency"],
                security_score      = 100.0,   # Fixed: security no longer scored, always 100
                style_score         = final_scores["style"],
                documentation_score = final_scores["documentation"],
                issues              = issues,
                time_complexity     = time_cx,
                space_complexity    = space_cx,
                cyclomatic_complexity = metrics["cyclomatic_complexity"],
                lines_of_code       = metrics["lines_of_code"],
                comment_ratio       = metrics["comment_ratio"],
                summary             = llm_result.get("summary", ""),
                detailed_feedback   = llm_result.get("detailed_feedback", ""),
                corrected_code      = llm_result.get("corrected_code"),
                key_improvements    = llm_result.get("key_improvements", []),
                learning_points     = llm_result.get("learning_points", []),
                best_practices_used = llm_result.get("best_practices_used", []),
                anti_patterns       = llm_result.get("anti_patterns", []),
                suggested_resources = llm_result.get("suggested_resources", []),
                agent_steps         = steps,
                tokens_used         = tokens_used,
                latency_ms          = duration_ms,
                model_used          = self.model,
                static_tool_used    = "regex_heuristics",
            )
            self.db.add(evaluation)
            self.db.flush()

            history = EvalHistoryEntry(
                user_id       = user_id,
                submission_id = submission_id,
                evaluation_id = evaluation.id,
                overall_score = final_scores["overall"],
                language      = lang,
                eval_number   = submission.eval_count,
            )
            self.db.add(history)

            submission.status = EvalStatus.DONE
            self.db.commit()
            self.db.refresh(evaluation)

            steps.append(f"✅ Done! Score: {final_scores['overall']}/100 in {duration_ms}ms")
            return evaluation

        except Exception as exc:
            submission.status = EvalStatus.FAILED
            self.db.commit()
            raise RuntimeError(f"Evaluation failed: {exc}") from exc

    # ─────────────────────────────────────────────────────────────────────────
    #  LLM Deep Analysis — FIXED system prompt
    # ─────────────────────────────────────────────────────────────────────────

    def _llm_deep_analysis(
        self,
        code:            str,
        language:        Language,
        issues:          List[Dict],
        metrics:         Dict,
        static_scores:   Dict[str, float],
        problem_context: Optional[str],
        expected_output: Optional[str],
        user_ctx:        Dict,
    ) -> Dict:

        issue_summary = "\n".join(
            f"- [{i['severity'].upper()}] Line {i.get('line','?')} | {i['category']}: {i['message']}"
            for i in issues[:15]
        ) or "No static issues found."

        system_prompt = f"""You are the Code Evaluation Agent inside aiTA — an AI teaching assistant for programming education in India.
Your job is to perform a thorough, educational code review for a {user_ctx['skill_level']}-level student.

Student profile:
- Skill level: {user_ctx['skill_level']}
- Languages they know: {', '.join(user_ctx['preferred_languages']) or 'general'}
- Learning goals: {', '.join(user_ctx['learning_goals']) or 'general programming'}

Static analysis already found these issues:
{issue_summary}

Static dimension scores (0-100): {json.dumps(static_scores)}

CRITICAL SCORING RULES — YOU MUST FOLLOW THESE:
1. Simple, correct code like print("Hello") MUST score 95-100 for correctness
2. Any code that produces correct output with no syntax errors = high correctness
3. Never penalise for simplicity — simple correct code is GOOD code
4. Do NOT include "security" in your scores — it is not a dimension
5. Score only: correctness, quality, efficiency, style, documentation
6. Be honest and encouraging — never demotivating

Your review MUST:
1. Assess CORRECTNESS — does the logic actually solve the problem / work?
2. Identify TIME and SPACE complexity (Big-O notation)
3. Point out ANTI-PATTERNS specific to {language.value} (if any)
4. List what the student did WELL (encouragement matters!)
5. Provide an IMPROVED version of the code with inline comments (if improvements exist)
6. Give 3-5 LEARNING POINTS matched to the student's skill level
7. Suggest specific RESOURCES/TOPICS for the student to study next

Tone: encouraging, specific, educational. Never demotivating.

You MUST respond with ONLY valid JSON in this exact structure:
{{
  "scores": {{
    "correctness":   <0-100 float, starts at 95+ for working code>,
    "quality":       <0-100 float>,
    "efficiency":    <0-100 float>,
    "style":         <0-100 float>,
    "documentation": <0-100 float>
  }},
  "time_complexity":  "<Big-O string or null>",
  "space_complexity": "<Big-O string or null>",
  "summary":          "<2-3 sentence overall verdict, warm and encouraging>",
  "detailed_feedback":"<full markdown feedback, structured with ## headings>",
  "corrected_code":   "<improved code with inline comments, or same code if already correct>",
  "key_improvements": ["improvement 1", "improvement 2"],
  "learning_points":  ["concept 1", "concept 2", "concept 3"],
  "best_practices_used": ["good thing 1", "good thing 2"],
  "anti_patterns":    ["pattern to avoid 1"],
  "suggested_resources": ["topic/resource 1", "topic/resource 2"]
}}"""

        context_block = ""
        if problem_context:
            context_block += f"\n\nProblem Statement:\n{problem_context}"
        if expected_output:
            context_block += f"\n\nExpected Output:\n{expected_output}"

        user_prompt = f"""Please evaluate this {language.value} code:
{context_block}

```{language.value}
{code}
```

Metrics from static analysis:
- Lines of code: {metrics['lines_of_code']}
- Comment ratio: {metrics['comment_ratio']:.1%}
- Cyclomatic complexity: {metrics['cyclomatic_complexity']}

Return ONLY valid JSON, no markdown fences, no extra text."""

        try:
            response = httpx.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       self.model,
                    "max_tokens":  MAX_TOKENS,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data        = response.json()
            raw_text    = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            clean = raw_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            parsed = json.loads(clean.strip())
            parsed["tokens_used"] = tokens_used
            return parsed

        except (httpx.HTTPStatusError, httpx.TimeoutException):
            return {
                "scores":              static_scores,
                "time_complexity":     None,
                "space_complexity":    None,
                "summary":             "Evaluated using static analysis (LLM unavailable).",
                "detailed_feedback":   "## Static Analysis Results\n\n" + issue_summary,
                "corrected_code":      None,
                "key_improvements":    [i["suggestion"] for i in issues[:5]],
                "learning_points":     [],
                "best_practices_used": [],
                "anti_patterns":       [],
                "suggested_resources": [],
                "tokens_used":         0,
            }
        except (json.JSONDecodeError, KeyError):
            return {
                "scores":              static_scores,
                "time_complexity":     None,
                "space_complexity":    None,
                "summary":             "Evaluation complete (LLM response parsing issue).",
                "detailed_feedback":   raw_text if 'raw_text' in dir() else "",
                "corrected_code":      None,
                "key_improvements":    [],
                "learning_points":     [],
                "best_practices_used": [],
                "anti_patterns":       [],
                "suggested_resources": [],
                "tokens_used":         0,
            }

    # ─────────────────────────────────────────────────────────────────────────
    #  User context & query helpers (unchanged)
    # ─────────────────────────────────────────────────────────────────────────

    def _get_user_context(self, user_id: int) -> Dict:
        user    = self.db.query(User).filter(User.id == user_id).first()
        profile = self.db.query(LearningProfile).filter(
            LearningProfile.user_id == user_id
        ).first()
        return {
            "username":            user.username if user else "student",
            "skill_level":         user.skill_level.value if user and user.skill_level else "beginner",
            "preferred_languages": user.preferred_languages if user else [],
            "learning_goals":      getattr(user, "learning_goals", []) or [],
            "weak_areas":          profile.weak_areas if profile else [],
        }

    def get_submissions(self, user_id: int, limit: int = 20) -> List[CodeSubmission]:
        return (
            self.db.query(CodeSubmission)
            .filter(CodeSubmission.user_id == user_id)
            .order_by(CodeSubmission.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_submission(self, submission_id: int, user_id: int) -> CodeSubmission:
        sub = self.db.query(CodeSubmission).filter(
            CodeSubmission.id      == submission_id,
            CodeSubmission.user_id == user_id,
        ).first()
        if not sub:
            raise ValueError("Submission not found.")
        return sub

    def get_user_stats(self, user_id: int) -> Dict:
        evals = (
            self.db.query(EvalHistoryEntry)
            .filter(EvalHistoryEntry.user_id == user_id)
            .order_by(EvalHistoryEntry.created_at.asc())
            .all()
        )
        submissions = self.db.query(CodeSubmission).filter(
            CodeSubmission.user_id == user_id
        ).all()
        evaluations = self.db.query(CodeEvaluation).filter(
            CodeEvaluation.user_id == user_id
        ).all()

        scores    = [e.overall_score for e in evals]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        best      = round(max(scores), 1) if scores else 0.0

        recent = scores[-5:]
        trend  = 0.0
        if len(recent) >= 2:
            trend = round((recent[-1] - recent[0]) / max(len(recent) - 1, 1), 2)

        languages_used = list({e.language.value for e in evals})

        all_issues = []
        for ev in evaluations:
            all_issues.extend(ev.issues or [])
        categories  = [i.get("category", "") for i in all_issues]
        most_common = [cat for cat, _ in Counter(categories).most_common(5)]

        return {
            "total_submissions":  len(submissions),
            "total_evaluations":  len(evaluations),
            "avg_overall_score":  avg_score,
            "best_score":         best,
            "languages_used":     languages_used,
            "most_common_issues": most_common,
            "improvement_trend":  trend,
            "recent_history":     evals[-10:],
        }