# NEKOVA Package — charts
# Simple ASCII charts for terminal output

def load() -> dict:
    return {
        "bar_chart":  _bar_chart,
        "line_chart": _line_chart,
        "pie_chart":  _pie_chart,
    }

def _bar_chart(data: list, width: int = 20):
    if not data: return ""
    max_val = max(data) if max(data) > 0 else 1
    lines = []
    for i, val in enumerate(data):
        bar_len = int((val / max_val) * width)
        bar     = "#" * bar_len
        lines.append(f"  {i+1:>2} | {bar} {val}")
    return "\n".join(lines)

def _line_chart(data: list, width: int = 40):
    if not data: return ""
    max_val = max(data) if max(data) > 0 else 1
    min_val = min(data)
    height  = 10
    lines   = []
    for row in range(height, -1, -1):
        line = ""
        for val in data:
            normalized = (val - min_val) / (max_val - min_val + 0.001)
            if int(normalized * height) >= row:
                line += "o"
            else:
                line += " "
        lines.append(f"  |{line}")
    lines.append(f"  +{-len(data) * -1 * chr(45)}")
    return "\n".join(lines)

def _pie_chart(data: dict):
    if not data: return ""
    total = sum(data.values())
    lines = ["  Pie Chart:"]
    for label, val in data.items():
        pct     = (val / total) * 100 if total > 0 else 0
        bar_len = int(pct / 5)
        bar     = "#" * bar_len
        lines.append(f"  {label:<12} | {bar} {pct:.1f}%")
    return "\n".join(lines)

