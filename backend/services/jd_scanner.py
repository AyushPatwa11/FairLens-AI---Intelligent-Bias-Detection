import os
import json
import re
from langchain_core.prompts import PromptTemplate
from .llm_helper import get_llm_wrapper

BIAS_PATTERNS = [
    # ========== GENDER BIAS ==========
    # Gender-explicit language
    {"type": "Gender", "word": "male candidate", "replacement": "candidate"},
    {"type": "Gender", "word": "female candidates", "replacement": "candidates"},
    {"type": "Gender", "word": "male-dominated", "replacement": "diverse"},
    {"type": "Gender", "word": "female", "replacement": "candidate"},
    {"type": "Gender", "word": "male", "replacement": "candidate"},
    {"type": "Gender", "word": "unmarried", "replacement": "available"},
    {"type": "Gender", "word": "married", "replacement": "available"},
    {"type": "Gender", "word": "motherhood", "replacement": "personal responsibilities"},
    {"type": "Gender", "word": "fatherhood", "replacement": "personal responsibilities"},
    {"type": "Gender", "word": "maternity", "replacement": "parental leave"},
    {"type": "Gender", "word": "paternity", "replacement": "parental leave"},
    {"type": "Gender", "word": "pregnant", "replacement": "candidate"},
    
    # Gender-coded language
    {"type": "Gender", "word": "aggressive", "replacement": "proactive"},
    {"type": "Gender", "word": "dominant", "replacement": "collaborative"},
    {"type": "Gender", "word": "rockstar", "replacement": "high-performing"},
    {"type": "Gender", "word": "ninja", "replacement": "specialist"},
    {"type": "Gender", "word": "boss", "replacement": "leader"},
    {"type": "Gender", "word": "super girl", "replacement": "exceptional candidate"},
    {"type": "Gender", "word": "ambitious", "replacement": "goal-oriented"},
    {"type": "Gender", "word": "emotional", "replacement": "empathetic"},
    {"type": "Gender", "word": "bossy", "replacement": "assertive"},
    
    # ========== AGE BIAS ==========
    {"type": "Age", "word": "young", "replacement": "early-career"},
    {"type": "Age", "word": "digital native", "replacement": "comfortable with technology"},
    {"type": "Age", "word": "recent graduate", "replacement": "entry-level candidate"},
    {"type": "Age", "word": "energetic", "replacement": "motivated"},
    {"type": "Age", "word": "fast-paced environment", "replacement": "dynamic environment"},
    {"type": "Age", "word": "millennial", "replacement": "candidate"},
    {"type": "Age", "word": "gen z", "replacement": "candidate"},
    {"type": "Age", "word": "tech savvy", "replacement": "technologically skilled"},
    {"type": "Age", "word": "old", "replacement": "experienced"},
    {"type": "Age", "word": "mature", "replacement": "experienced"},
    {"type": "Age", "word": "fresh out of college", "replacement": "early-career professional"},
    {"type": "Age", "word": "senior", "replacement": "experienced"},
    {"type": "Age", "word": "startup mentality", "replacement": "innovative mindset"},
    {"type": "Age", "word": "stamina", "replacement": "work commitment"},
    
    # ========== PHYSICAL/APPEARANCE BIAS ==========
    {"type": "Physical", "word": "attractive", "replacement": "professional appearance"},
    {"type": "Physical", "word": "tall", "replacement": ""},
    {"type": "Physical", "word": "fit", "replacement": "physically capable"},
    {"type": "Physical", "word": "good looking", "replacement": "professional appearance"},
    {"type": "Physical", "word": "handsome", "replacement": "professional appearance"},
    {"type": "Physical", "word": "beautiful", "replacement": "professional appearance"},
    {"type": "Physical", "word": "slim", "replacement": ""},
    {"type": "Physical", "word": "athletic", "replacement": "physically capable"},
    {"type": "Physical", "word": "well-groomed", "replacement": "professional"},
    
    # ========== DISABILITY BIAS ==========
    {"type": "Disability", "word": "able-bodied", "replacement": "candidate"},
    {"type": "Disability", "word": "physically able", "replacement": "candidate"},
    {"type": "Disability", "word": "no disabilities", "replacement": "candidate"},
    {"type": "Disability", "word": "normal ability", "replacement": "candidate"},
    {"type": "Disability", "word": "physically demanding", "replacement": "role requirements"},
    {"type": "Disability", "word": "must have mobility", "replacement": "role-specific requirements"},
    
    # ========== SOCIO-ECONOMIC BIAS ==========
    {"type": "Socio-Economic", "word": "elite school", "replacement": "strong academic background"},
    {"type": "Socio-Economic", "word": "ivy league", "replacement": "top-tier university"},
    {"type": "Socio-Economic", "word": "expensive degree", "replacement": "advanced qualification"},
    {"type": "Socio-Economic", "word": "native speaker", "replacement": "fluent in language"},
    {"type": "Socio-Economic", "word": "from rich family", "replacement": "candidate"},
    {"type": "Socio-Economic", "word": "upper class", "replacement": "candidate"},
    {"type": "Socio-Economic", "word": "prestigious background", "replacement": "relevant experience"},
    {"type": "Socio-Economic", "word": "luxury experience", "replacement": "professional experience"},
    
    # ========== CULTURAL/NATIONAL BIAS ==========
    {"type": "Cultural", "word": "western background", "replacement": "international experience"},
    {"type": "Cultural", "word": "british english", "replacement": "professional english"},
    {"type": "Cultural", "word": "american accent", "replacement": "clear communication"},
    {"type": "Cultural", "word": "christian values", "replacement": "company values"},
    {"type": "Cultural", "word": "local candidate", "replacement": "candidate"},
    {"type": "Cultural", "word": "speaks with accent", "replacement": "communicates clearly"},
    {"type": "Cultural", "word": "foreign", "replacement": "candidate"},
    {"type": "Cultural", "word": "immigrant", "replacement": "candidate"},
    
    # ========== RELIGION BIAS ==========
    {"type": "Religion", "word": "christian", "replacement": "candidate"},
    {"type": "Religion", "word": "hindu", "replacement": "candidate"},
    {"type": "Religion", "word": "muslim", "replacement": "candidate"},
    {"type": "Religion", "word": "jewish", "replacement": "candidate"},
    {"type": "Religion", "word": "atheist", "replacement": "candidate"},
    {"type": "Religion", "word": "non-religious", "replacement": "candidate"},
    {"type": "Religion", "word": "worship", "replacement": "personal values"},
    {"type": "Religion", "word": "faith-based", "replacement": "values-based"},
    
    # ========== FAMILY/MARITAL STATUS BIAS ==========
    {"type": "Family", "word": "single", "replacement": "candidate"},
    {"type": "Family", "word": "divorced", "replacement": "candidate"},
    {"type": "Family", "word": "no kids", "replacement": "candidate"},
    {"type": "Family", "word": "no children", "replacement": "candidate"},
    {"type": "Family", "word": "family man", "replacement": "reliable"},
    {"type": "Family", "word": "has dependents", "replacement": "candidate"},
    {"type": "Family", "word": "works from home", "replacement": "flexible work"},
    
    # ========== HEALTH/MENTAL HEALTH BIAS ==========
    {"type": "Health", "word": "mentally stable", "replacement": "candidate"},
    {"type": "Health", "word": "healthy individual", "replacement": "candidate"},
    {"type": "Health", "word": "no mental illness", "replacement": "candidate"},
    {"type": "Health", "word": "depression", "replacement": "candidate"},
    {"type": "Health", "word": "anxiety", "replacement": "candidate"},
    
    # ========== CASTE/CLASS BIAS ==========
    {"type": "Caste", "word": "upper caste", "replacement": "candidate"},
    {"type": "Caste", "word": "lower class", "replacement": "candidate"},
    {"type": "Caste", "word": "working class", "replacement": "candidate"},
    {"type": "Caste", "word": "rural background", "replacement": "candidate"},
    {"type": "Caste", "word": "urban background", "replacement": "candidate"},
    
    # ========== APPEARANCE/BEAUTY BIAS ==========
    {"type": "Appearance", "word": "beautiful", "replacement": "professional"},
    {"type": "Appearance", "word": "gorgeous", "replacement": "professional"},
    {"type": "Appearance", "word": "cute", "replacement": "professional"},
    {"type": "Appearance", "word": "homely", "replacement": "candidate"},
    {"type": "Appearance", "word": "fashionable", "replacement": "professional appearance"},
    {"type": "Appearance", "word": "modern look", "replacement": "professional appearance"},
]

