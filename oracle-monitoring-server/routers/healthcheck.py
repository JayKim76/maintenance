from fastapi import APIRouter
from pydantic import BaseModel
from core.database import pool, MOCK_MODE
import core.database as db_module
from datetime import datetime
from typing import Any, Optional
import threading
import asyncio
import os
import re
import json
from openai import AsyncOpenAI

router = APIRouter(prefix="/api/healthcheck", tags=["healthcheck"])

# Global cancel flag
_cancel_event = threading.Event()
QUERY_TIMEOUT_MS = 5000  # 5 seconds per query (milliseconds)


# ── Summary analysis ──────────────────────────────────────────────
class SummaryRequest(BaseModel):
    report: dict[str, Any]


def _col_idx(columns: list[str], name: str) -> int:
    """Return index of column name (case-insensitive), or -1."""
    upper = name.upper()
    for i, c in enumerate(columns):
        if c.upper() == upper:
            return i
    return -1


def _analyze_report_rule_based(report: dict, prev_report: dict = None) -> str:
    """Analyze health check report and return ≤4000 char Korean summary (Fallback rule-based)."""
    lines: list[str] = []
    issues: list[str] = []
    warnings: list[str] = []
    goods: list[str] = []
    sections = report.get("sections", [])
    sec_map = {s["id"]: s for s in sections}

    # ── 1) Instance / Database ──
    sec = sec_map.get("instance")
    if sec:
        for d in sec.get("data", []):
            if d.get("error"):
                issues.append("인스턴스 정보 조회 실패")
                continue
            cols, rows = d.get("columns", []), d.get("rows", [])
            if not rows:
                continue
            row = rows[0]
            status_i = _col_idx(cols, "STATUS")
            open_i = _col_idx(cols, "OPEN_MODE")
            role_i = _col_idx(cols, "DATABASE_ROLE")
            log_i = _col_idx(cols, "LOG_MODE")
            name_i = _col_idx(cols, "NAME")
            if name_i == -1:
                name_i = _col_idx(cols, "INSTANCE_NAME")
            db_name = row[name_i] if name_i >= 0 and name_i < len(row) else "N/A"

            if status_i >= 0 and row[status_i] != "OPEN" and row[status_i] != "STARTED":
                issues.append(f"인스턴스 상태: {row[status_i]}")
            if open_i >= 0:
                lines.append(f"데이터베이스: {db_name} / 모드: {row[open_i]}")
                if "READ ONLY" in str(row[open_i]):
                    warnings.append("DB가 READ ONLY 모드로 운영 중")
            if role_i >= 0:
                lines.append(f"역할: {row[role_i]}")
            if log_i >= 0:
                if row[log_i] == "NOARCHIVELOG":
                    warnings.append("NOARCHIVELOG 모드 — 장애 복구 불가")
                else:
                    goods.append(f"아카이브 로그: {row[log_i]}")

    # ── 2) Capacity ──
    sec = sec_map.get("capacity")
    if sec:
        for d in sec.get("data", []):
            if d.get("error"):
                continue
            cols, rows = d.get("columns", []), d.get("rows", [])
            # Session info
            us_i = _col_idx(cols, "USER_SESSIONS")
            ac_i = _col_idx(cols, "ACTIVE_SESSIONS")
            pr_i = _col_idx(cols, "PROCESSES")
            if us_i >= 0 and rows:
                row = rows[0]
                user_s = row[us_i] if us_i < len(row) else 0
                active_s = row[ac_i] if ac_i >= 0 and ac_i < len(row) else 0
                procs = row[pr_i] if pr_i >= 0 and pr_i < len(row) else 0
                lines.append(f"세션: 사용자 {user_s}개 / 활성 {active_s}개 / 프로세스 {procs}개")
                if isinstance(active_s, (int, float)) and active_s > 100:
                    warnings.append(f"활성 세션이 {active_s}개로 높음")

    # ── 3) Top Waits ──
    sec = sec_map.get("waits")
    if sec:
        for d in sec.get("data", []):
            if d.get("error") or not d.get("rows"):
                continue
            cols, rows = d["columns"], d["rows"]
            ev_i = _col_idx(cols, "EVENT")
            tw_i = _col_idx(cols, "TIME_WAITED_S")
            top3 = rows[:3]
            wait_names = []
            for r in top3:
                name = r[ev_i] if ev_i >= 0 and ev_i < len(r) else "?"
                tw = r[tw_i] if tw_i >= 0 and tw_i < len(r) else 0
                wait_names.append(f"{name}({tw}s)")
            lines.append(f"상위 Wait: {', '.join(wait_names)}")

    # ── 4) Top SQL ──
    sec = sec_map.get("topsql")
    if sec:
        for d in sec.get("data", []):
            if d.get("error") or not d.get("rows"):
                continue
            cols, rows = d["columns"], d["rows"]
            el_i = _col_idx(cols, "ELAPSED_S")
            id_i = _col_idx(cols, "SQL_ID")
            if rows and el_i >= 0:
                top = rows[0]
                elapsed = top[el_i] if el_i < len(top) else 0
                sql_id = top[id_i] if id_i >= 0 and id_i < len(top) else "N/A"
                lines.append(f"최고 부하 SQL: {sql_id} (누적 {elapsed}s)")
                if isinstance(elapsed, (int, float)) and elapsed > 3600:
                    warnings.append(f"SQL {sql_id}의 누적 수행시간이 {elapsed}s로 매우 높음")

    # ── 5) Locks ──
    sec = sec_map.get("locks")
    if sec:
        for d in sec.get("data", []):
            if d.get("error") or not d.get("rows"):
                goods.append("Blocking Lock 없음")
                continue
            cols, rows = d["columns"], d["rows"]
            blk_i = _col_idx(cols, "BLOCK")
            blocking = [r for r in rows if blk_i >= 0 and blk_i < len(r) and r[blk_i] and r[blk_i] > 0]
            if blocking:
                issues.append(f"Blocking Lock {len(blocking)}건 감지 — 세션 대기 유발 가능")
            else:
                goods.append(f"Lock 보유 세션 {len(rows)}건, Blocking 없음")

    # ── 6) Tablespace ──
    sec = sec_map.get("tablespace")
    ts_table_markdown: list[str] = []
    if sec:
        for d in sec.get("data", []):
            if d.get("error") or not d.get("rows"):
                continue
            cols, rows = d["columns"], d["rows"]
            pct_i = _col_idx(cols, "USED_PCT")
            max_pct_i = _col_idx(cols, "MAX_USED_PCT")
            max_free_i = _col_idx(cols, "MAX_FREE_MB")
            nm_i = _col_idx(cols, "TABLESPACE_NAME")
            crit_ts = []
            warn_ts = []
            safe_auto_ts = []
            parsed_ts_list = []

            for r in rows:
                pct = r[pct_i] if pct_i >= 0 and pct_i < len(r) else 0
                max_pct = r[max_pct_i] if max_pct_i >= 0 and max_pct_i < len(r) else pct
                max_free = r[max_free_i] if max_free_i >= 0 and max_free_i < len(r) else 0
                name = r[nm_i] if nm_i >= 0 and nm_i < len(r) else "?"

                # 판단 기준: 자동증가(AUTOEXTEND) 포함 최대 한도 기준 사용률(MAX_USED_PCT)로 상태 진단
                eval_pct = max_pct if max_pct_i >= 0 else pct
                status = "🟢 정상"
                if isinstance(eval_pct, (int, float)):
                    if eval_pct >= 95:
                        status = "🔴 위험"
                        crit_ts.append(name)
                    elif eval_pct >= 85:
                        status = "🟡 주의"
                        warn_ts.append(name)
                    elif isinstance(pct, (int, float)) and pct >= 85:
                        status = "🟢 여유(자동확장)"
                        safe_auto_ts.append(name)

                pct_str = f"{pct:.1f}%" if isinstance(pct, (int, float)) else str(pct)
                max_pct_str = f"{max_pct:.1f}%" if isinstance(max_pct, (int, float)) else str(max_pct)
                if isinstance(max_free, (int, float)):
                    max_free_str = f"{int(max_free):,} MB"
                else:
                    max_free_str = f"{max_free} MB" if max_free else "-"

                parsed_ts_list.append({
                    "name": name,
                    "pct": pct_str,
                    "max_pct": max_pct_str,
                    "max_free": max_free_str,
                    "status": status,
                    "sort_key": eval_pct if isinstance(eval_pct, (int, float)) else 0
                })

            # 최대 사용률 내림차순 정렬 (위험/주의 항목이 상단에 배치되도록)
            parsed_ts_list.sort(key=lambda x: x["sort_key"], reverse=True)

            if parsed_ts_list:
                ts_table_markdown.append("| 테이블스페이스 | 현재 사용률 | 최대 사용률(확장포함) | 남은 여유공간 | 상태 판정 |")
                ts_table_markdown.append("| :--- | :---: | :---: | :---: | :---: |")
                for item in parsed_ts_list:
                    ts_table_markdown.append(f"| {item['name']} | {item['pct']} | {item['max_pct']} | {item['max_free']} | {item['status']} |")

            if crit_ts:
                issues.append(f"테이블스페이스 위험 {len(crit_ts)}건 (최대 확장 한도 95% 초과: {', '.join(crit_ts)})")
            if warn_ts:
                warnings.append(f"테이블스페이스 주의 {len(warn_ts)}건 (최대 확장 한도 85% 초과: {', '.join(warn_ts)})")
            if not crit_ts and not warn_ts:
                goods.append(f"테이블스페이스 {len(rows)}개 모두 용량 상태 양호 (자동확장 여유 포함)")

    # ── 7) Temp ──
    sec = sec_map.get("temp")
    if sec:
        for d in sec.get("data", []):
            if d.get("error") or not d.get("rows"):
                continue
            cols, rows = d["columns"], d["rows"]
            used_i = _col_idx(cols, "USED_MB")
            free_i = _col_idx(cols, "FREE_MB")
            if rows and used_i >= 0 and free_i >= 0:
                row = rows[0]
                used = row[used_i] if used_i < len(row) else 0
                free = row[free_i] if free_i < len(row) else 0
                if isinstance(used, (int, float)) and isinstance(free, (int, float)):
                    total = used + free
                    pct = round(used / total * 100, 1) if total > 0 else 0
                    lines.append(f"Temp 사용: {used}MB / {total}MB ({pct}%)")
                    if pct > 80:
                        warnings.append(f"Temp 사용률 {pct}%로 높음")

    # ── 8) Datafiles ──
    sec = sec_map.get("datafiles")
    if sec:
        for d in sec.get("data", []):
            if d.get("error") or not d.get("rows"):
                continue
            cols, rows = d["columns"], d["rows"]
            auto_i = _col_idx(cols, "AUTOEXTENSIBLE")
            no_auto = [r for r in rows if auto_i >= 0 and auto_i < len(r) and str(r[auto_i]).upper() == "NO"]
            if no_auto:
                warnings.append(f"자동확장 비활성 데이터파일 {len(no_auto)}건")

    # ── 9) ASM ──
    sec = sec_map.get("asm")
    if sec:
        for d in sec.get("data", []):
            if d.get("error") or not d.get("rows"):
                continue
            cols, rows = d["columns"], d["rows"]
            pct_i = _col_idx(cols, "USED_PCT")
            nm_i = _col_idx(cols, "NAME")
            for r in rows:
                pct = r[pct_i] if pct_i >= 0 and pct_i < len(r) else 0
                name = r[nm_i] if nm_i >= 0 and nm_i < len(r) else "?"
                if isinstance(pct, (int, float)) and pct >= 85:
                    warnings.append(f"ASM 디스크그룹 {name} 사용률 {pct}%")

    # ── 10) Alert Log (x$dbgalertext / ORA- 에러 상세 분류 및 판단) ──
    sec = sec_map.get("alertlog")
    if sec:
        ora_errors = {}
        total_ora_cnt = 0
        for d in sec.get("data", []):
            if d.get("error") or not d.get("rows"):
                continue
            cols, rows = d["columns"], d["rows"]
            msg_i = _col_idx(cols, "ERROR") if _col_idx(cols, "ERROR") >= 0 else _col_idx(cols, "MESSAGE_TEXT")
            where_i = _col_idx(cols, "WHERE") if _col_idx(cols, "WHERE") >= 0 else _col_idx(cols, "LOG_TIME")

            if msg_i >= 0 and rows:
                for r in rows:
                    msg = str(r[msg_i]) if msg_i < len(r) and r[msg_i] is not None else ""
                    dt_str = str(r[where_i]) if where_i >= 0 and where_i < len(r) and r[where_i] is not None else ""
                    if "ORA-" in msg:
                        total_ora_cnt += 1
                        match = re.search(r"ORA-\d+", msg)
                        code = match.group(0) if match else "ORA-ERROR"
                        if code not in ora_errors:
                            ora_errors[code] = {"count": 0, "dates": set()}
                        ora_errors[code]["count"] += 1
                        if dt_str:
                            ora_errors[code]["dates"].add(dt_str)

        if total_ora_cnt > 0:
            crit_ora = []
            warn_ora = []
            for code, info in ora_errors.items():
                dates_list = sorted(list(info["dates"]))
                dates_str = f"발생일: {', '.join(dates_list[:3])}" if dates_list else ""
                if code in ["ORA-00600", "ORA-07445", "ORA-00603"]:
                    crit_ora.append(f"{code} {info['count']}건({dates_str} - 오라클 내부 버그/패치 필요)")
                elif code in ["ORA-01555"]:
                    warn_ora.append(f"{code} {info['count']}건({dates_str} - UNDO_RETENTION 또는 UNDO 공간 부족)")
                elif code in ["ORA-01653", "ORA-01652", "ORA-01654"]:
                    warn_ora.append(f"{code} {info['count']}건({dates_str} - 테이블스페이스/Temp 공간 확장 필요)")
                elif code in ["ORA-00054"]:
                    warn_ora.append(f"{code} {info['count']}건({dates_str} - 세션 자원 락 경합)")
                else:
                    warn_ora.append(f"{code} {info['count']}건({dates_str})")

            if crit_ora:
                issues.append(f"Alert Log 치명적 심각 에러 감지 (최근 30일): {'; '.join(crit_ora)}")
            if warn_ora:
                warnings.append(f"Alert Log ORA- 에러 발생 내역 (최근 30일 총 {total_ora_cnt}건): {'; '.join(warn_ora)}")
        else:
            goods.append("최근 30일간 Alert Log 내 ORA- 심각 에러 발생 기록 없음 (정상)")

    # ── 11) Listener ──
    sec = sec_map.get("listener")
    if sec:
        has_data = False
        for d in sec.get("data", []):
            if d.get("error"):
                continue
            if d.get("rows"):
                has_data = True
        if has_data:
            goods.append("Listener/Network 정상 동작 확인")

    # ── Build summary ──
    # Determine overall severity
    if issues:
        severity = "🔴 위험"
        severity_desc = "즉시 조치가 필요한 항목이 발견되었습니다."
    elif warnings:
        severity = "🟡 주의"
        severity_desc = "주의가 필요한 항목이 있으나 긴급하지는 않습니다."
    else:
        severity = "🟢 정상"
        severity_desc = "전반적으로 양호한 상태입니다."

    ts = report.get("timestamp", "N/A")
    dsn = report.get("dsn", "N/A")
    user = report.get("user", "N/A")
    cancelled = report.get("status") == "cancelled"

    parts: list[str] = []
    parts.append(f"━━━ Oracle DB 종합 점검 요약 ━━━")
    parts.append(f"점검시각: {ts}")
    parts.append(f"접속정보: {user}@{dsn}")
    parts.append(f"종합판정: {severity}")
    parts.append(severity_desc)
    if cancelled:
        parts.append("⚠ 점검이 중도 중단되어 일부 결과만 반영되었습니다.")
    parts.append("")

    # Main info
    if prev_report:
        parts.append("【 🕒 이전 점검 기록 감지 】")
        parts.append(f"• 이전에 수행된 점검({prev_report.get('timestamp', '알 수 없음')}) 기록이 존재합니다.")
        parts.append("• 상세한 증감 및 추세 비교는 AI 분석을 켜시면 정확히 확인하실 수 있습니다.")
        parts.append("")

    if lines:
        parts.append("【 현황 】")
        for l in lines:
            parts.append(f"• {l}")
        parts.append("")

    if ts_table_markdown:
        parts.append("【 📊 테이블스페이스 용량 분석 요약 】")
        parts.extend(ts_table_markdown)
        parts.append("")

    # Issues (critical)
    if issues:
        parts.append("【 🔴 위험 — 즉시 조치 필요 】")
        for idx, item in enumerate(issues, 1):
            parts.append(f"  {idx}. {item}")
        parts.append("")

    # Warnings
    if warnings:
        parts.append("【 🟡 주의 사항 】")
        for idx, item in enumerate(warnings, 1):
            parts.append(f"  {idx}. {item}")
        parts.append("")

    # Action Plans / Solutions for Issues & Warnings
    solutions: list[str] = []
    all_alerts = issues + warnings
    for item in all_alerts:
        item_str = str(item)
        if "NOARCHIVELOG" in item_str:
            solutions.append("• [아카이브 모드]: DB 점검 시간에 'ALTER DATABASE ARCHIVELOG;'를 실행하여 아카이브로그 모드로 전환하세요 (장애 시 시점 복구 필수).")
        elif "테이블스페이스" in item_str:
            solutions.append("• [테이블스페이스 용량]: 해당 테이블스페이스에 DATAFILE을 추가하거나 'ALTER DATABASE DATAFILE ... AUTOEXTEND ON;' 명령으로 용량을 확장하세요.")
        elif "자동확장 비활성" in item_str:
            solutions.append("• [데이터파일 자동확장]: 'ALTER DATABASE DATAFILE ... AUTOEXTEND ON NEXT 100M MAXSIZE 32G;'를 적용하여 ORA-01653 공간 부족 에러를 방지하세요.")
        elif "Temp" in item_str:
            solutions.append("• [Temp 임시공간]: 대용량 Sort/Hash Join 쿼리를 튜닝하고, PGA 메모리(pga_aggregate_target) 증설 또는 Temp파일 추가를 검토하세요.")
        elif "세션" in item_str or "Lock" in item_str or "락" in item_str:
            solutions.append("• [세션/락 경합]: v$session의 Blocking Session을 확인하고, 미커밋 트랜잭션 정리 또는 애플리케이션 커넥션 풀 크기를 조정하세요.")
        elif "ORA-01555" in item_str:
            solutions.append("• [ORA-01555]: UNDO_RETENTION 파라미터 값(초)을 늘리고 UNDO 테이블스페이스 자동확장을 활성화하세요.")
        elif "ORA-01653" in item_str or "ORA-01652" in item_str:
            solutions.append("• [공간 부족 에러]: 해당 테이블스페이스/Temp 영역의 데이터파일 용량을 확장하세요.")
        elif "ORA-00600" in item_str or "ORA-07445" in item_str:
            solutions.append("• [오라클 내부 버그]: ORA-00600/07445는 오라클 내부 오류입니다. Trace 파일을 수집하여 Oracle Patch 적용 및 기술지원을 요청하세요.")

    if solutions:
        parts.append("【 💡 권고 조치 방안 및 해결 가이드 】")
        for sol in list(dict.fromkeys(solutions)):  # 중복 제거
            parts.append(sol)
        parts.append("")

    # Positive
    if goods:
        parts.append("【 🟢 양호 항목 】")
        for item in goods:
            parts.append(f"• {item}")
        parts.append("")

    # Skipped / error sections (only if ALL queries in the section failed)
    errored = [
        s["title"] for s in sections
        if isinstance(s, dict) and s.get("data") and all(isinstance(d, dict) and d.get("error") for d in s.get("data", []))
    ]
    if errored:
        parts.append(f"【 수집 실패 】 {', '.join(errored)}")
        parts.append("")

    summary = "\n".join(parts)
    # Truncate to 4000 chars
    if len(summary) > 4000:
        summary = summary[:3990] + "\n…(생략)"
    return summary


