from typing import Any
SKILLS: list[dict[str, Any]] = [
 {"id":"market.research","name":"Market Research","description":"Prepare evidence-based briefs from indexed knowledge and connected sources.","enabled":True,"risk":"low"},
 {"id":"content.draft","name":"Content Studio","description":"Draft bilingual editorial and brand content; publishing requires separate approval.","enabled":True,"risk":"low"},
 {"id":"network.admin","name":"System Administration","description":"Reserved for owner-authorized network administration. No router or MAC-filter changes are enabled in this foundation.","enabled":False,"risk":"high","requires_approval":True},
 {"id":"market.collect","name":"Market Data Collection","description":"Reserved connector for compliant public-source collection; source policies and rate limits must be configured first.","enabled":False,"risk":"medium","requires_approval":True}
]
def list_skills() -> list[dict[str, Any]]:
    return SKILLS