def _risk_from_score(score: int) -> str:
    if score >= 60:
        return "High Risk"
    if score >= 30:
        return "Medium Risk"
    return "Low Risk"

def _rule_based_scan(text: str):
    suggestions = []
    highlighted = text
    gender_count = 0
    age_count = 0
    physical_count = 0
    socio_economic_count = 0
    cultural_count = 0
    disability_count = 0
    religion_count = 0
    family_count = 0
    health_count = 0
    caste_count = 0
    appearance_count = 0

    for item in BIAS_PATTERNS:
        pattern = re.compile(r"\b" + re.escape(item["word"]) + r"\b", re.IGNORECASE)
        matches = list(pattern.finditer(highlighted))
        if not matches:
            continue

        if item["type"] == "Gender":
            gender_count += len(matches)
        elif item["type"] == "Age":
            age_count += len(matches)
        elif item["type"] == "Physical":
            physical_count += len(matches)
        elif item["type"] == "Socio-Economic":
            socio_economic_count += len(matches)
        elif item["type"] == "Cultural":
            cultural_count += len(matches)
        elif item["type"] == "Disability":
            disability_count += len(matches)
        elif item["type"] == "Religion":
            religion_count += len(matches)
        elif item["type"] == "Family":
            family_count += len(matches)
        elif item["type"] == "Health":
            health_count += len(matches)
        elif item["type"] == "Caste":
            caste_count += len(matches)
        elif item["type"] == "Appearance":
            appearance_count += len(matches)

        suggestions.append({
            "type": item["type"],
            "word": item["word"],
            "replacement": item["replacement"]
        })

        highlighted = pattern.sub(
            lambda m: f"<span class='highlight-bias' title='Bias: {item['type']}'>{m.group(0)}</span>",
            highlighted
        )

    unique_suggestions = [dict(t) for t in {tuple(s.items()) for s in suggestions}]
    total_hits = (gender_count + age_count + physical_count + socio_economic_count + cultural_count + 
                  disability_count + religion_count + family_count + health_count + caste_count + appearance_count)
    score = min(100, total_hits * 12)

    return {
        "processed_text": highlighted.replace("\n", "<br>"),
        "suggestions": unique_suggestions,
        "gender_count": gender_count,
        "age_count": age_count,
        "physical_count": physical_count,
        "socio_economic_count": socio_economic_count,
        "cultural_count": cultural_count,
        "disability_count": disability_count,
        "religion_count": religion_count,
        "family_count": family_count,
        "health_count": health_count,
        "caste_count": caste_count,
        "appearance_count": appearance_count,
        "score": score,
        "risk": _risk_from_score(score)
    }