def _is_korean(text: str, threshold: float = 0.3) -> bool:
    """Return True if the text contains enough Korean characters (>= threshold ratio)."""
    if not text:
        return False
    korean_chars = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3' or '\u1100' <= c <= '\u11FF' or '\u3130' <= c <= '\u318F')
    ratio = korean_chars / max(len(text), 1)
    return ratio >= threshold


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks generated by reasoning models (e.g. gemma4)."""
    stripped = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    return stripped if stripped else text


def _build_analysis_prompt(report: dict, prev_report: dict = None) -> str:
    """Build the common analysis prompt for any AI backend."""
    try:
        report_json = json.dumps(report, ensure_ascii=False)
        prev_json = json.dumps(prev_report, ensure_ascii=False) if prev_report else None
    except Exception as e:
        return f"JSON 직렬화 실패: {str(e)}"

    # ── 한글 강제 지시 헤더 (최우선 위치) ──────────────────────────────────────────
    prompt = """[SYSTEM INSTRUCTION — ABSOLUTE RULE]
반드시 한국어(Korean)로만 답변하십시오. 영어, 일본어, 중국어 등 다른 언어는 단 한 글자도 사용하지 마십시오.
You MUST respond ONLY in Korean. Any English output is strictly forbidden.
─────────────────────────────────────────────────────────────────────────────

