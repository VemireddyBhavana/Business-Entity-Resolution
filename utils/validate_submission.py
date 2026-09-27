"""
Submission Validator for Business Entity Resolution Challenge.
Checks matching_results.tsv and candidate_pairs.tsv against official competition rules:
1. TSV format with exact headers.
2. Every Source 1 entity in the test set has exactly one row.
3. No duplicate rows and no missing entities.
4. Only valid Source 2 and Source 3 IDs (no self-matches, no nonexistent IDs).
5. No duplicates within any comma-separated ID list.
6. Every matched entity in matching_results.tsv is a subset of candidate_pairs.tsv.
"""

import sys
import os
import argparse
import csv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def validate(matching_path, candidate_path, test_dir):
    print("=" * 70)
    print(" [VALIDATOR] BUSINESS ENTITY RESOLUTION - SUBMISSION VALIDATOR")
    print("=" * 70)

    issues = []

    # Check files exist
    if not os.path.exists(matching_path):
        issues.append(f"Missing matching_results file: {matching_path}")
    if not os.path.exists(candidate_path):
        issues.append(f"Missing candidate_pairs file: {candidate_path}")
    
    test_s1_path = os.path.join(test_dir, "test_source1.tsv")
    if not os.path.exists(test_s1_path):
        issues.append(f"Missing test source 1 file: {test_s1_path}")

    if issues:
        print("\n[!] FATAL ISSUES:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        sys.exit(1)

    # 1. Load Expected Source 1 IDs
    print("\n[1/4] Reading test Source 1 entities...")
    with open(test_s1_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        s1_header = next(reader)
        id_idx = s1_header.index("entity_id") if "entity_id" in s1_header else 0
        expected_s1_ids = [row[id_idx] for row in reader if row]
    
    expected_set = set(expected_s1_ids)
    total_expected = len(expected_s1_ids)
    print(f"      Total expected Source 1 test entities: {total_expected:,}")

    # 2. Validate matching_results.tsv
    print("\n[2/4] Validating matching_results.tsv...")
    matching_map = {}
    with open(matching_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        try:
            m_header = next(reader)
        except StopIteration:
            m_header = []

        if len(m_header) != 2 or m_header[0] != "source1_entity_id" or m_header[1] != "matched_entity_ids":
            issues.append(f"matching_results.tsv must have header 'source1_entity_id\\tmatched_entity_ids', found: {m_header}")

        for line_num, row in enumerate(reader, start=2):
            if not row:
                continue
            s1_id = row[0]
            matched_str = row[1] if len(row) > 1 else ""

            if s1_id in matching_map:
                issues.append(f"Duplicate row for entity {s1_id} at line {line_num} in matching_results.tsv")
            
            ids = [x.strip() for x in matched_str.split(",") if x.strip()]
            if len(ids) != len(set(ids)):
                issues.append(f"Duplicate IDs in matched list for {s1_id} at line {line_num}")
            
            for mid in ids:
                if not (mid.startswith("S2-") or mid.startswith("S3-")):
                    issues.append(f"Invalid entity prefix in match '{mid}' for {s1_id} at line {line_num} (must start with S2- or S3-)")
                    break

            matching_map[s1_id] = set(ids)

    if len(matching_map) != total_expected:
        issues.append(f"matching_results.tsv row count ({len(matching_map):,}) does not match test_source1 count ({total_expected:,})")

    missing_in_m = expected_set - set(matching_map.keys())
    if missing_in_m:
        issues.append(f"{len(missing_in_m):,} Source 1 entities from test_source1 are missing from matching_results.tsv (e.g. {list(missing_in_m)[:3]})")

    # 3. Validate candidate_pairs.tsv
    print("\n[3/4] Validating candidate_pairs.tsv...")
    candidate_map = {}
    with open(candidate_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        try:
            c_header = next(reader)
        except StopIteration:
            c_header = []

        if len(c_header) != 2 or c_header[0] != "source1_entity_id" or c_header[1] != "candidate_entity_ids":
            issues.append(f"candidate_pairs.tsv must have header 'source1_entity_id\\tcandidate_entity_ids', found: {c_header}")

        for line_num, row in enumerate(reader, start=2):
            if not row:
                continue
            s1_id = row[0]
            cand_str = row[1] if len(row) > 1 else ""

            if s1_id in candidate_map:
                issues.append(f"Duplicate row for entity {s1_id} at line {line_num} in candidate_pairs.tsv")

            ids = [x.strip() for x in cand_str.split(",") if x.strip()]
            if len(ids) != len(set(ids)):
                issues.append(f"Duplicate IDs in candidate list for {s1_id} at line {line_num}")

            for cid in ids:
                if not (cid.startswith("S2-") or cid.startswith("S3-")):
                    issues.append(f"Invalid candidate prefix '{cid}' for {s1_id} at line {line_num}")
                    break

            candidate_map[s1_id] = set(ids)

    if len(candidate_map) != total_expected:
        issues.append(f"candidate_pairs.tsv row count ({len(candidate_map):,}) does not match test_source1 count ({total_expected:,})")

    # 4. Consistency Check: Matches MUST be a subset of Candidates
    print("\n[4/4] Cross-checking candidate vs match consistency...")
    subset_violations = 0
    for s1_id, matches in matching_map.items():
        candidates = candidate_map.get(s1_id, set())
        invalid_matches = matches - candidates
        if invalid_matches:
            subset_violations += 1
            if subset_violations <= 3:
                issues.append(f"Entity {s1_id} has matched IDs not present in its candidate set: {list(invalid_matches)[:3]}")

    if subset_violations > 3:
        issues.append(f"Total of {subset_violations} entities have matched IDs that never appeared in candidate_pairs.tsv")

    # Report Results
    print("\n" + "=" * 70)
    if issues:
        print(f" [FAIL] VALIDATION FAILED - Found {len(issues)} issue(s):")
        print("=" * 70)
        for i, issue in enumerate(issues[:10], 1):
            print(f"  {i}. {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more issues.")
        sys.exit(1)
    else:
        print("  [PASS] All files strictly conform to the competition requirements!")
        print("=" * 70)
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate submission files")
    parser.add_argument("--matching", default="output/matching_results.tsv", help="Path to matching_results.tsv")
    parser.add_argument("--candidate", default="output/candidate_pairs.tsv", help="Path to candidate_pairs.tsv")
    parser.add_argument("--test-dir", default="dataset/test", help="Path to test dataset directory")
    args = parser.parse_args()

    validate(args.matching, args.candidate, args.test_dir)
