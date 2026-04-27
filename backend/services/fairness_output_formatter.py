"""
Standardized output formatter for all fairness analysis modes.
Ensures consistent {bias_score, risk_level, detected_biases, insights, recommendations} format.
"""

def format_dataset_output(analysis_result: dict, domain: str = "hiring") -> dict:
    """
    Convert dataset analyzer output to standardized format.
    """
    if not analysis_result.get("success"):
        return analysis_result
    
    # Extract detected biases from group metrics
    detected_biases = []
    for metric in analysis_result.get("group_metrics", []):
        attr = metric.get("attribute", "Unknown")
        dpd = metric.get("demographic_parity_difference", 0)
        rates = metric.get("selection_rates", {})
        
        if dpd > 0.1:  # Significant disparity threshold
            detected_biases.append({
                "attribute": attr,
                "type": "demographic_parity_bias",
                "impact": "High" if dpd > 0.3 else "Medium",
                "explanation": f"Demographic parity difference of {dpd:.1%} detected for {attr}. Selection rates vary significantly: {rates}"
            })
    
    # Generate insights and recommendations based on domain
    insights = []
    recommendations = []
    
    if detected_biases:
        for bias in detected_biases:
            insights.append(f"Significant disparity detected in {bias['attribute']}-based selection")
        
        if domain == "hiring":
            recommendations.append("Apply reweighting to balance dataset towards equal opportunity")
            recommendations.append("Review job description for exclusionary language using JD Scanner")
            recommendations.append("Consider candidate profile simulator for counterfactual fairness analysis")
        elif domain == "loan":
            recommendations.append("Review financial eligibility criteria for disparate impact")
            recommendations.append("Apply resampling or threshold adjustment for underrepresented groups")
        elif domain == "healthcare":
            recommendations.append("Validate disparities are medically justified (context-aware analysis)")
            recommendations.append("Review medical decision algorithms for systemic bias")
    else:
        insights.append("No significant biases detected in current dataset")
        recommendations.append("Continue monitoring fairness metrics during model deployment")
    
    return {
        "success": True,
        "bias_score": analysis_result.get("score", 0),
        "risk_level": analysis_result.get("risk", "Low Risk"),
        "detected_biases": detected_biases,
        "insights": insights,
        "recommendations": recommendations,
        "group_metrics": analysis_result.get("group_metrics", []),
        "dataset_info": {
            "rows": analysis_result.get("rows"),
            "columns": analysis_result.get("cols")
        }
    }


def format_jd_output(scanner_result: dict, domain: str = "hiring") -> dict:
    """
    Convert JD scanner output to standardized format.
    """
    if not scanner_result.get("success"):
        return scanner_result
    
    # Build detected biases from suggestions
    detected_biases = []
    bias_types = {}
    
    for suggestion in scanner_result.get("suggestions", []):
        bias_type = suggestion.get("type", "Unknown")
        if bias_type not in bias_types:
            bias_types[bias_type] = []
        bias_types[bias_type].append(suggestion)
    
    # Group by type
    for bias_type, items in bias_types.items():
        count = len(items)
        impact = "High" if count > 2 else ("Medium" if count > 0 else "Low")
        detected_biases.append({
            "attribute": bias_type,
            "type": f"{bias_type.lower()}_bias",
            "impact": impact,
            "explanation": f"Found {count} instance(s) of {bias_type.lower()} bias: {', '.join([item['word'] for item in items])}"
        })
    
    # Generate insights
    insights = []
    if scanner_result.get("gender_count", 0) > 0:
        insights.append(f"Gender-coded language detected ({scanner_result['gender_count']} instance(s))")
    if scanner_result.get("age_count", 0) > 0:
        insights.append(f"Age-related bias detected ({scanner_result['age_count']} instance(s))")
    if scanner_result.get("physical_count", 0) > 0:
        insights.append(f"Physical appearance requirements detected ({scanner_result['physical_count']} instance(s))")
    if scanner_result.get("socio_economic_count", 0) > 0:
        insights.append(f"Socio-economic bias detected ({scanner_result['socio_economic_count']} instance(s))")
    if scanner_result.get("cultural_count", 0) > 0:
        insights.append(f"Cultural/national bias detected ({scanner_result['cultural_count']} instance(s))")
    
    if not insights:
        insights.append("No biased language patterns detected")
    
    # Generate recommendations
    recommendations = []
    for suggestion in scanner_result.get("suggestions", []):
        word = suggestion.get("word", "")
        replacement = suggestion.get("replacement", "")
        if replacement:
            recommendations.append(f"Replace '{word}' with '{replacement}'")
    
    if not recommendations:
        recommendations.append("Job description uses inclusive language - no changes needed")
    
    return {
        "success": True,
        "bias_score": scanner_result.get("score", 0),
        "risk_level": scanner_result.get("risk", "Low Risk"),
        "detected_biases": detected_biases,
        "insights": insights,
        "recommendations": recommendations,
        "processed_text": scanner_result.get("processed_text", ""),
        "engine": scanner_result.get("engine", "rule-based"),
        "ai_report": scanner_result.get("ai_report", ""),
        # Pass through raw per-category counts for the frontend breakdown
        "gender_count": scanner_result.get("gender_count", 0),
        "age_count": scanner_result.get("age_count", 0),
        "physical_count": scanner_result.get("physical_count", 0),
        "socio_economic_count": scanner_result.get("socio_economic_count", 0),
        "cultural_count": scanner_result.get("cultural_count", 0),
        "disability_count": scanner_result.get("disability_count", 0),
        "religion_count": scanner_result.get("religion_count", 0),
        "family_count": scanner_result.get("family_count", 0),
        "health_count": scanner_result.get("health_count", 0),
        "caste_count": scanner_result.get("caste_count", 0),
        "appearance_count": scanner_result.get("appearance_count", 0),
    }