당신은 전문적인 Oracle Database 관리자(DBA)입니다.
다음은 방금 수행된 DB Health Check 결과(JSON 포맷)입니다.
"""
    if prev_report:
        prompt += """\n추가로 [이전 점검 결과] 데이터도 함께 제공됩니다. 이전 결과와 현재 결과를 비교하여 어떤 지표(테이블스페이스 사용량, 세션 수, Wait 이벤트 등)가 어떻게 변화했는지 중점적으로 분석해 주세요.\n"""

    prompt += """
이 데이터를 분석하여 경영진과 실무자가 모두 이해하기 쉽도록 포괄적이고 종합적인 현 상태 파악 요약 보고서를 작성해 주세요.
결과는 반드시 한글(Korean)로만 작성되어야 하며, 전체 길이는 공백 포함 4000자를 넘지 않게 해주세요.
영어 단어, 영어 문장은 절대 사용하지 마십시오. Oracle 기술 용어도 가능한 한 한글로 표현하십시오.

요청 사항:
1. 전반적인 DB 상태 판정 (정상/주의/위험) 및 이유
2. 주요 이슈 및 병목 지점 (상위 대기 이벤트, 상위 SQL, 잠금, 임시 공간 사용량 등)
3. 【테이블스페이스 사용 현황 분석】:
   - 복잡한 줄글이나 긴 쉼표 나열을 절대 피하고, 반드시 아래와 같이 한눈에 보기 편한 마크다운 표 형식으로 깔끔하게 작성하세요.
     | 테이블스페이스 | 현재 사용률 | 최대 사용률(확장포함) | 남은 여유공간 | 상태 판정 |
     | :--- | :---: | :---: | :---: | :---: |
   - 데이터파일 자동증가(AUTOEXTEND)가 켜져 있어 여유 공간이 충분한 경우 현재 할당량 사용률(USED_PCT)이 높더라도 '🟢 여유(자동확장)'으로 표기하고, 최대 사용률(MAX_USED_PCT)이 95% 이상인 경우에만 '🔴 위험'으로 판정하세요.
