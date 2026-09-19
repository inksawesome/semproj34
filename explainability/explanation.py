def generate_explanation(spatial_score: float, freq_score: float, active_pass: bool, 
                         image=None, heatmap=None, spectrum=None):
    """
    Aggregates all signals into a final readable output dict for the UI.
    spatial_score: float (0-1, where 1 = Real, 0 = Spoof)
    freq_score: float (0-1, where 1 = Real, 0 = Spoof)
    active_pass: bool
    """
    threshold_spatial = 0.5
    threshold_freq = 0.5
    
    is_real = active_pass and (spatial_score > threshold_spatial) and (freq_score > threshold_freq)
    
    spatial_conf = spatial_score if is_real else (1 - spatial_score)
    freq_conf = freq_score if is_real else (1 - freq_score)
    confidence = (spatial_conf + freq_conf + (1.0 if active_pass else 0.0)) / 3.0
    
    reasons = []
    if not active_pass:
        reasons.append("Failed active challenge (possible static replay or deepfake lacking required movement).")
    if spatial_score <= threshold_spatial:
        reasons.append(f"Spatial model detected artifacts typical of spoofing (Score: {spatial_score:.2f}).")
    if freq_score <= threshold_freq:
        reasons.append(f"Frequency model detected anomalous high-frequency patterns (Score: {freq_score:.2f}).")
        
    if is_real:
        reasoning = "All liveness checks passed successfully. Presentation is genuine."
    else:
        reasoning = "Spoof detected due to: " + " ".join(reasons)
        
    result = {
        "verdict": "REAL" if is_real else "SPOOF",
        "confidence": confidence,
        "evidence": {
            "spatial_anomaly_detected": spatial_score <= threshold_spatial,
            "frequency_anomaly_detected": freq_score <= threshold_freq,
            "active_challenge_passed": active_pass
        },
        "reasoning": reasoning
    }
    
    # We can also attach the images to the dictionary if the UI expects them
    if heatmap is not None:
        result["spatial_heatmap_img"] = heatmap
    if spectrum is not None:
        result["frequency_spectrum_img"] = spectrum
        
    return result
