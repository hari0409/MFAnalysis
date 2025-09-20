def get_change_score(change_pct):
    """Calculate weighted score based on percentage change"""
    if change_pct >= 50:  # Very large increase (>50%)
        return 2.0
    elif change_pct >= 25:  # Large increase (25-50%)
        return 1.5
    elif change_pct >= 5:   # Moderate increase (5-25%)
        return 1.0
    elif change_pct <= -50:  # Very large decrease (<-50%)
        return -2.0
    elif change_pct <= -25:  # Large decrease (-25 to -50%)
        return -1.5
    elif change_pct <= -5:   # Moderate decrease (-5 to -25%)
        return -1.0
    return 0.0  # Small changes (-5% to 5%)

def max_abs_change(row, fund_trend_matrix):
    if row.name in fund_trend_matrix.index:
        other_value = fund_trend_matrix.loc[row.name, 'share_change']
        return max(abs(row['share_change']), abs(other_value)) * (
            1 if abs(row['share_change']) >= abs(other_value)
            else (1 if other_value > 0 else -1)
        )
    else:
        return row['share_change']
    