MAX_REPLACEMENT_SUGGESTIONS = 10

def _generate_ai_report(text: str, scan_result: dict, wrapper) -> str:
    """Generate an AI audit report summarizing JD bias findings."""
    try:
        bias_summary = []
        for bias_type, count_key in [
            ("Gender", "gender_count"), ("Age", "age_count"), ("Physical", "physical_count"),
            ("Socio-Economic", "socio_economic_count"), ("Cultural", "cultural_count"),
            ("Disability", "disability_count"), ("Religion", "religion_count"),
            ("Family", "family_count"), ("Health", "health_count"),
            ("Caste", "caste_count"), ("Appearance", "appearance_count"),
        ]:
            count = scan_result.get(count_key, 0)
            if count > 0:
                bias_summary.append(f"- {bias_type} Bias: {count} instance(s)")

        if not bias_summary:
            bias_summary_text = "No bias patterns detected."
        else:
            bias_summary_text = "\n".join(bias_summary)

        suggestions = scan_result.get("suggestions", [])
        replacements_text = "\n".join(
            [f'- Replace "{s["word"]}" with "{s["replacement"]}"' for s in suggestions[:MAX_REPLACEMENT_SUGGESTIONS] if s.get("replacement")]
        ) or "None"

        prompt_text = f"""You are an expert HR compliance and fairness AI auditor.

A job description has been scanned for biased language. Below is a summary of findings:

**Bias Score:** {scan_result.get('score', 0)}/100
**Risk Level:** {scan_result.get('risk', 'Low Risk')}

**Detected Bias Instances by Category:**
{bias_summary_text}

**Top Suggested Replacements:**
{replacements_text}

Based on these findings, write a concise professional audit report covering:
1. **Executive Summary** – overall bias risk assessment
2. **Key Findings** – which bias categories are most prominent and why they matter
3. **Impact Analysis** – how this language may affect candidate diversity and legal compliance
4. **Recommendations** – prioritized action items to improve inclusivity

Rules:
- Be objective, data-driven, and neutral.
- Use clear professional Markdown formatting.
- Keep the report concise and high-impact (max 300 words).
- Do not invent bias instances that are not in the summary above.
"""
        response = wrapper.invoke(prompt_text)
        return response.content.strip()
    except Exception as e:
        return f"AI Audit Report generation failed: {str(e)}"


