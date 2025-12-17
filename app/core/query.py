from core.db import get_pool


async def get_tests_and_execution(problem_slug: str, language_slug: str):
    """Database'dan problem va test case'larni olish"""
    pool = await get_pool()

    problem = await pool.fetchrow("""
        SELECT id
        FROM problems_problem
        WHERE slug = $1
          AND is_active = true
    """, problem_slug)
    
    if not problem:
        return None

    problem_id = problem["id"]

    language = await pool.fetchrow("""
        SELECT id
        FROM problems_language
        WHERE slug = $1
    """, language_slug)
    
    if not language:
        return None

    language_id = language["id"]

    test_cases = await pool.fetch("""
        SELECT input_txt, output_txt, is_sample
        FROM problems_testcase
        WHERE problem_id = $1
        ORDER BY is_sample DESC, id
    """, problem_id)

    exec_wrapper = await pool.fetchrow("""
        SELECT top_code, bottom_code
        FROM problems_executiontestcase
        WHERE problem_id = $1
          AND language_id = $2
    """, problem_id, language_id)

    return {
        "test_cases": [dict(tc) for tc in test_cases],
        "execution_wrapper": dict(exec_wrapper) if exec_wrapper else None
    }