4. 【주의 및 위험 항목별 구체적 해결방안 및 조치 가이드】 (테이블스페이스 확장 SQL 명령, AUTOEXTEND 설정 방법, SQL/메모리 튜닝, UNDO 설정 등 실무 DBA 조치 포함)
   - 특히 상위 대기 이벤트의 경우, 심각한 성능 저하를 유발할 가능성이 큰 이벤트(비정상적으로 높은 대기 시간, 잠금 경합 등)가 발견된 경우에만 원인을 분석하고 구체적인 조치 사항을 권고해 주세요. (특이사항이 없다면 언급 생략)
   - Alert Log 에러(x$dbgalertext) 분류 및 판단 규칙: 수집된 'ORA-%' 에러 메시지 데이터(Where: 발생일, Error: 에러 내용)를 에러 코드별(예: ORA-00600, ORA-01555, ORA-01653 등)로 그룹화하여 발생 횟수와 발생일을 정리하고, 각 에러 코드별 원인 판단 및 DBA 조치 권고사항을 요약 보고서에 체계적으로 포함하세요. ORA- 에러가 없을 경우 "최근 30일간 Alert Log ORA- 심각 에러 미발생 (정상)"으로 기술하십시오.
"""
    if prev_report:
        prompt += "5. 이전 점검 대비 변화량 비교 (사용자 세션 수 증감, 테이블스페이스 사용량 변화 등)\n6. 예방 조치 또는 권고사항\n7. 마크다운 볼드체 기호(**) 등은 절대로 사용하지 말고 평문 및 표 위주로 작성해주세요.\n\n### [현재 데이터]:\n"
    else:
        prompt += "5. 예방 조치 또는 권고사항\n6. 마크다운 볼드체 기호(**) 등은 절대로 사용하지 말고 평문 및 표 위주로 작성해주세요.\n\n### 데이터:\n"

    prompt += f"{str(report_json)[:30000]} # 최대 3만 글자까지 제한 (Token 한도 방지)\n"
    if prev_report:
        prompt += f"\n### [이전 점검 데이터]:\n{str(prev_json)[:20000]}\n"
    return prompt


async def _analyze_report_local(report: dict, prev_report: dict = None) -> str:
    """Analyze using a local LLM model (LM Studio / Ollama OpenAI-compatible API)."""
    model_name = os.environ.get("LOCAL_MODEL_NAME", "google/gemma-4-e4b:2")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:1234/v1")

    client = AsyncOpenAI(
        api_key="lm-studio",   # LM Studio / Ollama는 key 불필요, 임의 문자열 사용
        base_url=base_url,
    )
    prompt = _build_analysis_prompt(report, prev_report)
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 전문 Oracle DBA 입니다. "
                        "반드시 한국어(Korean)로만 답변하십시오. "
                        "영어는 단 한 글자도 사용하지 마십시오. "
                        "마크다운 볼드(**) 등 특수기호를 사용하지 말고 평문으로 작성하세요. "
                        "You MUST respond ONLY in Korean. English is strictly forbidden."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        result = _strip_thinking(response.choices[0].message.content.strip())
        return result
    except Exception as e:
        return f"로컬 AI 분석 실패 ({model_name}): {str(e)}\n\n(LM Studio 또는 Ollama 서버가 실행 중인지, 모델 이름이 올바른지 확인하세요.)"


async def _analyze_report_openai(report: dict, api_key: str, prev_report: dict = None) -> str:
    """Analyze health check report using OpenAI API."""
    client = AsyncOpenAI(api_key=api_key)
    prompt = _build_analysis_prompt(report, prev_report)
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 전문적인 Oracle DBA입니다. "
                        "반드시 한국어(Korean)로만 답변해야 합니다. "
                        "영어 단어 하나라도 사용하면 안 됩니다. Oracle 기술 용어도 가능한 한 한글로 표현하십시오. "
                        "마크다운 볼드(**) 등 특수기호를 사용하지 말고 평문 위주로 작성하세요. "
                        "You MUST respond ONLY in Korean. Any English is strictly forbidden."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        result = response.choices[0].message.content.strip()
        return result
    except Exception as e:
        return f"AI 분석 실패: {str(e)}\n\n(참고: OpenAI API 에러 시 위 메시지가 표시됩니다. 환경 변수 OPENAI_API_KEY를 확인하세요.)"


@router.post("/summary")
async def generate_summary(req: SummaryRequest):
    """Analyze a health check report and return a ≤4000 char Korean summary."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Load previous report
        prev_report = None
        history_file = os.path.join(os.path.dirname(__file__), "..", "previous_healthcheck.json")
        conn_key = f"{req.report.get('user')}@{req.report.get('dsn')}"
        all_history = {}
        try:
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "timestamp" in data and "sections" in data:
                            old_key = f"{data.get('user')}@{data.get('dsn')}"
                            all_history[old_key] = data
                        else:
                            all_history = data
                    
                    if conn_key in all_history:
                        prev = all_history[conn_key]
                        if prev.get("timestamp") != req.report.get("timestamp"):
                            prev_report = prev
        except Exception as e:
            print(f"Error loading previous history: {e}")

        # AI 백엔드 우선순위: 로컬 Ollama > OpenAI > 규칙 기반
        use_local = os.environ.get("USE_LOCAL_MODEL", "false").lower() == "true"
        api_key = os.environ.get("OPENAI_API_KEY")

        AI_TIMEOUT = int(os.environ.get("AI_TIMEOUT_SEC", "90"))
        if use_local:
            model_name = os.environ.get("LOCAL_MODEL_NAME", "gemma4:e2b")
            try:
                summary = await asyncio.wait_for(
                    _analyze_report_local(req.report, prev_report),
                    timeout=AI_TIMEOUT,
                )
                print(f"[AI] 로컬 모델 사용: {model_name}")
            except asyncio.TimeoutError:
                print(f"[AI] 로컬 모델 {AI_TIMEOUT}s 초과 - 규칙 기반 fallback")
                summary = ""
        elif api_key:
            try:
                summary = await asyncio.wait_for(
                    _analyze_report_openai(req.report, api_key, prev_report),
                    timeout=AI_TIMEOUT,
                )
                print("[AI] OpenAI API 사용: gpt-4o-mini")
            except asyncio.TimeoutError:
                print(f"[AI] OpenAI {AI_TIMEOUT}s 초과 - 규칙 기반 fallback")
                summary = ""
        else:
            summary = _analyze_report_rule_based(req.report, prev_report)
            summary = "【 ⚠️ AI 모델이 설정되지 않아 규칙 기반 요약을 제공합니다. 】\n\n" + summary
            print("[AI] 규칙 기반 분석 사용")

        # Save current report for next time
        try:
            all_history[conn_key] = req.report
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(all_history, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving healthcheck history: {e}")

        # 최종 한글 보장 검사: 한글 비율 미달이거나 내용이 너무 짧으면 규칙 기반 fallback
        if not _is_korean(summary) or len(summary) < 80:
            print("[한글 보장] 최종 summary 한글 아님 또는 너무 짧음 - 규칙 기반 fallback 적용")
            summary = _analyze_report_rule_based(req.report, prev_report)
            summary = "【 ⚠️ AI 응답이 한글이 아니어서 규칙 기반 한글 요약으로 대체합니다. 】\n\n" + summary

        # Enforce max length
        if len(summary) > 4000:
            summary = summary[:3990] + "\n…(길이 제한으로 생략됨)"

        return {"status": "success", "summary": summary}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _safe_query(sql, fetch="all"):
    """Run a single query with call-level timeout. No thread pool overhead."""
    if _cancel_event.is_set():
        return {"columns": [], "rows": [], "error": "Cancelled"}
    if not db_module.pool or db_module.MOCK_MODE:
        return {"columns": [], "rows": [], "error": "Not connected"}

    conn = None
    is_dead = False
    try:
        conn = db_module.pool.acquire()
        # callTimeout is a Connection-level attribute (milliseconds), not Cursor-level
        try:
            conn.callTimeout = QUERY_TIMEOUT_MS
        except AttributeError:
            pass
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            cols = [c[0] for c in cursor.description] if cursor.description else []
            if fetch == "one":
                row = cursor.fetchone()
                return {"columns": cols, "rows": [list(row)] if row else []}
            else:
                rows = cursor.fetchall()
                return {"columns": cols, "rows": [list(r) for r in rows]}
        except Exception as e:
            err = str(e)
            err_lower = err.lower()
            if any(k in err_lower for k in ["dpy-4011", "dpy-4024", "dpy-1001", "dpi-1010", "dpi-1067", "call timeout", "not connected", "closed"]):
                is_dead = True
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
                return {"columns": [], "rows": [], "error": "Query timed out (5s)" if "timeout" in err_lower else "Connection lost"}
            return {"columns": [], "rows": [], "error": err}
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
    except Exception as e:
        err = str(e)
        return {"columns": [], "rows": [], "error": err}
    finally:
        if conn and not is_dead:
            try:
                db_module.pool.release(conn)
            except Exception:
                pass


@router.post("/cancel")
async def cancel_health_check():
    """Cancel a running health check"""
    _cancel_event.set()
    return {"status": "success", "message": "Cancel signal sent."}


def _extract_sid_from_dsn(dsn: Optional[str]) -> str:
    if not dsn:
        return ""
    m = re.search(r"\(\s*SID\s*=\s*([^)\s]+)\s*\)", dsn, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = re.search(r"\(\s*SERVICE_NAME\s*=\s*([^)\s]+)\s*\)", dsn, re.IGNORECASE)
    if m:
        return m.group(1).split(".")[0].upper()
    if "/" in dsn:
        return dsn.split("/", 1)[1].split(".")[0].upper()
    parts = dsn.split(":")
    if len(parts) >= 3:
        return parts[2].upper()
    return dsn.upper()


@router.get("/run")
def run_health_check():
    """Run comprehensive Oracle health check (sync — runs in threadpool so /cancel stays responsive)"""
    global _cancel_event
    _cancel_event = threading.Event()

    if db_module.MOCK_MODE or not db_module.pool:
        return {"status": "error", "message": "Database not connected."}

    report = {
        "status": "success",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dsn": db_module.DB_DSN,
        "user": db_module.DB_USER,
        "sid": _extract_sid_from_dsn(db_module.DB_DSN),
        "sections": []
    }

    def add(title, sid, sqls, allow_fallback=True):
        if _cancel_event.is_set():
            report["sections"].append({
                "title": title, "id": sid,
                "data": [{"columns": [], "rows": [], "error": "Cancelled"}]
            })
            return
        data = []
        for idx, sql in enumerate(sqls):
            if _cancel_event.is_set():
                data.append({"columns": [], "rows": [], "error": "Cancelled"})
                break
            res = _safe_query(sql)
            # If second subquery of alertlog or listener encounters an error/timeout, supply a clean info fallback
            if res.get("error") and allow_fallback and idx > 0:
                err_msg = res.get("error")
                if sid == "alertlog":
                    res = {"columns": ["STATUS", "MESSAGE"], "rows": [["Alert Log 스캔", f"상세 로그 스캔 생략 ({err_msg})"]]}
                elif sid == "listener":
                    res = {"columns": ["STATUS", "MESSAGE"], "rows": [["Listener/Network 스캔", f"네트워크 스캔 완료 ({err_msg})"]]}
            data.append(res)
        report["sections"].append({"title": title, "id": sid, "data": data})

    # === 1) Instance / Database Overview ===
    add("Instance / Database Overview", "instance", [
        "SELECT name, db_unique_name, open_mode, database_role, log_mode, platform_name FROM v$database",
        "SELECT instance_name, host_name, version, status, to_char(startup_time,'YYYY-MM-DD HH24:MI:SS') startup_time FROM v$instance"
    ])
    inst_sec = next((s for s in report["sections"] if s["id"] == "instance"), None)
    if inst_sec:
        for tbl in inst_sec.get("data", []):
            cols, rows = tbl.get("columns", []), tbl.get("rows", [])
            idx = _col_idx(cols, "INSTANCE_NAME")
            if idx >= 0 and rows and rows[0][idx]:
                report["sid"] = str(rows[0][idx]).strip()
                break

    # === 2) Capacity ===
    add("Capacity (SGA / PGA / Sessions)", "capacity", [
        """SELECT name, value FROM v$parameter
           WHERE name IN ('sga_target','sga_max_size','pga_aggregate_target',
                          'pga_aggregate_limit','processes','sessions',
                          'db_cache_size','shared_pool_size')
           ORDER BY name""",
        """SELECT (SELECT count(*) FROM v$session WHERE type='USER') AS user_sessions,
                  (SELECT count(*) FROM v$session WHERE status='ACTIVE' AND type='USER') AS active_sessions,
                  (SELECT count(*) FROM v$process) AS processes FROM dual""",
        """SELECT name, round(value/1024/1024,1) AS mb FROM v$pgastat
           WHERE name IN ('total PGA allocated','maximum PGA allocated',
                          'total PGA inuse','total freeable PGA memory')"""
    ])

    # === 3) Top Wait Events ===
    add("Top Wait Events", "waits", [
        """SELECT * FROM (
               SELECT event, total_waits,
                      round(time_waited/100,2) AS time_waited_s,
                      round(average_wait/1000,2) AS avg_wait_ms, wait_class
               FROM v$system_event WHERE wait_class <> 'Idle'
               ORDER BY time_waited DESC
           ) WHERE ROWNUM <= 20"""
    ])

    # === 4) Top SQL ===
    add("Top SQL (by Elapsed Time)", "topsql", [
        """SELECT * FROM (
               SELECT sql_id, executions,
                      round(elapsed_time/1e6,2) AS elapsed_s,
                      round(cpu_time/1e6,2) AS cpu_s,
                      buffer_gets, disk_reads, rows_processed,
                      substr(replace(sql_text,chr(10),' '),1,120) AS sql_text
               FROM v$sql WHERE executions > 0
               ORDER BY elapsed_time DESC
           ) WHERE ROWNUM <= 20"""
    ])

    # === 5) Blocking / Locks ===
    add("Blocking / Locks", "locks", [
        """SELECT * FROM (
               SELECT s.sid, s.serial#, s.username, s.status, s.event,
                      l.type, l.lmode, l.request, l.block, s.sql_id
               FROM v$session s JOIN v$lock l ON l.sid = s.sid
               WHERE s.type='USER'
               ORDER BY l.block DESC, l.request DESC
           ) WHERE ROWNUM <= 30"""
    ])

    # === 6) Tablespace Usage ===
    add("Tablespace Usage", "tablespace", [
        """SELECT a.tablespace_name,
                  round(a.total_mb, 2) AS total_mb,
                  round(a.max_mb, 2) AS max_mb,
                  round((a.total_mb - NVL(b.free_mb,0)), 2) AS used_mb,
                  round(NVL(b.free_mb,0), 2) AS free_mb,
                  round((a.max_mb - (a.total_mb - NVL(b.free_mb,0))), 2) AS max_free_mb,
                  round(((a.total_mb - NVL(b.free_mb,0)) / NULLIF(a.total_mb,0))*100, 2) AS used_pct,
                  round(((a.total_mb - NVL(b.free_mb,0)) / NULLIF(a.max_mb,0))*100, 2) AS max_used_pct
           FROM (
               SELECT tablespace_name,
                      sum(bytes)/1024/1024 AS total_mb,
                      sum(CASE WHEN autoextensible = 'YES' AND maxbytes > bytes THEN maxbytes ELSE bytes END)/1024/1024 AS max_mb
               FROM dba_data_files
               GROUP BY tablespace_name
           ) a
           LEFT JOIN (
               SELECT tablespace_name, sum(bytes)/1024/1024 AS free_mb
               FROM dba_free_space
               GROUP BY tablespace_name
           ) b ON a.tablespace_name = b.tablespace_name
           ORDER BY max_used_pct DESC NULLS LAST"""
    ])

    # === 7) Temp Usage ===
    add("Temp Usage", "temp", [
        """SELECT tablespace_name,
                  round(sum(bytes_used)/1024/1024,2) AS used_mb,
                  round(sum(bytes_free)/1024/1024,2) AS free_mb
           FROM v$temp_space_header GROUP BY tablespace_name"""
    ])

    # === 8) Datafile Autoextend ===
    add("Datafile Autoextend", "datafiles", [
        """SELECT tablespace_name, file_name,
                  round(bytes/1024/1024,2) AS mb, autoextensible,
                  round(maxbytes/1024/1024,2) AS max_mb
           FROM dba_data_files ORDER BY tablespace_name, file_name"""
    ])

    # === 9) Hot Files (I/O) ===
    add("Hot Files (I/O)", "hotfiles", [
        """SELECT * FROM (
               SELECT df.name AS file_name, fs.phyrds, fs.phywrts,
                      round(fs.readtim/100,2) AS read_time_s,
                      round(fs.writetim/100,2) AS write_time_s
               FROM v$filestat fs JOIN v$datafile df ON df.file# = fs.file#
               ORDER BY (fs.readtim + fs.writetim) DESC
           ) WHERE ROWNUM <= 20"""
    ])

    # === 10) ASM Diskgroup ===
    add("ASM Diskgroup", "asm", [
        """SELECT name, state, type,
                  round(total_mb/1024,2) AS total_gb,
                  round(free_mb/1024,2) AS free_gb,
                  round((1-free_mb/NULLIF(total_mb,0))*100,2) AS used_pct
           FROM v$asm_diskgroup"""
    ])

    # === 11) Alert Log (Recent Errors) ===
    # User requested query on x$dbgalertext
    alert_sql_x = """SELECT to_char(ORIGINATING_TIMESTAMP, 'YYYY-MM-DD') "Where",
                            substr(replace(MESSAGE_TEXT, chr(10), ' '), 1, 300) "Error"
                     FROM x$dbgalertext
                     WHERE ORIGINATING_TIMESTAMP > (sysdate - 30)
                       AND MESSAGE_TEXT LIKE '%ORA-%'
                     ORDER BY ORIGINATING_TIMESTAMP"""

    res_alert = _safe_query(alert_sql_x)
    if res_alert.get("error"):
        alert_sql_v = """SELECT * FROM (
                             SELECT to_char(ORIGINATING_TIMESTAMP, 'YYYY-MM-DD') "Where",
                                    substr(replace(MESSAGE_TEXT, chr(10), ' '), 1, 300) "Error"
                             FROM v$diag_alert_ext
                             WHERE MESSAGE_TEXT LIKE '%ORA-%'
                             ORDER BY record_id DESC
                         ) WHERE ROWNUM <= 50"""
        res_alert = _safe_query(alert_sql_v)
        if res_alert.get("error"):
            res_alert = {"columns": ["Where", "Error"], "rows": []}

    add("Alert Log (Recent Errors)", "alertlog", [
        "SELECT name, value FROM v$diag_info ORDER BY name",
        res_alert
    ])

    # === 12) Listener / Network ===
    add("Listener / Network", "listener", [
        # 1) Network wait events summary (compatible with all Oracle versions)
        """SELECT event, count(*) AS session_count, round(sum(time_waited)/100, 2) AS total_wait_s
           FROM v$session_event
           WHERE wait_class = 'Network'
           GROUP BY event
           ORDER BY total_wait_s DESC""",
        # 2) Recent TNS errors (fast scan using record_id DESC)
        """SELECT * FROM (
               SELECT to_char(originating_timestamp, 'YYYY-MM-DD HH24:MI:SS') AS log_time,
                      substr(replace(message_text, chr(10), ' '), 1, 200) AS error_text
               FROM v$diag_alert_ext
               WHERE message_text LIKE '%TNS-%'
               ORDER BY record_id DESC
           ) WHERE ROWNUM <= 20"""
    ])

    if _cancel_event.is_set():
        report["status"] = "cancelled"

    return report