def scan(text: str):
    baseline = _rule_based_scan(text)
    wrapper = get_llm_wrapper(temperature=0.1)
    if not wrapper:
        baseline["success"] = True
        baseline["engine"] = "rule-based"
        baseline["ai_report"] = "Offline Mode: AI Audit Report unavailable. Please set the GOOGLE_API_KEY environment variable (e.g., in backend/.env) to enable."
        return baseline

    try:
        prompt = PromptTemplate.from_template("""
You are a fairness and compliance AI. Analyze the following job description for exclusionary language and bias.
Job Description:
{text}

Return your response strictly as a JSON object with the following schema:
{{
  "processed_text": "The original text but with HTML <span class='highlight-bias' title='Bias: [Type]'>biased_word</span> tags wrapping the biased words.",
  "suggestions": [
    {{"type": "Gender (or Age, Disability, Religion, Family, Physical, Socio-Economic, Cultural, Health, Caste, Appearance)", "word": "biased word", "replacement": "inclusive alternative"}}
  ],
  "gender_count": 0,
  "age_count": 0,
  "physical_count": 0,
  "socio_economic_count": 0,
  "cultural_count": 0,
  "disability_count": 0,
  "religion_count": 0,
  "family_count": 0,
  "health_count": 0,
  "caste_count": 0,
  "appearance_count": 0,
  "score": 0,
  "risk": "Low Risk"
}}
Rules:
- "risk" must be one of: "Low Risk", "Medium Risk", "High Risk" based on severity (score 0-100).
- score is 0 (no bias) to 100 (maximum bias).
- Make sure it is valid JSON. Do not include markdown codeblocks like ```json.
""")
        response = wrapper.invoke(prompt.format(text=text))
        content = response.content.strip()
        
        # Clean up markdown if LLM includes it
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        data = json.loads(content.strip())
        data["success"] = True
        data["engine"] = "llm"
        # Generate AI audit report using LLM output
        data["ai_report"] = _generate_ai_report(text, data, wrapper)
        return data
    except Exception as e:
        baseline["success"] = True
        baseline["engine"] = "rule-based"
        baseline["fallback_reason"] = str(e)
        # Still generate AI report from rule-based results
        baseline["ai_report"] = _generate_ai_report(text, baseline, wrapper)
        return baseline

