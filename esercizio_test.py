def calculate_cagr(beginning_value, ending_value, years):
    if beginning_value <= 0 or ending_value <= 0 or years <= 0:
        return None
    cagr = (ending_value / beginning_value) ** (1 / years) - 1
    return cagr
