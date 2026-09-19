def generate_explanation(spatial_score: float, freq_score: float, active_pass: bool, heatmap, spectrum):
    """
    Aggregates all signals into a final readable output.
    Returns a dictionary containing the explanation details.
    """
    # Assuming scores > 0.5 mean SPOOF
    spatial_spoof = spatial_score > 0.5
    freq_spoof = freq_score > 0.5
    
    is_spoof = spatial_spoof or freq_spoof or not active_pass
    confidence = max(spatial_score, freq_score) if is_spoof else (1.0 - max(spatial_score, freq_score))
    
    evidence = []
    if spatial_spoof:
        evidence.append("Spatial anomaly detected (Texture/Artifacts)")
    if freq_spoof:
        evidence.append("Frequency anomaly detected (High-frequency spoof noise)")
    if not active_pass:
        evidence.append("Active challenge failed (Potential replay/deepfake)")
        
    if not is_spoof:
        evidence.append("All liveness checks passed.")
        reason = "Genuine user presentation"
    else:
        reasons = []
        if not active_pass and not spatial_spoof:
            reasons.append("Likely replay or deepfake (failed active interaction)")
        if spatial_spoof or freq_spoof:
            reasons.append("Likely print or screen attack (visual artifacts detected)")
        reason = " and ".join(reasons) if reasons else "Spoof attack detected"

    return {
        "Result": "SPOOF" if is_spoof else "REAL",
        "Confidence": f"{confidence * 100:.2f}%",
        "Evidence": evidence,
        "Reason": reason,
        "Heatmap_Available": heatmap is not None,
        "Spectrum_Available": spectrum is not None
    }
