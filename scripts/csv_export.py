"""Shared CSV writer: flattens enriched records for Excel/Sheets review."""

import csv


def write_csv(records: list[dict], destination) -> int:
    """Write enriched records (as plain dicts) to a flat CSV file."""
    rows = []
    for r in records:
        rows.append({
            "domain": r["domain"],
            "company_overview": r["company_overview"],
            "target_audience": "; ".join(r["target_audience"]),
            "public_emails": "; ".join(r["contact_points"]["public_emails"]),
            "key_leadership": "; ".join(
                f"{p['name']} ({p['role']})" for p in r["key_leadership"]
            ),
            "data_confidence_score": r["data_confidence_score"],
            "total_tokens": r.get("token_usage", {}).get("total_tokens", ""),
            "errors": "; ".join(r["errors"]),
        })
    with open(destination, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
