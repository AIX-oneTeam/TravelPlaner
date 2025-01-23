from app.schema.plan import Plan


def reg_plan(plan: Plan, member_id: int):
    plan.member_id = member_id
    save_plan(plan)