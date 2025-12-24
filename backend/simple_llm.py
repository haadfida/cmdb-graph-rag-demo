"""
simple_llm.py - Simple rule-based LLM fallback (no API needed)
Generates answers based on graph context without external API calls
"""


def generate_answer(question: str, context: str) -> str:
    """
    Generate a simple answer based on the graph context
    This is a fallback that doesn't require any LLM API
    """
    question_lower = question.lower()

    # Extract key information from context
    lines = context.split('\n')

    # Simple pattern matching for common questions
    if 'located' in question_lower or 'location' in question_lower:
        for line in lines:
            if 'LOCATED_IN' in line or 'Location' in line:
                return f"Based on the graph data: {line.strip()}"

    elif 'break' in question_lower or 'depend' in question_lower or 'down' in question_lower:
        deps = [line.strip() for line in lines if 'DEPENDS_ON' in line]
        if deps:
            return f"Based on the dependency graph:\n" + "\n".join(deps)

    elif 'own' in question_lower:
        for line in lines:
            if 'OWNS' in line or 'User' in line:
                return f"Based on the ownership data: {line.strip()}"

    elif 'service' in question_lower and 'running' in question_lower:
        services = [line.strip() for line in lines if 'Service' in line or 'RUNS_ON' in line]
        if services:
            return "Based on the graph:\n" + "\n".join(services[:5])

    # Generic response using all relevant information
    relevant_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
    if relevant_lines:
        return "Based on the CMDB graph data:\n\n" + "\n".join(relevant_lines[:10])

    return "I found some information in the graph. Please check the visualization on the right for details."