def format_simulator_output(simulator_result: dict) -> dict:
    """
    Convert profile simulator output to standardized format.
    """
    if not simulator_result.get("success"):
        return simulator_result
    
    orig_prob = simulator_result.get("orig_prob", 0)
    cf_prob = simulator_result.get("cf_prob", 0)
    difference = simulator_result.get("difference", 0)
    
    # Determine if bias is significant
    bias_impact = simulator_result.get("bias_impact", "Low")
    risk_level = "High Risk" if abs(difference) > 15 else ("Medium Risk" if abs(difference) > 5 else "Low Risk")
    
    # Build detected biases
    detected_biases = []
    if abs(difference) > 5:
        detected_biases.append({
            "attribute": "Sensitive Attributes",
            "type": "counterfactual_bias",
            "impact": bias_impact,
            "explanation": f"Model prediction changes by {abs(difference):.1f}% when sensitive attribute(s) change: {', '.join(simulator_result.get('changed_attributes', ['Gender']))}. Original prediction: {orig_prob:.1f}%, Counterfactual: {cf_prob:.1f}%"
        })
    
    insights = [
        f"Original prediction: {orig_prob:.1f}% probability",
        f"Counterfactual prediction: {cf_prob:.1f}% probability",
        f"Difference: {abs(difference):.1f}% (severity: {bias_impact})"
    ]
    
    if abs(difference) > 15:
        insights.append("⚠️ SEVERE BIAS: Small changes in sensitive attributes significantly alter predictions")
    elif abs(difference) > 5:
        insights.append("Moderate bias detected: Sensitive attributes influence predictions")
    
    recommendations = []
    if abs(difference) > 15:
        recommendations.append("Conduct comprehensive fairness audit of model and training data")
        recommendations.append("Retrain model with fairness constraints or reweighting")
        recommendations.append("Review feature importance to identify discriminatory patterns")
    elif abs(difference) > 5:
        recommendations.append("Monitor model fairness during deployment")
        recommendations.append("Consider applying fairness-aware ML techniques")
    else:
        recommendations.append("Model appears relatively fair on this attribute")
        recommendations.append("Continue monitoring with diverse test cases")
    
    return {
        "success": True,
        "bias_score": int(min(100, abs(difference) * 6)),  # Map difference to 0-100 scale
        "risk_level": risk_level,
        "detected_biases": detected_biases,
        "insights": insights,
        "recommendations": recommendations,
        "counterfactual_analysis": {
            "original_prediction": orig_prob,
            "counterfactual_prediction": cf_prob,
            "difference": difference,
            "changed_attributes": simulator_result.get("changed_attributes", ["Gender"]),
            "scenario": simulator_result.get("scenario", "Hiring")
        }
    }
