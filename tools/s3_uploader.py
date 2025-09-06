#!/usr/bin/env python3
import re, sys, pathlib, argparse, csv, boto3, botocore

ICON_RE = re.compile(r'^ICON-(\d{6})-([A-Z0-9\-]+)(?:-([A-Z0-9\-]+))?\.(svg|png|pdf)$')
SPEC_RE = re.compile(r'^(USA)-([A-Z]{2})-(\d{3})-([12])-([0-9]{6})-([0-9]{6})-([A-Za-z0-9\-]+)-([A-Za-z0-9\-]+)\.pdf$')

def load_mf_map(path="schema/mf_section_map.csv"):
    m = {}
    p = pathlib.Path(path)
    if not p.exists(): return m
    with p.open() as f:
        r = csv.DictReader(f)
        for row in r:
            key = row["mf_section"].strip()
            allowed = set(t.strip().upper() for t in row["allowed_types"].split("|"))
            m[key] = allowed
    return m

def parse_icon(name: str):
    m = ICON_RE.match(name)
    if not m: return None
    mf_section, type_slug, variant = m.group(1), m.group(2), m.group(3)
    tags = {"kind":"icon","mf_sec": mf_section, "mf_div": mf_section[:2], "type": type_slug.upper()}
    if variant: tags["variant"] = variant.upper()
    return tags

def parse_spec(name: str):
    m = SPEC_RE.match(name)
    if not m: return None
    country, state, fips, own, naics, mf_section, desc, brand = m.groups()
    form_factor = desc.split("-")[0].upper()
    tags = {
        "kind":"spec",
        "country": country, "state": state, "fips": fips, "ownership": own, "naics": naics,
        "mf_sec": mf_section, "mf_div": mf_section[:2],
        "type": form_factor, "brand": brand, "desc": desc
    }
    return tags

def decide_key(tags: dict, filename: str) -> str:
    if tags["kind"] == "icon":
        return f"ICONS/normalized/{tags['mf_div']}/{filename}"
    return (f"SPECS/normalized/region={tags['country']}/state={tags['state']}/county={tags['fips']}/"
            f"ownership={tags['ownership']}/naics={tags['naics']}/{tags['mf_div']}/{tags['mf_sec']}/{filename}")

def main():
    ap = argparse.ArgumentParser(description="Validate name, enforce MasterFormat rules, upload to S3 with tags.")
    ap.add_argument("file", help="Path to file (name must be canonical)")
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--mf-map", default="schema/mf_section_map.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mf_rules = load_mf_map(args.mf_map)

    path = pathlib.Path(args.file)
    if not path.is_file():
        print(f"ERROR: file not found: {path}", file=sys.stderr); sys.exit(2)

    name = path.name
    tags = parse_icon(name) or parse_spec(name)
    if not tags:
        print(f"ERROR: filename does not match ICON or SPEC patterns: {name}", file=sys.stderr); sys.exit(3)

    # MasterFormat type check (if we have rules for this section)
    allowed = mf_rules.get(tags["mf_sec"])
    if allowed and tags["type"].upper() not in allowed:
        print(f"ERROR: type '{tags['type']}' not allowed for MF section {tags['mf_sec']} (allowed: {sorted(allowed)})", file=sys.stderr)
        sys.exit(5)

    s3_key = decide_key(tags, name)
    tag_str = "&".join(f"{k}={v}" for k, v in tags.items())

    print("✔ Valid filename & MF check passed")
    print(f"  s3 key: s3://{args.bucket}/{s3_key}")
    print(f"  tags:   {tag_str}")

    if args.dry_run: return

    s3 = boto3.client("s3")
    extra = {"Tagging": tag_str}
    if name.lower().endswith(".pdf"): extra["ContentType"] = "application/pdf"

    try:
        s3.upload_file(str(path), args.bucket, s3_key, ExtraArgs=extra)
        print(f"✔ Uploaded")
    except botocore.exceptions.ClientError as e:
        print(f"ERROR: upload failed: {e}", file=sys.stderr); sys.exit(4)

if __name__ == "__main__":
    main()
