from typing import Any

SKILLS: list[dict[str, Any]] = [
    {"id":"assistant.general","name":"General Assistant","description":"Answer questions using available context and indexed evidence.","enabled":True,"risk":"low","system_instruction":"Answer the user's request directly. Separate facts, assumptions and recommendations."},
    {"id":"market.research","name":"Market Research","description":"Structure market and competitor research briefs from available evidence.","enabled":True,"risk":"low","system_instruction":"Produce a research brief with scope, evidence, findings, gaps and next steps. Never claim live web research unless a connected source supplied it."},
    {"id":"content.draft","name":"Content Studio","description":"Draft bilingual editorial, business and brand content.","enabled":True,"risk":"low","system_instruction":"Create the requested content in the requested format and tone. Do not publish or send it."},
    {"id":"workflow.plan","name":"Workflow Planner","description":"Convert repeatable work into documented, reviewable workflows.","enabled":True,"risk":"low","system_instruction":"Return objective, prerequisites, ordered steps, inputs, outputs, failure handling and approval gates."},
    {"id":"system.admin","name":"System Administration","description":"Reserved for explicitly authorized system administration.","enabled":False,"risk":"high","requires_approval":True,"system_instruction":"Disabled."},
    {"id":"market.collect","name":"Public Data Collection","description":"Reserved for compliant source collection after source policy and rate limits are configured.","enabled":False,"risk":"medium","requires_approval":True,"system_instruction":"Disabled."},
]

def list_skills() -> list[dict[str, Any]]:
    return [{key:value for key,value in skill.items() if key != "system_instruction"} for skill in SKILLS]

def get_skill(skill_id: str) -> dict[str, Any] | None:
    return next((skill for skill in SKILLS if skill["id"] == skill_id), None)
