"""Convert output.json into a flat CSV for quick review in Excel/Sheets."""

import csv
import json
import sys


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else "output/output.json"
    if source == "output.json" and not __import__("pathlib").Path(source).exists():
        source = "output/output.json"  # new default location
    destination = source.rsplit(".", 1)[0] + ".csv"
    records = json.loads(open(source, encoding="utf-8").read())
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
    print(f"Wrote {len(rows)} rows to {destination}")


if __name__ == "__main__":
    main()
